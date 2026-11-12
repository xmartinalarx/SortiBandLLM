"""Análisis de una foto del producto con OpenCV (HSV). No usa cámara ni MQTT.

Pasos:
1. Separar el producto del fondo: el túnel es blanco mate (saturación baja), el
   producto tiene color (saturación alta). Se toma el contorno más grande y se
   rellena, para incluir también las manchas oscuras de adentro.
2. Color: se cuentan los píxeles del producto dentro de cada rango de tono (H).
   El color es el rango con más píxeles; la confianza es la fracción que ocupa.
3. Defecto: fracción del producto con zonas bastante más oscuras que su alrededor
   (manchas). Las sombras suaves por luz despareja no cuentan.

Hay un perfil por producto (PRODUCTO en .env): "manzana" o "lata" (latas de bebida,
para probar el sistema mientras no hay manzanas). Cambiar de producto = cambiar el
perfil; el resto del sistema no cambia.

Los umbrales se calibran con el producto real y la luz del túnel
(vision/calibrar_hsv.py) y se guardan en vision/calibracion_<producto>.json.
"""
import json
from pathlib import Path

import cv2
import numpy as np

from comun import config

PERFILES = {
    "manzana": {
        "fondo_s_min": 60,          # S mayor que esto = producto (el fondo blanco tiene S baja)
        "fondo_v_min": 40,          # descarta sombras muy negras del fondo
        "area_min": 3000,           # px: contornos más chicos no son un producto
        "detectar_defectos": True,
        "defecto_ratio": 0.6,       # mancha = píxel con brillo < 60 % del de su alrededor
        "defecto_fraccion": 0.03,   # más de 3 % de la manzana con manchas = defectuosa
        # Rangos de tono en OpenCV (H va de 0 a 179). El rojo da la vuelta: dos tramos.
        "rangos_hue": {
            "rojo": [[0, 10], [170, 179]],
            "amarillo": [[20, 34]],
            "verde": [[35, 85]],
        },
    },
    "lata": {
        "fondo_s_min": 70,
        "fondo_v_min": 40,
        "area_min": 3000,
        # Las letras y logos oscuros de la etiqueta parecerían manchas: no se buscan defectos
        "detectar_defectos": False,
        "defecto_ratio": 0.6,
        "defecto_fraccion": 0.03,
        "rangos_hue": {
            "rojo": [[0, 8], [170, 179]],    # Coca-Cola
            "naranjo": [[9, 20]],            # Fanta
            "amarillo": [[21, 34]],
            "verde": [[35, 85]],             # Sprite
            "azul": [[86, 130]],             # Pepsi
        },
    },
}

# Se mantiene para las pruebas y para quien importe el nombre anterior
CALIBRACION_POR_DEFECTO = PERFILES["manzana"]


def archivo_calibracion(producto: str) -> Path:
    return Path(__file__).with_name(f"calibracion_{producto}.json")


def cargar_calibracion(producto: str | None = None) -> dict:
    producto = producto or config.PRODUCTO
    if producto not in PERFILES:
        raise SystemExit(f"PRODUCTO desconocido: {producto!r}. Opciones: {', '.join(PERFILES)}")
    calib = json.loads(json.dumps(PERFILES[producto]))   # copia profunda
    calib["producto"] = producto
    archivo = archivo_calibracion(producto)
    if archivo.exists():
        calib.update(json.loads(archivo.read_text(encoding="utf-8")))
    return calib


def guardar_calibracion(calib: dict) -> None:
    producto = calib.get("producto", config.PRODUCTO)
    archivo_calibracion(producto).write_text(json.dumps(calib, indent=2, ensure_ascii=False), encoding="utf-8")


def mascara_manzana(hsv: np.ndarray, calib: dict) -> np.ndarray | None:
    """Máscara (0/255) con la manzana rellena, o None si no se encuentra ninguna."""
    s, v = hsv[:, :, 1], hsv[:, :, 2]
    con_color = ((s > calib["fondo_s_min"]) & (v > calib["fondo_v_min"])).astype(np.uint8) * 255
    # Limpia puntitos sueltos
    con_color = cv2.morphologyEx(con_color, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contornos, _ = cv2.findContours(con_color, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None
    mayor = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(mayor) < calib["area_min"]:
        return None

    mascara = np.zeros(con_color.shape, np.uint8)
    cv2.drawContours(mascara, [mayor], -1, 255, thickness=cv2.FILLED)
    # Se encoge un poco para no contar la sombra del borde como mancha
    return cv2.erode(mascara, np.ones((7, 7), np.uint8))


def manchas_locales(v: np.ndarray, mascara: np.ndarray, calib: dict) -> np.ndarray:
    """Píxeles (bool) bastante más oscuros que el promedio de su vecindario dentro del producto.

    El "vecindario" es un desenfoque grande calculado SOLO con píxeles del producto
    (convolución normalizada), para que el fondo blanco no aclare los bordes.
    """
    dentro = mascara > 0
    x, y, w, h = cv2.boundingRect(mascara)
    k = max(15, (min(w, h) // 3) | 1)          # tamaño impar: ~1/3 del producto
    vf = v.astype(np.float32) * dentro
    peso = cv2.GaussianBlur(dentro.astype(np.float32), (k, k), 0)
    vecindario = cv2.GaussianBlur(vf, (k, k), 0) / np.maximum(peso, 1e-3)
    oscuro = dentro & (v < calib.get("defecto_ratio", 0.6) * vecindario)
    # Se quitan puntitos sueltos (ruido de la cámara, brillos)
    oscuro = cv2.morphologyEx(oscuro.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
    return oscuro


def clasificar_imagen(imagen_bgr: np.ndarray, calib: dict | None = None) -> dict:
    """Devuelve {color, is_defective, confidence, bbox, mascara, manchas}.

    Este es el "contrato" del clasificador: recibe una imagen BGR y devuelve al menos
    color, is_defective, confidence y bbox (x, y, ancho, alto, o None si no hay manzana).
    Para usar un modelo de Hugging Face más adelante, basta con otra función que
    devuelva estas mismas claves; el resto del sistema no cambia.
    """
    calib = calib or cargar_calibracion()
    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)
    mascara = mascara_manzana(hsv, calib)
    if mascara is None:
        return {"color": "desconocido", "is_defective": False, "confidence": 0.0,
                "bbox": None, "mascara": None, "manchas": None}

    h, v = hsv[:, :, 0], hsv[:, :, 2]
    dentro = mascara > 0
    total = int(dentro.sum())

    # Manchas = zonas oscuras COMPARADAS CON SU ALREDEDOR dentro del producto.
    # Así una sombra (degradado suave, por luz despareja) no cuenta como defecto,
    # pero un punto más oscuro que la piel que lo rodea sí.
    manchas = manchas_locales(v, mascara, calib)
    detectar = calib.get("detectar_defectos", True)
    is_defective = detectar and bool(manchas.sum() / total > calib["defecto_fraccion"])

    # Color: solo con la parte clara (sin los píxeles oscuros)
    sana = dentro & ~manchas
    total_sana = max(int(sana.sum()), 1)
    conteos = {}
    for color, rangos in calib["rangos_hue"].items():
        en_rango = np.zeros(h.shape, bool)
        for bajo, alto in rangos:
            en_rango |= (h >= bajo) & (h <= alto)
        conteos[color] = int((sana & en_rango).sum())

    color = max(conteos, key=conteos.get)
    confidence = round(conteos[color] / total_sana, 3)
    bbox = tuple(int(n) for n in cv2.boundingRect(mascara))   # (x, y, ancho, alto)
    return {"color": color, "is_defective": is_defective, "confidence": confidence, "bbox": bbox,
            "mascara": mascara, "manchas": manchas.astype(np.uint8) * 255 if detectar else None}


COLORES_BGR_SINTETICOS = {
    "rojo": (40, 30, 190), "naranjo": (20, 120, 240), "amarillo": (40, 200, 220),
    "verde": (50, 170, 70), "azul": (190, 90, 30),
}


def imagen_sintetica(color: str, con_mancha: bool, semilla: int | None = None,
                     forma: str = "manzana") -> np.ndarray:
    """Dibuja un producto falso sobre fondo blanco (círculo = manzana, rectángulo = lata).
    Se usa en el modo simulación y en los tests."""
    rng = np.random.default_rng(semilla)
    img = np.full((480, 640, 3), 235, np.uint8)
    centro = (320 + int(rng.integers(-40, 40)), 240 + int(rng.integers(-30, 30)))
    radio = int(rng.integers(110, 140))
    if forma == "lata":
        ancho, alto = radio, int(radio * 1.7)   # lata vista de lado: más alta que ancha
        x0, y0 = centro[0] - ancho // 2, max(centro[1] - alto // 2, 10)
        cv2.rectangle(img, (x0, y0), (x0 + ancho, min(y0 + alto, 470)), COLORES_BGR_SINTETICOS[color], -1)
        cv2.putText(img, "COLA", (x0 + 8, centro[1]), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (20, 20, 20), 4)
    else:
        cv2.circle(img, centro, radio, COLORES_BGR_SINTETICOS[color], thickness=-1)
    if con_mancha and forma != "lata":
        mancha = (centro[0] + int(rng.integers(-40, 40)), centro[1] + int(rng.integers(-40, 40)))
        cv2.circle(img, mancha, int(rng.integers(28, 40)), (25, 30, 35), thickness=-1)
    ruido = rng.normal(0, 6, img.shape)
    return np.clip(img + ruido, 0, 255).astype(np.uint8)
