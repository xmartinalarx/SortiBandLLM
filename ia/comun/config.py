"""Configuración del PC-IA, leída desde variables de entorno (archivo ia/.env).

Nada de IPs, claves ni rutas escritas en el código: todo sale de aquí.
El PC-IA no toca la base de datos: todo lo que necesita del servidor lo pide por HTTP.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent   # carpeta ia/
load_dotenv(RAIZ / ".env")

# Broker MQTT: corre en el PC-servidor (poner su IP; ver con ipconfig en ese PC)
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Dirección del PC-servidor: de ahí se lee la configuración (/api/settings)
# y ahí se sube cada foto (/api/imagenes). Ej.: http://10.157.200.37:8000
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000").strip().rstrip("/")

# Producto que se clasifica: "manzana" o "lata" (latas de bebida, para probar)
PRODUCTO = os.getenv("PRODUCTO", "manzana").strip().lower()

# Cámara
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))   # 0 = webcam integrada (por ahora)
# Carpeta donde se guarda una copia de cada foto (sirve de dataset)
IMAGES_DIR = (RAIZ / os.getenv("IMAGES_DIR", "data/imagenes")).resolve()

# Motor de visión: "ia" (modelo de Hugging Face) u "opencv" (reglas de color)
VISION_MOTOR = os.getenv("VISION_MOTOR", "opencv").strip().lower()
HF_MODELO = os.getenv("HF_MODELO", "openai/clip-vit-base-patch32").strip()
