"""Tópicos MQTT del sistema. Deben coincidir con CLAUDE.md y con el firmware.

Hay una copia de este archivo en servidor/comun y otra en ia/comun: si se cambia
un tópico, cambiarlo en las dos (y en el firmware).
"""
import json
import time

ARRIVAL = "sorter/sensor/arrival"      # Arduino: manzana centrada bajo la cámara
RESULT = "sorter/vision/result"        # PC: clasificación y salida asignada
COMMAND = "sorter/control/command"     # Servidor/web: start, stop, set_speed
STATUS = "sorter/control/status"       # Arduino: estado de la banda (retenido + Last Will)
DIVERTED = "sorter/control/diverted"   # Arduino: por qué salida se fue la manzana
SERVO = "sorter/control/servo"         # Arduino: confirma la prueba manual de un servo
SUPERVISION = "sorter/supervision/event"  # Supervisor LLM (fuera del MVP)
EMERGENCY = "sorter/emergency"         # Cualquier nodo

TODOS = "sorter/#"

# Colores que puede informar la visión en `sorter/vision/result` (perfiles manzana y lata).
# Esta lista está en servidor/comun y en ia/comun: si se cambia, cambiarla en las dos.
COLORES = ("rojo", "naranjo", "amarillo", "verde", "azul")


def ahora() -> float:
    """Marca de tiempo Unix en segundos (con decimales)."""
    return round(time.time(), 3)


def a_json(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False)


def de_json(payload: bytes) -> dict | None:
    """Convierte el payload a dict. Devuelve None si no es JSON válido."""
    try:
        datos = json.loads(payload.decode("utf-8"))
        return datos if isinstance(datos, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
