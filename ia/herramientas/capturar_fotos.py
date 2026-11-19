"""Saca fotos de manzanas sanas y dañadas para entrenar el modelo de defectos.

Abre la webcam y guarda cada foto en data/entrenamiento/sana/ o
data/entrenamiento/defectuosa/ según la tecla:

    s = guardar como SANA       d = guardar como DEFECTUOSA
    b = borrar la última foto   q = salir

Consejos:
- Usar la MISMA cámara y la misma luz que en la banda (ideal: dentro del túnel).
- Sacar 30 a 50 fotos de cada clase. Girar la manzana entre foto y foto.
- La etiqueta es lo que se VE en la foto: si una manzana dañada muestra solo
  su lado sano, esa foto va como "sana" (la cámara de la banda solo ve la cara de arriba).
- Usar varias manzanas distintas, no 50 fotos de la misma.

Uso (desde ia/):  python -m herramientas.capturar_fotos
"""
import time

import cv2

from comun import config
from vision.analisis import cargar_calibracion
from vision.modelo_ia import recortar

VENTANA = "Fotos de entrenamiento (s = sana, d = defectuosa, b = borrar, q = salir)"


def contar() -> dict[str, int]:
    return {c: len(list((config.ENTRENAMIENTO_DIR / c).glob("*.jpg"))) for c in ("sana", "defectuosa")}


def main():
    calib = cargar_calibracion()
    for clase in ("sana", "defectuosa"):
        (config.ENTRENAMIENTO_DIR / clase).mkdir(parents=True, exist_ok=True)

    camara = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camara.isOpened():
        raise SystemExit(f"No se pudo abrir la webcam {config.CAMERA_INDEX} (revisar CAMERA_INDEX en .env)")

    ultima = None
    aviso, hora_aviso = "", 0.0
    print(f"Guardando en {config.ENTRENAMIENTO_DIR}")
    while True:
        ok, imagen = camara.read()
        if not ok:
            break
        vista = imagen.copy()
        _, bbox = recortar(imagen, calib)
        if bbox:
            x, y, w, h = bbox
            cv2.rectangle(vista, (x, y), (x + w, y + h), (0, 200, 0), 2)
        else:
            cv2.putText(vista, "No veo la manzana (fondo claro?)", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        n = contar()
        cv2.putText(vista, f"sanas: {n['sana']}   defectuosas: {n['defectuosa']}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 3)
        cv2.putText(vista, f"sanas: {n['sana']}   defectuosas: {n['defectuosa']}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
        if time.time() - hora_aviso < 1.5:
            cv2.putText(vista, aviso, (10, vista.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 120, 255), 2)
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
