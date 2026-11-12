"""Prueba la traducción de las respuestas de CLIP al contrato del clasificador,
con un pipeline FALSO: no descarga ningún modelo ni necesita GPU."""
import pytest

pytest.importorskip("PIL")   # el clasificador convierte la imagen a PIL

from vision.analisis import PERFILES, imagen_sintetica
from vision.modelo_ia import ClasificadorCLIP, crear_motor


def calib_manzana():
    c = dict(PERFILES["manzana"])
    c["producto"] = "manzana"
    return c


def pipeline_falso(gana: str, prob_defecto: float = 0.1):
    """Simula el pipeline de transformers: la frase que contiene `gana` se lleva 0,8."""
    def pipe(imagen, candidate_labels):
        if any("healthy" in f for f in candidate_labels):   # consulta de estado (sana/dañada)
            return [{"label": f, "score": prob_defecto if "rotten" in f else 1 - prob_defecto}
                    for f in candidate_labels]
        resto = 0.2 / (len(candidate_labels) - 1)
        return [{"label": f, "score": 0.8 if gana in f else resto} for f in candidate_labels]
    return pipe


def test_color_y_sana():
    ia = ClasificadorCLIP(calib_manzana(), pipeline_fn=pipeline_falso("red apple"))
    r = ia.clasificar(imagen_sintetica("rojo", con_mancha=False, semilla=1))
    assert r["color"] == "rojo"
    assert r["is_defective"] is False
    assert r["confidence"] > 0.8          # 0,8 entre los colores (sin contar "nada")
    assert r["bbox"] is not None          # OpenCV encontró dónde está para recortar


def test_defectuosa_sobre_el_umbral():
    ia = ClasificadorCLIP(calib_manzana(), pipeline_fn=pipeline_falso("green apple", prob_defecto=0.85))
    r = ia.clasificar(imagen_sintetica("verde", con_mancha=False, semilla=2))
    assert r["color"] == "verde"
    assert r["is_defective"] is True
    assert r["prob_defecto"] == pytest.approx(0.85)


def test_sin_producto_es_desconocido():
    ia = ClasificadorCLIP(calib_manzana(), pipeline_fn=pipeline_falso("a person"))
    r = ia.clasificar(imagen_sintetica("rojo", con_mancha=False, semilla=3))
    assert r["color"] == "desconocido"
    assert r["confidence"] == 0.0
    assert r["bbox"] is None


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
