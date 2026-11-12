"""Nodo de visión: clasifica cada manzana cuando el Arduino avisa que está bajo la cámara.

Flujo: recibe `sorter/sensor/arrival` -> toma la foto -> la clasifica (IA de Hugging
Face o OpenCV, según VISION_MOTOR en .env) -> decide la salida (reglas.py) -> guarda
la foto -> publica `sorter/vision/result`.

La configuración (colores del grupo A, umbral) se lee por HTTP del PC-servidor
(SERVER_URL/api/settings) y cada foto se sube a él (/api/imagenes) para el dashboard.
Este nodo no toca la base de datos.

Además abre una ventana con la cámara en vivo: muestra el rectángulo de lo que
detecta, su color, la confianza y las manchas. Cuando el Arduino pide una foto,
la ventana muestra esa foto ~2,5 s con la salida asignada.

Uso (desde la carpeta ia/):
    python -m vision.clasificador                 # webcam real + ventana en vivo
    python -m vision.clasificador --sin-ventana   # webcam real, sin ventana
    python -m vision.clasificador --simular       # sin cámara: dibuja manzanas falsas

En la ventana: tecla q = cerrar la visión.
"""
import argparse
import random
import threading
import time
from datetime import datetime

import cv2
import numpy as np
import paho.mqtt.client as mqtt
import requests

from comun import config, topicos
from vision.analisis import cargar_calibracion, imagen_sintetica
from vision.modelo_ia import crear_motor
from vision.dibujo import dibujar_aviso_foto, dibujar_deteccion
from vision.reglas import decidir_salida

CACHE_SETTINGS_S = 5      # cada cuánto se vuelve a pedir la configuración al servidor
MOSTRAR_FOTO_S = 2.5      # cuánto tiempo queda en pantalla la foto de cada manzana
REFRESCO_VIVO_S = 0.1     # cada cuánto se analiza la cámara en vivo (la IA tarda ~20-50 ms en GPU)
VENTANA = "SortiBandLLM - vision (q = salir)"

# Configuración usada mientras el servidor no responde (degradación segura)
SETTINGS_POR_DEFECTO = {
    "grupo_a_colores": "rojo",
    "umbral_confianza": "0.6",
    "velocidad_mm_s": "30",
}


class NodoVision:
    def __init__(self, simular: bool, ventana: bool):
        self.simular = simular
        self.ventana = ventana
        self.calib = cargar_calibracion()
        self.settings = dict(SETTINGS_POR_DEFECTO)   # se actualiza en refrescar_settings()
        self.camara = None
        self.cuadro = None                # última imagen leída de la cámara
        self.lock = threading.Lock()      # MQTT y la ventana corren en hilos distintos
        self.ultima_foto = None           # (momento, imagen anotada) para mostrar en la ventana
        self.ultimo_vivo = (0.0, None)    # (momento, resultado) del análisis en vivo
        config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # Motor de clasificación: IA (CLIP) u OpenCV, con OpenCV de respaldo
        print(f"[VISION] Cargando motor '{config.VISION_MOTOR}'...")
        self.clasificar, self.etiqueta_motor, self.nombre_modelo = crear_motor(self.calib)
        print(f"[VISION] Motor listo: {self.etiqueta_motor}")

        if not simular:
            # CAP_DSHOW abre más rápido la webcam en Windows
            self.camara = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
            if not self.camara.isOpened():
                raise SystemExit(f"No se pudo abrir la webcam {config.CAMERA_INDEX}. Prueba con --simular.")

        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="vision_pc")
        self.cliente.on_connect = self.al_conectar
        self.cliente.on_message = self.al_recibir

    def leer_settings(self) -> dict:
        """Pide la configuración al PC-servidor por HTTP."""
        r = requests.get(f"{config.SERVER_URL}/api/settings", timeout=3)
        r.raise_for_status()
        return r.json()["settings"]

    def refrescar_settings(self):
        """Hilo aparte: relee la configuración cada pocos segundos.

        Va separado del camino crítico: si el servidor está lento o caído,
        la clasificación no espera; sigue con la última configuración conocida.
        """
        bd_ok = None
        origen = config.SERVER_URL
        while True:
            try:
                self.settings = self.leer_settings()
                if bd_ok is not True:
                    print(f"[CONFIG] Configuración leída de {origen}")
                bd_ok = True
            except Exception as error:  # noqa: BLE001 - una falla del servidor no debe detener la visión
                if bd_ok is not False:   # se avisa una sola vez, no cada 5 s
                    print(f"[AVISO] No se pudo leer la configuración de {origen} ({error}); "
                          "uso la última conocida")
                bd_ok = False
            time.sleep(CACHE_SETTINGS_S)

    def tomar_foto(self):
        if self.simular:
            color = random.choice(list(self.calib["rangos_hue"]))   # colores del perfil actual
            imagen = imagen_sintetica(color, con_mancha=random.random() < 0.2, forma=self.calib["producto"])
            return imagen, color
        # La cámara se lee todo el tiempo en correr(): la foto es el cuadro más reciente
        with self.lock:
            cuadro = None if self.cuadro is None else self.cuadro.copy()
        return cuadro, None

    def al_conectar(self, cliente, userdata, flags, reason_code, properties):
        modo = ("SIMULACIÓN" if self.simular else f"webcam {config.CAMERA_INDEX}") + f", producto: {config.PRODUCTO}"
        print(f"[MQTT] Conectado. Visión lista ({modo}).")
        cliente.subscribe(topicos.ARRIVAL, qos=1)

    def al_recibir(self, cliente, userdata, msg):
        datos = topicos.de_json(msg.payload)
        if datos is None or "piece_id" not in datos:
            print(f"[AVISO] Llegada inválida: {msg.payload!r}")
            return
        piece_id = datos["piece_id"]
        inicio = time.perf_counter()

        imagen, color_real = self.tomar_foto()
        if imagen is None:
            resultado = {"color": "desconocido", "is_defective": False, "confidence": 0.0, "bbox": None}
            image_path = None
            print(f"[ERROR] No se pudo capturar la foto de la manzana {piece_id}")
        else:
            resultado = self.clasificar(imagen)
            nombre = f"{datetime.now():%Y%m%d_%H%M%S}_{piece_id}.jpg"
            cv2.imwrite(str(config.IMAGES_DIR / nombre), imagen)   # se guarda sin dibujos (sirve de dataset)
            image_path = f"imagenes/{nombre}"   # ruta que sirve el servidor web
            # se sube la foto al servidor en otro hilo, sin atrasar el resultado
            threading.Thread(target=self.subir_foto, args=(nombre,), daemon=True).start()

        salida = decidir_salida(resultado["color"], resultado["is_defective"],
                                resultado["confidence"], self.settings)
        mensaje = {
            "piece_id": piece_id,
            "ts": topicos.ahora(),
            "color": resultado["color"],
            "is_defective": resultado["is_defective"],
            "confidence": resultado["confidence"],
            "output_channel": salida,
            "image_path": image_path,
            "model": resultado.get("modelo", "opencv"),   # quién decidió: la IA o OpenCV
        }
        cliente.publish(topicos.RESULT, topicos.a_json(mensaje), qos=1)

        ms = (time.perf_counter() - inicio) * 1000
        extra = f" (dibujada: {color_real})" if color_real else ""
        print(f"[RESULTADO] manzana {piece_id} ({resultado.get('motor', 'OpenCV')}): {resultado['color']}{extra}, "
              f"defectuosa={resultado['is_defective']}, conf={resultado['confidence']:.2f} "
              f"-> salida {salida} [{ms:.0f} ms]")

        # Para la ventana: la foto tomada, con el rectángulo y la salida
        if self.ventana and imagen is not None:
            vista = dibujar_deteccion(imagen, resultado)
            dibujar_aviso_foto(vista, piece_id, resultado, salida)
            with self.lock:
                self.ultima_foto = (time.time(), vista)

    def subir_foto(self, nombre: str):
        """Envía la foto al servidor (otro PC) para que el dashboard la muestre."""
        try:
            with open(config.IMAGES_DIR / nombre, "rb") as archivo:
                r = requests.post(f"{config.SERVER_URL}/api/imagenes",
                                  files={"archivo": (nombre, archivo, "image/jpeg")}, timeout=10)
            r.raise_for_status()
        except Exception as error:  # noqa: BLE001 - sin foto en el dashboard, la clasificación igual sigue
            print(f"[AVISO] No se pudo subir la foto {nombre} al servidor: {error}")

    def cuadro_para_ventana(self, cuadro):
        """Lo que se muestra: la foto recién tomada, o la cámara en vivo analizada."""
        with self.lock:
            foto = self.ultima_foto
        if foto and time.time() - foto[0] < MOSTRAR_FOTO_S:
            return foto[1]
        if cuadro is None:   # modo simulación: no hay cámara en vivo
            vista = np.full((480, 640, 3), 40, np.uint8)
            cv2.putText(vista, "Simulacion: esperando manzanas", (40, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 230), 2, cv2.LINE_AA)
            return vista
        # La IA no se corre en cada cuadro: cada REFRESCO_VIVO_S, y entre medio se reusa el resultado
        momento, resultado = self.ultimo_vivo
        if resultado is None or time.time() - momento >= REFRESCO_VIVO_S:
            resultado = self.clasificar(cuadro)
            self.ultimo_vivo = (time.time(), resultado)
        return dibujar_deteccion(cuadro, resultado)

    def correr(self):
        threading.Thread(target=self.refrescar_settings, daemon=True).start()
        self.cliente.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=10)
        self.cliente.loop_start()   # MQTT en su propio hilo; la ventana va en el hilo principal
        try:
            while True:
                cuadro = None
                if self.camara is not None:
                    ok, cuadro = self.camara.read()
                    if ok:
                        with self.lock:
                            self.cuadro = cuadro
                    else:
                        cuadro = None
                        time.sleep(0.05)
                if self.ventana:
                    cv2.imshow(VENTANA, self.cuadro_para_ventana(cuadro))
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                elif self.camara is None:
                    time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            print("\nCerrando visión")
            self.cliente.loop_stop()
            self.cliente.disconnect()
            if self.camara is not None:
                self.camara.release()
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Nodo de visión de SortiBandLLM")
    parser.add_argument("--simular", action="store_true", help="sin cámara: usa imágenes sintéticas")
    parser.add_argument("--sin-ventana", action="store_true", help="no abrir la ventana en vivo")
    args = parser.parse_args()
    NodoVision(args.simular, ventana=not args.sin_ventana).correr()


if __name__ == "__main__":
    main()
