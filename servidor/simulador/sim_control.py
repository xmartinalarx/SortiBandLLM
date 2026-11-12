"""Simulador del Arduino UNO R4 de control: reemplaza a la banda real para probar sin hardware.

Hace lo mismo que el firmware (firmware/control_uno_r4), con la misma lógica:
- Genera manzanas en el sensor IR cada cierta separación (en mm de banda).
- Sigue cada manzana por los mm que avanzó la banda (en el Arduino real son los
  pasos del motor). Así no depende de relojes ni del retardo de MQTT.
- Publica `arrival` cuando la manzana queda bajo la cámara, espera el `result`
  y mueve la paleta que corresponda; luego publica `diverted`.
- Obedece start / stop / set_speed y la parada de emergencia.
- Si se cae el broker, detiene la banda. El broker publica su Last Will (offline).

Uso (desde la raíz del proyecto):
    python -m simulador.sim_control
    python -m simulador.sim_control --separacion 330 --velocidad 30
"""
import argparse
import random
import time

import paho.mqtt.client as mqtt

from comun import config, topicos

# Distancias en mm (iguales a firmware/control_uno_r4/config.h). Calibrar con la banda real.
DIST_IR_A_CAMARA = 110      # sensor IR (x=170) -> centro del túnel (x=280)
MARGEN_SERVO = 30           # se cierra un poco antes: el servo tarda ~0,15 s en girar
CIERRE_P1 = 227 - MARGEN_SERVO   # desde la cámara: la paleta 1 debe estar cerrada a +227
APERTURA_P1 = 507                # +227 + ~280 mm que tarda en salir la manzana
CIERRE_P2 = 527 - MARGEN_SERVO
APERTURA_P2 = 807

VEL_MIN, VEL_MAX = 10, 40   # mm/s (el 28BYJ-48 llega a ~12 rpm)
TICK = 0.02                 # s entre actualizaciones (50 por segundo)


class Pieza:
    def __init__(self, piece_id: int, pos_ir: float):
        self.piece_id = piece_id
        self.pos_ir = pos_ir          # posición de la banda (mm) cuando cruzó el IR
        self.salida_pedida = None     # la que manda la visión (None = aún no llega)
        self.en_camara = False        # ya se publicó arrival
        self.paso_p1 = False          # ya pasó el punto de decisión de la paleta 1


class SimuladorBanda:
    def __init__(self, separacion: float, velocidad: float):
        self.separacion = separacion
        self.velocidad = velocidad
        self.estado = "stopped"       # running | stopped | emergency
        self.pos = 0.0                # mm que avanzó la banda desde que partió el programa
        self.pos_ultima_carga = -1e9
        self.siguiente_id = 1
        self.piezas: list[Pieza] = []
        # Posición de banda en la que se abre cada paleta (None = abierta)
        self.p1_abrir_en = None
        self.p2_abrir_en = None
        self.ultimo_status = 0.0

        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sim_control")
        # Last Will: si el simulador muere o pierde la conexión, el broker publica esto
        self.cliente.will_set(topicos.STATUS, topicos.a_json({"state": "offline"}), qos=1, retain=True)
        self.cliente.on_connect = self.al_conectar
        self.cliente.on_disconnect = self.al_desconectar
        self.cliente.on_message = self.al_recibir

    # ---------- MQTT ----------
    def al_conectar(self, cliente, userdata, flags, reason_code, properties):
        print(f"[MQTT] Conectado a {config.MQTT_HOST}:{config.MQTT_PORT}")
        cliente.subscribe([(topicos.COMMAND, 1), (topicos.RESULT, 1), (topicos.EMERGENCY, 1)])
        self.publicar_status()

    def al_desconectar(self, cliente, userdata, flags, reason_code, properties):
        # Regla del proyecto: sin broker, la banda se detiene
        if self.estado == "running":
            print("[MQTT] Conexión perdida: banda detenida")
            self.estado = "stopped"

    def al_recibir(self, cliente, userdata, msg):
        datos = topicos.de_json(msg.payload)
        if datos is None:
            print(f"[AVISO] JSON inválido en {msg.topic}")
            return
        if msg.topic == topicos.COMMAND:
            self.atender_comando(datos)
        elif msg.topic == topicos.RESULT:
            self.atender_resultado(datos)
        elif msg.topic == topicos.EMERGENCY:
            print(f"[EMERGENCIA] desde {datos.get('source')}: banda detenida")
            self.estado = "emergency"
            self.publicar_status()

    def atender_comando(self, datos: dict):
        accion = datos.get("action")
        if accion == "start":
            self.estado = "running"
        elif accion == "stop":
            self.estado = "stopped"
        elif accion == "servo":
            self.probar_servo(datos)
            return
        elif accion == "set_speed":
            try:
                self.velocidad = max(VEL_MIN, min(VEL_MAX, float(datos.get("value"))))
            except (TypeError, ValueError):
                print(f"[AVISO] Velocidad inválida: {datos.get('value')}")
        else:
            print(f"[AVISO] Comando desconocido: {accion}")
            return
        print(f"[CMD] {accion} -> estado={self.estado}, velocidad={self.velocidad} mm/s")
        self.publicar_status()

    def probar_servo(self, datos: dict):
        """Igual que el firmware: solo con la banda detenida; confirma en sorter/control/servo."""
        n, angulo = datos.get("servo"), datos.get("value")
        motivo = None
        if self.estado != "stopped":
            motivo = "la banda debe estar detenida"
        elif n not in (1, 2):
            motivo = "servo invalido (1 o 2)"
        elif not isinstance(angulo, (int, float)) or not 0 <= angulo <= 180:
            motivo = "angulo fuera de 0-180"
        respuesta = {"servo": n, "angle": angulo, "ok": motivo is None, "ts": topicos.ahora()}
        if motivo:
            respuesta["motivo"] = motivo
        self.publicar(topicos.SERVO, respuesta)
        print(f"[SERVO] {n} -> {angulo}°" if not motivo else f"[SERVO] rechazado: {motivo}")

    def atender_resultado(self, datos: dict):
        pieza = next((p for p in self.piezas if p.piece_id == datos.get("piece_id")), None)
        if pieza is None:
            print(f"[AVISO] Resultado de una manzana que no está en la banda: {datos.get('piece_id')}")
            return
        if pieza.paso_p1:
            print(f"[AVISO] Resultado tardío de la manzana {pieza.piece_id}: ya se decidió")
            return
        pieza.salida_pedida = int(datos.get("output_channel", 3))

    def publicar(self, topico: str, datos: dict, retain=False):
        self.cliente.publish(topico, topicos.a_json(datos), qos=1, retain=retain)

    def publicar_status(self):
        self.publicar(topicos.STATUS, {"state": self.estado, "speed": self.velocidad, "ts": topicos.ahora()}, retain=True)
        self.ultimo_status = time.time()

    def publicar_desvio(self, pieza: Pieza, salida: int, motivo: str):
        self.publicar(topicos.DIVERTED, {"piece_id": pieza.piece_id, "output_channel": salida, "ts": topicos.ahora()})
        print(f"[DESVÍO] manzana {pieza.piece_id} -> salida {salida} ({motivo})")
        self.piezas.remove(pieza)

    # ---------- Banda ----------
    def avanzar(self, dt: float):
        if self.estado != "running":
            return
        self.pos += self.velocidad * dt

        # Carga: una manzana nueva cruza el IR cada `separacion` mm (con algo de variación)
        if self.pos - self.pos_ultima_carga >= self.separacion:
            self.piezas.append(Pieza(self.siguiente_id, self.pos))
            self.siguiente_id += 1
            self.pos_ultima_carga = self.pos + random.uniform(0, 0.15 * self.separacion)

        # Abrir paletas cuando la última manzana desviada ya salió
        if self.p1_abrir_en is not None and self.pos >= self.p1_abrir_en:
            self.p1_abrir_en = None
            print("[PALETA 1] abierta")
        if self.p2_abrir_en is not None and self.pos >= self.p2_abrir_en:
            self.p2_abrir_en = None
            print("[PALETA 2] abierta")

        for pieza in list(self.piezas):
            self.procesar_pieza(pieza)

    def procesar_pieza(self, p: Pieza):
        recorrido = self.pos - p.pos_ir            # mm desde el IR
        desde_camara = recorrido - DIST_IR_A_CAMARA

        if not p.en_camara and desde_camara >= 0:
            p.en_camara = True
            self.publicar(topicos.ARRIVAL, {"piece_id": p.piece_id, "ts": topicos.ahora()})
            print(f"[LLEGADA] manzana {p.piece_id} bajo la cámara")

        # Punto de decisión de la paleta 1
        if not p.paso_p1 and desde_camara >= CIERRE_P1:
            p.paso_p1 = True
            if p.salida_pedida is None:
                p.salida_pedida = 3
                print(f"[AVISO] Sin resultado para la manzana {p.piece_id}: va a la salida 3")
            if self.p1_abrir_en is not None:
                # La paleta 1 sigue cerrada por la manzana anterior: esta también se desvía
                self.publicar_desvio(p, 1, "paleta 1 ocupada: manzanas demasiado juntas")
                return
            if p.salida_pedida == 1:
                self.p1_abrir_en = p.pos_ir + DIST_IR_A_CAMARA + APERTURA_P1
                print("[PALETA 1] cerrada")
                self.publicar_desvio(p, 1, "pedido por visión")
            return

        # Punto de decisión de la paleta 2
        if p.paso_p1 and desde_camara >= CIERRE_P2:
            if self.p2_abrir_en is not None:
                self.publicar_desvio(p, 2, "paleta 2 ocupada: manzanas demasiado juntas")
            elif p.salida_pedida == 2:
                self.p2_abrir_en = p.pos_ir + DIST_IR_A_CAMARA + APERTURA_P2
                print("[PALETA 2] cerrada")
                self.publicar_desvio(p, 2, "pedido por visión")
            else:
                self.publicar_desvio(p, 3, "sigue hasta el final")

    def correr(self):
        self.cliente.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=10)
        self.cliente.loop_start()   # MQTT en un hilo aparte (reconecta solo)
        print("Simulador listo. Envía 'start' desde el dashboard o con mosquitto_pub.")
        anterior = time.time()
        try:
            while True:
                time.sleep(TICK)
                ahora = time.time()
                self.avanzar(ahora - anterior)
                anterior = ahora
                if ahora - self.ultimo_status >= 2:   # estado periódico cada 2 s
                    self.publicar_status()
        except KeyboardInterrupt:
            print("\nCerrando simulador")
        finally:
            # Salida ordenada: se publica offline a mano (el Last Will solo se usa si muere)
            self.publicar(topicos.STATUS, {"state": "offline"}, retain=True)
            time.sleep(0.2)
            self.cliente.loop_stop()
            self.cliente.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Simulador del Arduino de control")
    parser.add_argument("--separacion", type=float, default=330, help="mm entre manzanas (mínimo ~310)")
    parser.add_argument("--velocidad", type=float, default=30, help="mm/s al partir")
    args = parser.parse_args()
    SimuladorBanda(args.separacion, args.velocidad).correr()


if __name__ == "__main__":
    main()
