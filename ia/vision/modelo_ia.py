"""Clasificación con IA de Hugging Face: CLIP en modo "zero-shot".

CLIP compara la imagen con frases ("a photo of a red apple", "a photo of a rotten
apple"...) y dice cuál calza mejor. No necesita entrenamiento: las frases están en
vision/prompts_ia.json y se pueden ajustar.

Pasos para cada imagen:
1. Recorte: OpenCV (mascara_manzana) busca el producto sobre el fondo claro y se
   recorta con margen. Con el recorte CLIP acierta más. Si no encuentra nada, se
   usa la imagen completa.
2. Color: CLIP elige entre las frases de color y las de "nada" (mesa vacía, persona,
   mano). Si gana una de "nada", el color es "desconocido".
3. Estado: CLIP elige entre "sana" y "defectuosa"; es defectuosa si esa frase
   supera el umbral.

Devuelve el MISMO contrato que vision/analisis.py::clasificar_imagen (color,
is_defective, confidence, bbox), así que el resto del sistema no cambia.

Degradación segura: crear_motor() vuelve a OpenCV si falta torch/transformers,
si el modelo no se puede cargar o si la IA falla en una imagen.
"""
import json
import threading
from pathlib import Path

import cv2
import numpy as np

from comun import config
from vision.analisis import clasificar_imagen, mascara_manzana

ARCHIVO_PROMPTS = Path(__file__).with_name("prompts_ia.json")
MARGEN_RECORTE = 0.15   # se agrega 15 % alrededor del producto al recortar


class ClasificadorCLIP:
    def __init__(self, calib: dict, modelo: str | None = None, pipeline_fn=None):
        """pipeline_fn permite probar sin descargar el modelo (tests)."""
        self.calib = calib
        self.producto = calib.get("producto", config.PRODUCTO)
        self.nombre_modelo = modelo or config.HF_MODELO
        prompts = json.loads(ARCHIVO_PROMPTS.read_text(encoding="utf-8"))
        if self.producto not in prompts:
            raise ValueError(f"No hay frases para el producto {self.producto!r} en {ARCHIVO_PROMPTS.name}")
        p = prompts[self.producto]
        self.frases_color = p["color"]                 # {"rojo": "a photo of a red apple", ...}
        self.frases_nada = p["nada"]                   # lista de frases "no hay producto"
        self.frases_estado = p.get("estado")           # {"sana": ..., "defectuosa": ...} o None
        self.umbral_defecto = float(p.get("umbral_defecto", 0.6))
        self.lock = threading.Lock()                   # la usan la ventana y el hilo de MQTT

        if pipeline_fn is not None:
            self.pipe = pipeline_fn
            self.dispositivo = "prueba"
        else:
            import torch
            from transformers import pipeline

            usar_gpu = torch.cuda.is_available()
            self.dispositivo = "GPU" if usar_gpu else "CPU"
            opciones = {"device": 0 if usar_gpu else -1}
            if usar_gpu:
                opciones["dtype"] = torch.float16   # la mitad de memoria y más rápido en la GPU
            self.pipe = pipeline("zero-shot-image-classification", model=self.nombre_modelo, **opciones)
        self.etiqueta = f"IA {self.nombre_modelo.split('/')[-1]} ({self.dispositivo})"

    def _consultar(self, imagen_pil, frases: list[str]) -> dict[str, float]:
        """Probabilidad de cada frase (suman 1)."""
        respuesta = self.pipe(imagen_pil, candidate_labels=frases)
        return {r["label"]: float(r["score"]) for r in respuesta}

    def _recortar(self, imagen_bgr: np.ndarray):
        hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)
        mascara = mascara_manzana(hsv, self.calib)
        if mascara is None:
            return imagen_bgr, None
        x, y, w, h = cv2.boundingRect(mascara)
        m = int(MARGEN_RECORTE * max(w, h))
        alto, ancho = imagen_bgr.shape[:2]
        x0, y0, x1, y1 = max(x - m, 0), max(y - m, 0), min(x + w + m, ancho), min(y + h + m, alto)
        return imagen_bgr[y0:y1, x0:x1], (int(x), int(y), int(w), int(h))

    def clasificar(self, imagen_bgr: np.ndarray) -> dict:
        from PIL import Image

        recorte, bbox = self._recortar(imagen_bgr)
        imagen = Image.fromarray(cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB))

        with self.lock:
            probs = self._consultar(imagen, list(self.frases_color.values()) + list(self.frases_nada))
            p_nada = sum(probs[f] for f in self.frases_nada)
            por_color = {color: probs[frase] for color, frase in self.frases_color.items()}
            color = max(por_color, key=por_color.get)

            resultado = {"modelo": self.nombre_modelo, "motor": self.etiqueta,
                         "probabilidades": {**por_color, "nada": p_nada},
                         "mascara": None, "manchas": None, "prob_defecto": None}

            if p_nada > por_color[color]:
                # Lo más probable es que no haya producto a la vista
                resultado.update(color="desconocido", is_defective=False, confidence=0.0, bbox=None)
                return resultado

            is_defective = False
            if self.frases_estado:
                estado = self._consultar(imagen, [self.frases_estado["sana"], self.frases_estado["defectuosa"]])
                prob_defecto = estado[self.frases_estado["defectuosa"]]
                is_defective = prob_defecto >= self.umbral_defecto
                resultado["prob_defecto"] = round(prob_defecto, 3)

        # La confianza es la probabilidad del color entre los colores (sin contar "nada")
        total_colores = sum(por_color.values()) or 1.0
        resultado.update(color=color, is_defective=bool(is_defective),
                         confidence=round(por_color[color] / total_colores, 3), bbox=bbox)
        return resultado


def crear_motor(calib: dict, motor: str | None = None, cargar_ia=ClasificadorCLIP):
    """Devuelve (funcion_clasificar, etiqueta, nombre_modelo) según VISION_MOTOR.

    Con "ia" intenta cargar CLIP; si no puede, avisa y usa OpenCV. Si la IA falla
    con una imagen puntual, esa imagen se clasifica con OpenCV.
    """
    motor = (motor or config.VISION_MOTOR).lower()

    def opencv(imagen):
        r = clasificar_imagen(imagen, calib)
        r.setdefault("modelo", "opencv")
        r.setdefault("motor", "OpenCV (HSV)")
        return r

    if motor != "ia":
        return opencv, "OpenCV (HSV)", "opencv"
    try:
        ia = cargar_ia(calib)
    except Exception as error:  # noqa: BLE001 - sin IA la banda igual debe clasificar
        print(f"[AVISO] No se pudo cargar la IA ({error}). Se usa OpenCV.")
        return opencv, "OpenCV (HSV) - IA no disponible", "opencv"

    def con_respaldo(imagen):
        try:
            return ia.clasificar(imagen)
        except Exception as error:  # noqa: BLE001
            print(f"[AVISO] La IA falló con una imagen ({error}); se usa OpenCV para esta.")
            return opencv(imagen)

    return con_respaldo, ia.etiqueta, ia.nombre_modelo
