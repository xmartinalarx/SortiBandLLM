"""Regla que decide a qué salida va cada manzana.

Salida 1 (paleta 1, derecha):   defectuosas
Salida 2 (paleta 2, izquierda): colores del grupo A (configurable en settings)
Salida 3 (final de la banda):   el resto

Es una función pura (no usa cámara, MQTT ni BD) para poder probarla con pytest.
"""

# Todos los colores que puede entregar algún perfil (manzana o lata). Ver vision/analisis.py
COLORES = ("rojo", "naranjo", "amarillo", "verde", "azul")


def colores_grupo_a(settings: dict) -> set[str]:
    texto = settings.get("grupo_a_colores", "")
    return {c.strip().lower() for c in texto.split(",") if c.strip()}


def decidir_salida(color: str, is_defective: bool, confidence: float, settings: dict) -> int:
    umbral = float(settings.get("umbral_confianza", 0.6))

    # Si la visión no está segura, no se desvía: va al final para revisión manual.
    if confidence < umbral:
        return 3
    if is_defective:
        return 1
    if color.lower() in colores_grupo_a(settings):
        return 2
    return 3
