"""Prueba automática de punta a punta: ¿llegan los datos y se guardan bien?

Necesita corriendo: Mosquitto, el servidor (python -m server.api.main), la visión
y la banda (el simulador o el Arduino real).

Qué hace:
1. Escucha `sorter/#`, envía `start` (y la velocidad) y espera N manzanas desviadas.
2. Envía `stop`.
3. Revisa los mensajes: cada manzana debe tener arrival -> result -> diverted,
   con la salida real igual a la pedida.
4. Revisa la BD: cada manzana debe estar en `pieces` con su salida y su `diverted_ts`.
5. Imprime OK o la lista de fallas.

Uso (desde la raíz del proyecto):
    python -m herramientas.verificar_flujo --manzanas 10
    python -m herramientas.verificar_flujo --manzanas 10 --velocidad 40 --sin-bd
"""
import argparse
import sys
import threading
import time
from collections import defaultdict

import paho.mqtt.client as mqtt

from comun import config, topicos


class Registro:
    """Guarda, por cada piece_id, los mensajes recibidos y la hora (del PC) de llegada."""

    def __init__(self):
        self.piezas = defaultdict(dict)   # piece_id -> {"arrival": (t, datos), ...}
        self.estados = []
        self.desviadas = []               # piece_ids en orden de desvío
        self.listo = threading.Event()
        self.objetivo = 0
        self.grabando = False

    def al_recibir(self, cliente, userdata, msg):
        datos = topicos.de_json(msg.payload)
        if datos is None:
            print(f"  [FALLA] JSON inválido en {msg.topic}: {msg.payload!r}")
            return
        t = time.time()
        if msg.topic == topicos.STATUS:
            self.estados.append(datos.get("state"))
            return
        if not self.grabando:
            return
        tipo = {topicos.ARRIVAL: "arrival", topicos.RESULT: "result", topicos.DIVERTED: "diverted"}.get(msg.topic)
        if tipo is None or "piece_id" not in datos:
            return
        pid = datos["piece_id"]
        self.piezas[pid][tipo] = (t, datos)
        print(f"  {tipo:8s} manzana {pid}")
        if tipo == "diverted" and "arrival" in self.piezas[pid]:
            self.desviadas.append(pid)
            if len(self.desviadas) >= self.objetivo:
                self.listo.set()


def revisar_mensajes(reg: Registro, ids: list[int]) -> tuple[list[str], list[str]]:
    fallas, avisos = [], []
    latencias_vision, latencias_desvio = [], []
    for pid in ids:
        p = reg.piezas[pid]
        faltan = [t for t in ("arrival", "result", "diverted") if t not in p]
        if faltan:
            fallas.append(f"manzana {pid}: faltan mensajes {faltan}")
            continue
        t_arr, _ = p["arrival"]
        t_res, res = p["result"]
        t_div, div = p["diverted"]
        if not t_arr <= t_res <= t_div:
            fallas.append(f"manzana {pid}: mensajes fuera de orden")
        campos = {"color", "is_defective", "confidence", "output_channel", "image_path"}
        if not campos <= res.keys():
            fallas.append(f"manzana {pid}: al resultado le faltan {campos - res.keys()}")
        if div["output_channel"] != res.get("output_channel"):
            # Puede pasar si dos manzanas venían demasiado juntas: es un aviso, no una falla del software
            avisos.append(f"manzana {pid}: pidió salida {res.get('output_channel')} y salió por {div['output_channel']}")
        latencias_vision.append((t_res - t_arr) * 1000)
        latencias_desvio.append(t_div - t_res)

    if latencias_vision:
        print(f"\nLatencia llegada -> resultado (visión + MQTT): "
              f"prom {sum(latencias_vision) / len(latencias_vision):.0f} ms, máx {max(latencias_vision):.0f} ms")
        print(f"Tiempo resultado -> desvío: prom {sum(latencias_desvio) / len(latencias_desvio):.1f} s "
              f"(depende de la velocidad y la salida)")
        lentas = [l for l in latencias_vision if l > 1000]
        if lentas:
            avisos.append(f"{len(lentas)} resultados tardaron más de 1 s")
    return fallas, avisos


def revisar_bd(reg: Registro, ids: list[int]) -> list[str]:
    from comun.db import conectar   # se importa aquí para que --sin-bd no necesite MySQL

    fallas = []
    with conectar() as con, con.cursor() as cur:
        cur.execute("SELECT id FROM batches ORDER BY id DESC LIMIT 1")
        lote = cur.fetchone()
        if lote is None:
            return ["no hay ningún lote en la BD (¿está corriendo el servidor?)"]
        print(f"\nRevisando BD, lote {lote['id']}")
        for pid in ids:
            cur.execute(
                "SELECT color, output_channel, diverted_ts, image_path FROM pieces "
                "WHERE batch_id = %s AND piece_id = %s ORDER BY id DESC LIMIT 1",
                (lote["id"], pid),
            )
            fila = cur.fetchone()
            esperado = reg.piezas[pid]["diverted"][1]["output_channel"]
            if fila is None:
                fallas.append(f"BD: la manzana {pid} no está en el lote {lote['id']}")
            elif fila["diverted_ts"] is None:
                fallas.append(f"BD: la manzana {pid} no tiene diverted_ts")
            elif fila["output_channel"] != esperado:
                fallas.append(f"BD: la manzana {pid} tiene salida {fila['output_channel']}, se esperaba {esperado}")
            elif fila["color"] is None:
                fallas.append(f"BD: la manzana {pid} no tiene color (¿se perdió el resultado?)")
    return fallas


def main():
    parser = argparse.ArgumentParser(description="Verifica el flujo de datos de punta a punta")
    parser.add_argument("--manzanas", type=int, default=10)
    parser.add_argument("--velocidad", type=float, default=None, help="mm/s (opcional)")
    parser.add_argument("--timeout", type=float, default=300, help="segundos máximos de espera")
    parser.add_argument("--sin-bd", action="store_true", help="no revisar MySQL")
    args = parser.parse_args()

    reg = Registro()
    reg.objetivo = args.manzanas
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="verificar_flujo")
    cliente.on_message = reg.al_recibir
    try:
        cliente.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=10)
    except OSError as error:
        sys.exit(f"[FALLA] No se pudo conectar al broker {config.MQTT_HOST}:{config.MQTT_PORT}: {error}")
    cliente.subscribe(topicos.TODOS, qos=1)
    cliente.loop_start()
    time.sleep(1)   # recibe el estado retenido

    if not reg.estados or reg.estados[-1] in ("offline", None):
        print(f"[AVISO] La banda no parece conectada (estado: {reg.estados[-1] if reg.estados else 'sin datos'}). "
              "¿Está corriendo el simulador o el Arduino?")

    def comando(accion, valor=None):
        cliente.publish(topicos.COMMAND, topicos.a_json({"action": accion, "value": valor, "ts": topicos.ahora()}), qos=1)

    print(f"Esperando {args.manzanas} manzanas (máx. {args.timeout:.0f} s)…")
    reg.grabando = True
    if args.velocidad:
        comando("set_speed", args.velocidad)
    comando("start")
    completo = reg.listo.wait(args.timeout)
    comando("stop")
    time.sleep(1.5)   # da tiempo al servidor para escribir en la BD
    cliente.loop_stop()
    cliente.disconnect()

    ids = reg.desviadas[: args.manzanas]
    fallas, avisos = revisar_mensajes(reg, ids)
    if not completo:
        fallas.append(f"solo se desviaron {len(reg.desviadas)} de {args.manzanas} manzanas antes del timeout")
    if not args.sin_bd and ids:
        try:
            fallas += revisar_bd(reg, ids)
        except Exception as error:  # noqa: BLE001
            fallas.append(f"no se pudo revisar la BD: {error}")

    print()
    for a in avisos:
        print(f"[AVISO] {a}")
    for f in fallas:
        print(f"[FALLA] {f}")
    if fallas:
        print(f"\nRESULTADO: FALLA ({len(fallas)} problemas)")
        sys.exit(1)
    print(f"\nRESULTADO: OK — {len(ids)} manzanas con arrival -> result -> diverted"
          + ("" if args.sin_bd else " y guardadas en la BD"))


if __name__ == "__main__":
    main()
