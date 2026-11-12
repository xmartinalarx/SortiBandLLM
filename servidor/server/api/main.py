"""Servidor web de SortiBandLLM: API REST + dashboard + puente MQTT.

Uso (desde la raíz del proyecto):
    python -m server.api.main
y abrir http://localhost:8000 (o la IP del PC desde el celular).
"""
import re
from contextlib import asynccontextmanager
from typing import Literal

import pymysql
import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from comun import config
from comun.db import guardar_setting, leer_settings
from server.api import db
from server.api.mqtt_bridge import PuenteMQTT
from comun.topicos import COLORES

puente = PuenteMQTT()
VEL_MIN, VEL_MAX = 10, 40    # mm/s, igual que en el firmware (28BYJ-48)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    puente.iniciar()
    yield
    puente.detener()


app = FastAPI(title="SortiBandLLM", lifespan=ciclo_de_vida)


@app.exception_handler(pymysql.err.OperationalError)
async def bd_caida(request: Request, error: pymysql.err.OperationalError):
    # Si MySQL no responde, la API contesta 503 y el dashboard lo muestra
    return JSONResponse(status_code=503, content={"detail": f"Base de datos sin conexión: {error}"})


# ---------- Lectura ----------
@app.get("/api/estado")
def estado():
    return {
        "banda": puente.estado_banda,
        "servos": puente.servos,
        "mqtt_conectado": puente.conectado,
        "lote_abierto": puente.lote_id,
        "error_bd": puente.ultimo_error_bd,
    }


@app.get("/api/estadisticas")
def estadisticas():
    lote = db.lote_actual_o_ultimo()
    if lote is None:
        return {"lote": None, "total": 0}
    return {"lote": lote, **db.estadisticas(lote["id"])}


@app.get("/api/piezas")
def piezas(limite: int = 20):
    return db.ultimas_piezas(min(limite, 200))


@app.get("/api/rechazadas")
def rechazadas(limite: int = 12):
    return db.ultimas_rechazadas(min(limite, 50))


@app.get("/api/settings")
def obtener_settings():
    return {"settings": leer_settings(), "colores": COLORES}


# ---------- Control ----------
class Comando(BaseModel):
    action: Literal["start", "stop", "set_speed"]
    value: float | None = None


@app.post("/api/comando")
def comando(cmd: Comando):
    if cmd.action == "set_speed":
        if cmd.value is None or not VEL_MIN <= cmd.value <= VEL_MAX:
            raise HTTPException(400, f"La velocidad debe estar entre {VEL_MIN} y {VEL_MAX} mm/s")
    if not puente.conectado:
        raise HTTPException(503, "El servidor no está conectado al broker MQTT")
    puente.enviar_comando(cmd.action, cmd.value)
    return {"ok": True}


class PruebaServo(BaseModel):
    servo: Literal[1, 2]                 # 1 = paleta 1 (D9), 2 = paleta 2 (D10)
    angle: int = Field(ge=0, le=180)


@app.post("/api/servo")
def probar_servo(prueba: PruebaServo):
    """Mueve un servo a mano para probarlo. El Arduino solo lo acepta con la banda detenida
    y confirma en sorter/control/servo (se ve en /api/estado -> servos)."""
    if not puente.conectado:
        raise HTTPException(503, "El servidor no está conectado al broker MQTT")
    if puente.estado_banda.get("state") == "running":
        raise HTTPException(409, "Detén la banda antes de probar los servos")
    puente.probar_servo(prueba.servo, prueba.angle)
    return {"ok": True}


NOMBRE_FOTO = re.compile(r"^[\w.-]+\.jpg$")   # solo nombres simples: evita escribir fuera de la carpeta
MAX_FOTO_BYTES = 5_000_000


@app.post("/api/imagenes")
async def subir_imagen(archivo: UploadFile = File(...)):
    """Recibe la foto de una manzana desde el PC de la IA (cuando corre en otro equipo)
    y la guarda donde el dashboard la muestra (/imagenes)."""
    nombre = archivo.filename or ""
    if not NOMBRE_FOTO.match(nombre):
        raise HTTPException(400, "Nombre de foto inválido: debe ser algo como 20261106_101500_3.jpg")
    datos = await archivo.read()
    if len(datos) > MAX_FOTO_BYTES:
        raise HTTPException(413, "La foto pesa más de 5 MB")
    (config.IMAGES_DIR / nombre).write_bytes(datos)
    return {"ok": True, "image_path": f"imagenes/{nombre}"}


@app.post("/api/emergencia")
def emergencia():
    if not puente.conectado:
        raise HTTPException(503, "Sin broker MQTT: usar la parada de emergencia física")
    puente.enviar_emergencia()
    return {"ok": True}


class Settings(BaseModel):
    grupo_a_colores: list[str]
    umbral_confianza: float


@app.put("/api/settings")
def guardar_settings(s: Settings):
    invalidos = [c for c in s.grupo_a_colores if c not in COLORES]
    if invalidos:
        raise HTTPException(400, f"Colores desconocidos: {invalidos}")
    if not 0 <= s.umbral_confianza <= 1:
        raise HTTPException(400, "El umbral de confianza debe estar entre 0 y 1")
    guardar_setting("grupo_a_colores", ",".join(s.grupo_a_colores))
    guardar_setting("umbral_confianza", str(s.umbral_confianza))
    return {"ok": True}


# ---------- Archivos estáticos (al final, para no tapar /api) ----------
config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/imagenes", StaticFiles(directory=config.IMAGES_DIR), name="imagenes")
app.mount("/", StaticFiles(directory=config.RAIZ / "web", html=True), name="web")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.API_PORT)
