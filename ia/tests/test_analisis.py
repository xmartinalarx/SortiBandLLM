"""Prueba el clasificador OpenCV con manzanas sintéticas (sin cámara)."""
import numpy as np
import pytest

from vision.analisis import CALIBRACION_POR_DEFECTO, clasificar_imagen, imagen_sintetica


@pytest.mark.parametrize("color", ["rojo", "verde", "amarillo"])
def test_detecta_color(color):
    for semilla in range(5):
        r = clasificar_imagen(imagen_sintetica(color, con_mancha=False, semilla=semilla), CALIBRACION_POR_DEFECTO)
        assert r["color"] == color
        assert r["is_defective"] is False
        assert r["confidence"] > 0.8


def test_detecta_mancha():
    for semilla in range(5):
        r = clasificar_imagen(imagen_sintetica("rojo", con_mancha=True, semilla=semilla), CALIBRACION_POR_DEFECTO)
        assert r["is_defective"] is True
        assert r["color"] == "rojo"


def test_sin_manzana():
    fondo = np.full((480, 640, 3), 235, np.uint8)
    r = clasificar_imagen(fondo, CALIBRACION_POR_DEFECTO)
    assert r["color"] == "desconocido"
    assert r["confidence"] == 0.0


@pytest.mark.parametrize("color", ["rojo", "naranjo", "amarillo", "verde", "azul"])
def test_lata_detecta_color_y_no_confunde_letras_con_defectos(color):
    from vision.analisis import PERFILES
    for semilla in range(3):
        img = imagen_sintetica(color, con_mancha=False, semilla=semilla, forma="lata")
        r = clasificar_imagen(img, PERFILES["lata"])
        assert r["color"] == color
        assert r["is_defective"] is False     # las letras oscuras no son defectos
        assert r["bbox"] is not None
