"""Conexión a MySQL y lectura de la configuración (tabla settings).

Se abre una conexión nueva por operación: es simple, evita problemas entre hilos
(MQTT y web corren en hilos distintos) y el volumen es bajo (~10 manzanas/min).
"""
import pymysql

from comun import config

# Valores usados si la BD no responde (degradación segura)
SETTINGS_POR_DEFECTO = {
    "grupo_a_colores": "rojo",
    "umbral_confianza": "0.6",
    "velocidad_mm_s": "30",
}


def conectar():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=3,
    )


def leer_settings() -> dict:
    """Devuelve la configuración como dict {clave: valor (texto)}."""
    with conectar() as con, con.cursor() as cur:
        cur.execute("SELECT `key`, `value` FROM settings")
        filas = cur.fetchall()
    settings = dict(SETTINGS_POR_DEFECTO)
    settings.update({f["key"]: f["value"] for f in filas})
    return settings


def guardar_setting(clave: str, valor: str) -> None:
    with conectar() as con, con.cursor() as cur:
        cur.execute(
            "INSERT INTO settings (`key`, `value`) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
            (clave, valor),
        )
