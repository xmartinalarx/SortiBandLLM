"""Configuración leída desde variables de entorno (archivo .env en la raíz).

Nada de IPs, claves ni rutas escritas en el código: todo sale de aquí.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# Broker MQTT (Mosquitto)
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Base de datos MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "clasifiot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "clasifiot")

# Producto que se clasifica: "manzana" o "lata" (latas de bebida, para probar)
PRODUCTO = os.getenv("PRODUCTO", "manzana").strip().lower()

# Visión
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))   # 0 = webcam integrada (por ahora)
# Carpeta donde se guardan las fotos de cada manzana (la BD guarda solo la ruta)
IMAGES_DIR = (RAIZ / os.getenv("IMAGES_DIR", "data/imagenes")).resolve()

# Motor de visión: "ia" (modelo de Hugging Face) u "opencv" (reglas de color)
VISION_MOTOR = os.getenv("VISION_MOTOR", "opencv").strip().lower()
HF_MODELO = os.getenv("HF_MODELO", "openai/clip-vit-base-patch32").strip()

# Dirección del servidor web cuando la visión corre en OTRO PC (ej. http://10.157.200.50:8000).
# Vacío = mismo PC: la visión lee la configuración de MySQL y guarda las fotos donde las sirve el servidor.
SERVER_URL = os.getenv("SERVER_URL", "").strip().rstrip("/")

# Servidor web
API_PORT = int(os.getenv("API_PORT", "8000"))
