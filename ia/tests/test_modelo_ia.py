"""Prueba el motor de IA con un codificador FALSO: no descarga ningún modelo ni necesita GPU.

El codificador falso le da a la foto el vector e0. Las frases que contienen alguna de
las palabras de `calzan` también reciben e0 (similitud 1); el resto recibe e1 (similitud 0).
"""
import numpy as np
import pytest

pytest.importorskip("PIL")   # el clasificador convierte la imagen a PIL

from vision import defectos_entrenados as de
from vision.analisis import PERFILES, imagen_sintetica
from vision.modelo_ia import ClasificadorIA, crear_motor

E0, E1 = np.eye(4, dtype=np.float32)[0], np.eye(4, dtype=np.float32)[1]


class CodificadorFalso:
    escala, sesgo, dispositivo = 10.0, 0.0, "prueba"

    def __init__(self, *calzan):
        self.calzan = calzan

    def textos(self, frases):
        return np.array([E0 if any(p in f for p in self.calzan) else E1 for f in frases])

    def imagenes(self, imagenes):
        return np.array([E0 for _ in imagenes])


def calib_manzana():
    c = dict(PERFILES["manzana"])
    c["producto"] = "manzana"
    return c


def ia_con(*calzan, defectos=None):
    return ClasificadorIA(calib_manzana(), modelo="prueba/modelo",
                          codificador=CodificadorFalso(*calzan), defectos=defectos)


def test_color_y_sana():
    r = ia_con("manzana roja", "sana").clasificar(imagen_sintetica("rojo", con_mancha=False, semilla=1))
    assert r["color"] == "rojo"
    assert r["is_defective"] is False
    assert r["confidence"] > 0.9
    assert r["prob_defecto"] < 0.01
    assert r["defecto"] is None
    assert r["bbox"] is not None          # OpenCV encontró dónde está para recortar


def test_defectuosa_dice_que_defecto():
    r = ia_con("manzana verde", "golpe").clasificar(imagen_sintetica("verde", con_mancha=False, semilla=2))
    assert r["color"] == "verde"
    assert r["is_defective"] is True
    assert r["prob_defecto"] > 0.99
    assert r["defecto"] == "golpe"


def test_sin_producto_es_desconocido():
    r = ia_con("persona").clasificar(imagen_sintetica("rojo", con_mancha=False, semilla=3))
    assert r["color"] == "desconocido"
    assert r["confidence"] == 0.0
    assert r["bbox"] is None


def test_modelo_entrenado_manda_sobre_las_frases():
    # Las frases dicen "golpe", pero el modelo entrenado dice sana (peso negativo en e0)
    entrenado = {"w": -5 * E0, "b": 0.0, "modelo": "prueba/modelo", "producto": "manzana", "umbral": 0.5}
    ia = ia_con("manzana roja", "golpe", defectos=entrenado)
    r = ia.clasificar(imagen_sintetica("rojo", con_mancha=False, semilla=4))
    assert r["is_defective"] is False
    assert "entrenados" in ia.etiqueta


def test_modelo_entrenado_de_otro_modelo_se_ignora():
    entrenado = {"w": -5 * E0, "b": 0.0, "modelo": "otro/modelo", "producto": "manzana"}
    ia = ia_con("manzana roja", "golpe", defectos=entrenado)
    assert ia.entrenado is None
    assert ia.clasificar(imagen_sintetica("rojo", con_mancha=False, semilla=5))["is_defective"] is True


def test_entrenar_separa_dos_grupos():
    rng = np.random.default_rng(0)
    sanas = rng.normal(0, 1, (40, 16)) + np.r_[3, np.zeros(15)]
    dañadas = rng.normal(0, 1, (40, 16)) - np.r_[3, np.zeros(15)]
    X = np.vstack([sanas, dañadas])
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    y = np.r_[np.zeros(40), np.ones(40)]
    m = de.validacion_cruzada(X, y, grupos=np.arange(80))
    assert m["aciertos"] > 0.9


def test_guardar_y_cargar(tmp_path):
    ruta = tmp_path / "m.npz"
    de.guardar(ruta, np.ones(4, np.float32), 0.25, modelo="a/b", producto="manzana", info={"umbral": 0.5})
    m = de.cargar(ruta)
    assert m["modelo"] == "a/b" and m["producto"] == "manzana"
    assert m["b"] == pytest.approx(0.25) and m["umbral"] == pytest.approx(0.5)
    assert de.cargar(tmp_path / "no_existe.npz") is None


def test_si_la_ia_no_carga_se_usa_opencv():
    def no_carga(calib):
        raise ImportError("torch no instalado")
    clasificar, etiqueta, modelo = crear_motor(calib_manzana(), motor="ia", cargar_ia=no_carga)
    assert modelo == "opencv"
    r = clasificar(imagen_sintetica("verde", con_mancha=False, semilla=4))
    assert r["color"] == "verde"


def test_si_la_ia_falla_en_una_imagen_se_usa_opencv():
    class IARota:
        etiqueta, nombre_modelo = "IA rota", "rota"
        def __init__(self, calib):
            pass
        def clasificar(self, imagen):
            raise RuntimeError("CUDA out of memory")
    clasificar, _, _ = crear_motor(calib_manzana(), motor="ia", cargar_ia=IARota)
    r = clasificar(imagen_sintetica("rojo", con_mancha=False, semilla=5))
    assert r["color"] == "rojo"
    assert r["modelo"] == "opencv"
