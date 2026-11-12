"""Configuración del PC-servidor, leída desde variables de entorno (archivo servidor/.env).

Nada de IPs, claves ni rutas escritas en el código: todo sale de aquí.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent   # carpeta servidor/
load_dotenv(RAIZ / ".env")

# Broker MQTT (Mosquitto, en este mismo PC)
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Base de datos MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "clasifiot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "clasifiot")

# Producto que se clasifica ("manzana" o "lata"): se anota en cada lote
PRODUCTO = os.getenv("PRODUCTO", "manzana").strip().lower()

# Carpeta donde quedan las fotos que sube el PC-IA (la BD guarda solo la ruta)
IMAGES_DIR = (RAIZ / os.getenv("IMAGES_DIR", "data/imagenes")).resolve()

# Servidor web (API + dashboard)
API_PORT = int(os.getenv("API_PORT", "8000"))
