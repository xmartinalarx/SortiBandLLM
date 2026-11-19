"""Clasificación con IA de Hugging Face (SigLIP 2 de Google; también acepta CLIP).

El modelo convierte la foto en un vector que resume lo que se ve, y cada frase
("una foto de una manzana roja", "una manzana con un golpe o machucón"...) en otro
vector. Mientras más se parecen los dos vectores, más calza la frase con la foto.
No necesita entrenamiento: las frases están en vision/prompts_ia.json, en español
(SigLIP 2 es multilingüe).

Pasos para cada imagen:
1. Recorte: OpenCV (mascara_manzana) busca el producto sobre el fondo claro y se
   recorta con margen. Con el recorte la IA ve más detalle. Si no encuentra nada,
   se usa la imagen completa.
2. Color: se elige entre las frases de color y las de "nada" (mesa vacía, persona,
   mano). Si gana "nada", el color es "desconocido".
3. Sana o defectuosa:
   - Si existe data/modelo_defectos.npz (entrenado con fotos propias con
     python -m herramientas.entrenar_defectos), decide ese modelo.
   - Si no, se compara la frase de defecto que más calza (golpe, mancha, podrida...)
     con la frase de "sana" que más calza. Es defectuosa si la probabilidad del
     defecto supera el umbral.

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
from vision import defectos_entrenados
from vision.analisis import clasificar_imagen, mascara_manzana

ARCHIVO_PROMPTS = Path(__file__).with_name("prompts_ia.json")
MARGEN_RECORTE = 0.15   # se agrega 15 % alrededor del producto al recortar


def _como_lista(valor) -> list[str]:
    return [valor] if isinstance(valor, str) else list(valor)


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


class CodificadorHF:
    """Carga el modelo de Hugging Face y convierte imágenes y frases en vectores de norma 1."""

    def __init__(self, nombre: str):
        import torch
        from transformers import AutoModel, AutoProcessor

        self.torch = torch
        usar_gpu = torch.cuda.is_available()
        self.dispositivo_torch = "cuda" if usar_gpu else "cpu"
        self.dispositivo = "GPU" if usar_gpu else "CPU"
        self.dtype = torch.float16 if usar_gpu else torch.float32   # en la GPU: mitad de memoria y más rápido
        self.modelo = AutoModel.from_pretrained(nombre, dtype=self.dtype).to(self.dispositivo_torch).eval()
        self.procesador = AutoProcessor.from_pretrained(nombre)
        # SigLIP se entrenó con las frases rellenadas a 64 tokens; CLIP no lo necesita
        self.opciones_texto = ({"padding": "max_length", "max_length": 64} if "siglip" in nombre.lower()
                               else {"padding": True})
        # logit = escala * similitud + sesgo (el sesgo solo existe en SigLIP)
        self.escala = float(self.modelo.logit_scale.detach().exp())
        sesgo = getattr(self.modelo, "logit_bias", None)
        self.sesgo = float(sesgo.detach()) if sesgo is not None else 0.0

    def _normalizar(self, salida) -> np.ndarray:
        if not self.torch.is_tensor(salida):   # transformers 5 devuelve un objeto con pooler_output
            salida = salida.pooler_output
        salida = salida / salida.norm(dim=-1, keepdim=True)
        return salida.float().cpu().numpy()

    def textos(self, frases: list[str]) -> np.ndarray:
        entradas = self.procesador(text=frases, return_tensors="pt", **self.opciones_texto)
        with self.torch.no_grad():
            return self._normalizar(self.modelo.get_text_features(**entradas.to(self.dispositivo_torch)))

    def imagenes(self, imagenes_pil: list) -> np.ndarray:
        entradas = self.procesador(images=imagenes_pil, return_tensors="pt").to(self.dispositivo_torch)
        entradas = {k: (v.to(self.dtype) if v.is_floating_point() else v) for k, v in entradas.items()}
        with self.torch.no_grad():
            return self._normalizar(self.modelo.get_image_features(**entradas))


def recortar(imagen_bgr: np.ndarray, calib: dict):
    """Recorta el producto con margen. Devuelve (recorte, bbox) o (imagen completa, None)."""
    hsv = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2HSV)
    mascara = mascara_manzana(hsv, calib)
    if mascara is None:
        return imagen_bgr, None
    x, y, w, h = cv2.boundingRect(mascara)
    m = int(MARGEN_RECORTE * max(w, h))
    alto, ancho = imagen_bgr.shape[:2]
    x0, y0, x1, y1 = max(x - m, 0), max(y - m, 0), min(x + w + m, ancho), min(y + h + m, alto)
    return imagen_bgr[y0:y1, x0:x1], (int(x), int(y), int(w), int(h))


def a_pil(imagen_bgr: np.ndarray):
    from PIL import Image
    return Image.fromarray(cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB))


class ClasificadorIA:
    def __init__(self, calib: dict, modelo: str | None = None, codificador=None,
                 defectos: dict | None | bool = True):
        """codificador: permite probar sin descargar el modelo (tests).
        defectos: True = buscar data/modelo_defectos.npz; dict = usar ese; None/False = solo frases."""
        self.calib = calib
        self.producto = calib.get("producto", config.PRODUCTO)
        self.nombre_modelo = modelo or config.HF_MODELO
        prompts = json.loads(ARCHIVO_PROMPTS.read_text(encoding="utf-8"))
        if self.producto not in prompts:
            raise ValueError(f"No hay frases para el producto {self.producto!r} en {ARCHIVO_PROMPTS.name}")
        p = prompts[self.producto]
        self.umbral_defecto = float(p.get("umbral_defecto", 0.5))
        self.lock = threading.Lock()   # la usan la ventana y el hilo de MQTT

        self.cod = codificador or CodificadorHF(self.nombre_modelo)
        self.dispositivo = getattr(self.cod, "dispositivo", "prueba")

        # Frases de color + "nada": se convierten a vectores UNA vez (así cada foto tarda menos)
        self.dueño_color = []   # a qué color pertenece cada frase ("nada" = no hay producto)
        frases = []
        for color, f in p["color"].items():
            for frase in _como_lista(f):
                frases.append(frase)
                self.dueño_color.append(color)
        for frase in p["nada"]:
            frases.append(frase)
            self.dueño_color.append("nada")
        self.colores = [c for c in dict.fromkeys(self.dueño_color) if c != "nada"]
        self.dueño_color = np.array(self.dueño_color)
        self.vec_color = self.cod.textos(frases)

        # Frases de sana / defectuosa (cada defecto tiene nombre: golpe, mancha...)
        self.vec_sana = self.vec_defecto = None
        estado = p.get("estado")
        if estado:
            self.vec_sana = self.cod.textos(_como_lista(estado["sana"]))
            defectos_frases = estado["defectuosa"]
            if not isinstance(defectos_frases, dict):
                defectos_frases = {f"defecto {i + 1}": f for i, f in enumerate(_como_lista(defectos_frases))}
            self.tipos_defecto = list(defectos_frases)
            self.vec_defecto = self.cod.textos(list(defectos_frases.values()))

        # Modelo sana/defectuosa entrenado con fotos propias (si existe y es del mismo modelo)
        if defectos is True:
            defectos = defectos_entrenados.cargar(config.MODELO_DEFECTOS) if estado else None
        self.entrenado = None
        if defectos:
            if defectos.get("modelo") != self.nombre_modelo or defectos.get("producto") != self.producto:
                print(f"[AVISO] {config.MODELO_DEFECTOS.name} se entrenó con {defectos.get('modelo')} "
                      f"({defectos.get('producto')}); no calza con {self.nombre_modelo} ({self.producto}). "
                      "Se usan las frases. Volver a entrenar: python -m herramientas.entrenar_defectos")
            else:
                self.entrenado = defectos

        self.etiqueta = f"IA {self.nombre_modelo.split('/')[-1]} ({self.dispositivo})"
        if self.entrenado:
            self.etiqueta += " + defectos entrenados"

    def _logits(self, vector: np.ndarray, frases: np.ndarray) -> np.ndarray:
        return self.cod.escala * (frases @ vector) + self.cod.sesgo

    def defecto_por_frases(self, vector: np.ndarray) -> tuple[float, str]:
        """(probabilidad de defecto, defecto que más calzó) usando solo las frases."""
        l_sana = self._logits(vector, self.vec_sana).max()
        l_def = self._logits(vector, self.vec_defecto)
        i = int(l_def.argmax())
        prob = float(_softmax(np.array([l_sana, l_def[i]]))[1])
        return prob, self.tipos_defecto[i]

    def vector_de(self, imagen_bgr: np.ndarray):
        """(vector de la foto recortada, bbox)."""
        recorte, bbox = recortar(imagen_bgr, self.calib)
        return self.cod.imagenes([a_pil(recorte)])[0], bbox

    def clasificar(self, imagen_bgr: np.ndarray) -> dict:
        with self.lock:
            vector, bbox = self.vector_de(imagen_bgr)

        probs = _softmax(self._logits(vector, self.vec_color))
        p_nada = float(probs[self.dueño_color == "nada"].sum())
        por_color = {c: float(probs[self.dueño_color == c].sum()) for c in self.colores}
        color = max(por_color, key=por_color.get)

        resultado = {"modelo": self.nombre_modelo, "motor": self.etiqueta,
                     "probabilidades": {**por_color, "nada": p_nada},
                     "mascara": None, "manchas": None, "prob_defecto": None, "defecto": None}

        if p_nada > por_color[color]:
            # Lo más probable es que no haya producto a la vista
            resultado.update(color="desconocido", is_defective=False, confidence=0.0, bbox=None)
            return resultado

        is_defective = False
        if self.vec_defecto is not None:
            prob, tipo = self.defecto_por_frases(vector)   # el tipo sirve de pista aunque decida el entrenado
            if self.entrenado:
                prob = float(defectos_entrenados.probabilidad(vector[None], self.entrenado["w"],
                                                              self.entrenado["b"])[0])
                umbral = float(self.entrenado.get("umbral", 0.5))
            else:
                umbral = self.umbral_defecto
            is_defective = prob >= umbral
            resultado.update(prob_defecto=round(prob, 3), defecto=tipo if is_defective else None)

        # La confianza es la probabilidad del color entre los colores (sin contar "nada")
        total_colores = sum(por_color.values()) or 1.0
        resultado.update(color=color, is_defective=bool(is_defective),
                         confidence=round(por_color[color] / total_colores, 3), bbox=bbox)
        return resultado


ClasificadorCLIP = ClasificadorIA   # nombre anterior, por compatibilidad


def crear_motor(calib: dict, motor: str | None = None, cargar_ia=ClasificadorIA):
    """Devuelve (funcion_clasificar, etiqueta, nombre_modelo) según VISION_MOTOR.

    Con "ia" intenta cargar el modelo de Hugging Face; si no puede, avisa y usa
    OpenCV. Si la IA falla con una imagen puntual, esa imagen se clasifica con OpenCV.
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
