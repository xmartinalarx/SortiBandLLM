"""Puente entre MQTT y la base de datos.

Escucha todos los tópicos `sorter/#` y guarda cada manzana en MySQL. También
publica los comandos que llegan desde el dashboard.

- arrival   -> crea la fila de la manzana
- result    -> completa color, defecto, confianza, salida pedida y foto
- diverted  -> guarda la salida real y la hora del desvío
- command   -> start abre un lote; stop lo cierra; set_speed guarda la velocidad
- emergency -> cierra el lote
- status    -> se guarda en memoria para mostrarlo en el dashboard

Si la BD falla, se informa por consola y el puente sigue funcionando.
"""
import threading

import paho.mqtt.client as mqtt

from comun import config, topicos
from comun.db import guardar_setting
from server.api import db


class PuenteMQTT:
    def __init__(self):
        self.estado_banda = {"state": "desconocido"}
        self.servos = {}    # última confirmación del Arduino por servo: {"1": {...}, "2": {...}}
        self.conectado = False
        self.ultimo_error_bd = None
        self.lote_id = None
        self._lock = threading.Lock()   # los callbacks MQTT y la web corren en hilos distintos

        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="servidor_api")
        self.cliente.on_connect = self.al_conectar
        self.cliente.on_disconnect = self.al_desconectar
        self.cliente.on_message = self.al_recibir

    # ---------- Ciclo de vida ----------
    def iniciar(self):
        try:
            self.lote_id = db.lote_abierto()   # si el servidor se reinició con un lote abierto
        except Exception as error:  # noqa: BLE001
            self._error_bd("leer lote abierto", error)
        # connect_async + loop_start: no bloquea si el broker aún no está arriba; reintenta solo
        self.cliente.connect_async(config.MQTT_HOST, config.MQTT_PORT, keepalive=10)
        self.cliente.loop_start()

    def detener(self):
        self.cliente.loop_stop()
        self.cliente.disconnect()

    # ---------- MQTT ----------
    def al_conectar(self, cliente, userdata, flags, reason_code, properties):
        self.conectado = True
        print(f"[MQTT] Servidor conectado a {config.MQTT_HOST}:{config.MQTT_PORT}")
        cliente.subscribe(topicos.TODOS, qos=1)

    def al_desconectar(self, cliente, userdata, flags, reason_code, properties):
        self.conectado = False
        print("[MQTT] Servidor desconectado del broker (reintentando)")

    def al_recibir(self, cliente, userdata, msg):
        datos = topicos.de_json(msg.payload)
        if datos is None:
            print(f"[AVISO] JSON inválido en {msg.topic}: {msg.payload!r}")
            return
        try:
            with self._lock:
                self._procesar(msg.topic, datos)
        except Exception as error:  # noqa: BLE001 - un mensaje malo o la BD caída no deben botar el puente
            self._error_bd(msg.topic, error)

    def _procesar(self, topico: str, datos: dict):
        if topico == topicos.STATUS:
            self.estado_banda = datos
            return   # no toca la BD

        if topico == topicos.SERVO:   # confirmación de una prueba manual (no se guarda en la BD)
            self.servos[str(datos.get("servo"))] = {**datos, "recibido": topicos.ahora()}
            return

        if topico == topicos.ARRIVAL:
            if self.lote_id is None:   # llegó una manzana sin start previo: se abre un lote igual
                self.lote_id = db.abrir_lote()
            db.registrar_llegada(self.lote_id, int(datos["piece_id"]))

        elif topico == topicos.RESULT:
            db.registrar_resultado(self.lote_id, datos)

        elif topico == topicos.DIVERTED:
            db.registrar_desvio(self.lote_id, int(datos["piece_id"]), int(datos["output_channel"]))

        elif topico == topicos.COMMAND:
            accion = datos.get("action")
            if accion == "start" and self.lote_id is None:
                self.lote_id = db.abrir_lote()
                print(f"[LOTE] Abierto lote {self.lote_id}")
            elif accion == "stop":
                self._cerrar_lote()
            elif accion == "set_speed":
                guardar_setting("velocidad_mm_s", str(datos.get("value")))

        elif topico == topicos.EMERGENCY:
            print(f"[EMERGENCIA] desde {datos.get('source')}")
            self._cerrar_lote()

        self.ultimo_error_bd = None

    def _cerrar_lote(self):
        if self.lote_id is not None:
            db.cerrar_lote(self.lote_id)
            print(f"[LOTE] Cerrado lote {self.lote_id}")
            self.lote_id = None

    def _error_bd(self, contexto: str, error: Exception):
        self.ultimo_error_bd = f"{contexto}: {error}"
        print(f"[ERROR] {self.ultimo_error_bd}")

    # ---------- Publicar desde el dashboard ----------
    def enviar_comando(self, accion: str, valor=None):
        mensaje = {"action": accion, "value": valor, "ts": topicos.ahora()}
        self.cliente.publish(topicos.COMMAND, topicos.a_json(mensaje), qos=1)

    def probar_servo(self, servo: int, angulo: int):
        mensaje = {"action": "servo", "servo": servo, "value": angulo, "ts": topicos.ahora()}
        self.cliente.publish(topicos.COMMAND, topicos.a_json(mensaje), qos=1)

    def enviar_emergencia(self, origen: str = "dashboard"):
        self.cliente.publish(topicos.EMERGENCY, topicos.a_json({"source": origen, "ts": topicos.ahora()}), qos=1)
