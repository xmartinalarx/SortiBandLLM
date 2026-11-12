from vision.reglas import decidir_salida

SETTINGS = {"grupo_a_colores": "rojo, amarillo", "umbral_confianza": "0.6"}


def test_defectuosa_va_a_salida_1():
    assert decidir_salida("rojo", True, 0.9, SETTINGS) == 1
    assert decidir_salida("verde", True, 0.9, SETTINGS) == 1


def test_grupo_a_va_a_salida_2():
    assert decidir_salida("rojo", False, 0.9, SETTINGS) == 2
    assert decidir_salida("Amarillo", False, 0.9, SETTINGS) == 2


def test_resto_va_a_salida_3():
    assert decidir_salida("verde", False, 0.9, SETTINGS) == 3
    assert decidir_salida("desconocido", False, 0.9, SETTINGS) == 3


def test_baja_confianza_va_a_salida_3():
    assert decidir_salida("rojo", False, 0.5, SETTINGS) == 3
    assert decidir_salida("rojo", True, 0.5, SETTINGS) == 3


def test_grupo_a_vacio():
    assert decidir_salida("rojo", False, 0.9, {"grupo_a_colores": "", "umbral_confianza": "0.6"}) == 3
