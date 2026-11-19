"""Saca fotos de manzanas sanas y dañadas para entrenar el modelo de defectos.

Abre la webcam y muestra en vivo lo que opina la IA (BUENA o MALA, y qué defecto).
La etiqueta la pone la persona con la tecla; las fotos donde la IA se equivoca
son las que más enseñan al entrenar. Guarda cada foto en data/entrenamiento/sana/ o
data/entrenamiento/defectuosa/ según la tecla:

    s = guardar como SANA       d = guardar como DEFECTUOSA
    b = borrar la última foto   q = salir

Consejos:
- Usar la MISMA cámara y la misma luz que en la banda (ideal: dentro del túnel).
- Sacar 30 a 50 fotos de cada clase. Girar la manzana entre foto y foto.
- La etiqueta es lo que se VE en la foto: si una manzana dañada muestra solo
  su lado sano, esa foto va como "sana" (la cámara de la banda solo ve la cara de arriba).
- Usar varias manzanas distintas, no 50 fotos de la misma.
- Si la IA no carga (sin GPU o sin el modelo), igual se pueden sacar las fotos.

Uso (desde ia/):  python -m herramientas.capturar_fotos
"""
import time

import cv2

from comun import config
from vision.analisis import cargar_calibracion
from vision.modelo_ia import ClasificadorIA, recortar

VENTANA = "Fotos de entrenamiento (s = sana, d = defectuosa, b = borrar, q = salir)"
CADA_CUADROS = 5   # la IA opina cada 5 cuadros (~6 veces por segundo)


def texto(vista, msg, pos, color, escala=0.8):
    """Texto con borde negro para que se lea sobre cualquier fondo."""
    cv2.putText(vista, msg, pos, cv2.FONT_HERSHEY_SIMPLEX, escala, (0, 0, 0), 4)
    cv2.putText(vista, msg, pos, cv2.FONT_HERSHEY_SIMPLEX, escala, color, 2)


def opinion_ia(r: dict) -> tuple[str, tuple]:
    """Frase y color (BGR) con lo que opina la IA (BUENA/MALA: la fuente de OpenCV no tiene ñ)."""
    if r["color"] == "desconocido":
        return "IA: no veo una manzana", (200, 200, 200)
    p = r.get("prob_defecto")
    if p is None:
        return f"IA: {r['color']}", (255, 255, 255)
    if r["is_defective"]:
        return f"IA: MALA ({r.get('defecto') or '?'}) {p:.2f}  - {r['color']}", (0, 0, 255)
    return f"IA: BUENA {1 - p:.2f}  - {r['color']}", (0, 200, 0)


def contar() -> dict[str, int]:
    return {c: len(list((config.ENTRENAMIENTO_DIR / c).glob("*.jpg"))) for c in ("sana", "defectuosa")}


def main():
    calib = cargar_calibracion()
    for clase in ("sana", "defectuosa"):
        (config.ENTRENAMIENTO_DIR / clase).mkdir(parents=True, exist_ok=True)

    camara = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camara.isOpened():
        raise SystemExit(f"No se pudo abrir la webcam {config.CAMERA_INDEX} (revisar CAMERA_INDEX en .env)")

    print(f"Cargando la IA ({config.HF_MODELO})...")
    try:
        ia = ClasificadorIA(calib)
        print(f"IA lista: {ia.etiqueta}")
    except Exception as error:  # noqa: BLE001 - sin IA igual se pueden sacar fotos
        ia = None
        print(f"[AVISO] No se pudo cargar la IA ({error}). Se sacan fotos sin su opinión.")

    ultima = None
    cuadro, opinion = 0, None
    aviso, hora_aviso = "", 0.0
    print(f"Guardando en {config.ENTRENAMIENTO_DIR}")
    while True:
        ok, imagen = camara.read()
        if not ok:
            break
        vista = imagen.copy()
        cuadro += 1
        if ia and cuadro % CADA_CUADROS == 0:
            try:
                opinion = opinion_ia(ia.clasificar(imagen))
            except Exception as error:  # noqa: BLE001
                opinion = (f"IA: error ({error})", (0, 0, 255))
        _, bbox = recortar(imagen, calib)
        if bbox:
            x, y, w, h = bbox
            cv2.rectangle(vista, (x, y), (x + w, y + h), (0, 200, 0), 2)
        else:
            texto(vista, "No veo la manzana (fondo claro?)", (10, 60), (0, 0, 255), 0.7)
        n = contar()
        texto(vista, f"sanas: {n['sana']}   defectuosas: {n['defectuosa']}", (10, 30), (255, 255, 255))
        if opinion:
            texto(vista, opinion[0], (10, 95), opinion[1])
        texto(vista, "s = sana   d = defectuosa   b = borrar   q = salir", (10, vista.shape[0] - 50),
              (255, 255, 255), 0.6)
        if time.time() - hora_aviso < 1.5:
            texto(vista, aviso, (10, vista.shape[0] - 15), (0, 200, 255))
        cv2.imshow(VENTANA, vista)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break
        if tecla in (ord("s"), ord("d")):
            clase = "sana" if tecla == ord("s") else "defectuosa"
            nombre = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}.jpg"
            ultima = config.ENTRENAMIENTO_DIR / clase / nombre
            cv2.imwrite(str(ultima), imagen)   # se guarda la foto completa, sin dibujos
            aviso, hora_aviso = f"Guardada como {clase.upper()}", time.time()
        elif tecla == ord("b") and ultima and ultima.exists():
            ultima.unlink()
            aviso, hora_aviso = f"Borrada {ultima.name}", time.time()
            ultima = None

    camara.release()
    cv2.destroyAllWindows()
    n = contar()
    print(f"Listo: {n['sana']} sanas y {n['defectuosa']} defectuosas en {config.ENTRENAMIENTO_DIR}")
    print("Siguiente paso: python -m herramientas.entrenar_defectos")


if __name__ == "__main__":
    main()
