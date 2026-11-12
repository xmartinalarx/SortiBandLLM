"""Lista las cámaras conectadas al PC para saber qué índice usar en CAMERA_INDEX (.env).

La clasificación usa una webcam USB EXTERNA montada en el túnel. En un notebook la
cámara integrada suele ser la 0 y la externa la 1, pero el orden puede cambiar.

Uso:  python -m vision.listar_camaras            (lista las que responden)
      python -m vision.listar_camaras --ver 1    (muestra la imagen de la cámara 1; q = salir)
"""
import argparse

import cv2

from comun import config


def listar(maximo: int = 5) -> None:
    print(f"CAMERA_INDEX actual en .env: {config.CAMERA_INDEX}\n")
    encontradas = 0
    for indice in range(maximo):
        camara = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
        if camara.isOpened():
            ok, imagen = camara.read()
            if ok:
                alto, ancho = imagen.shape[:2]
                print(f"  Cámara {indice}: responde ({ancho} x {alto})")
                encontradas += 1
        camara.release()
    if not encontradas:
        print("  No se encontró ninguna cámara. ¿Está conectada la webcam?")
    else:
        print("\nPara saber cuál es la externa: python -m vision.listar_camaras --ver <índice>")


def ver(indice: int) -> None:
    camara = cv2.VideoCapture(indice, cv2.CAP_DSHOW)
    if not camara.isOpened():
        raise SystemExit(f"No se pudo abrir la cámara {indice}")
    print("Mostrando imagen. Tecla q para salir.")
    while True:
        ok, imagen = camara.read()
        if not ok:
            break
        cv2.imshow(f"Camara {indice} (q = salir)", imagen)
        if cv2.waitKey(30) & 0xFF == ord("q"):
            break
    camara.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Lista las cámaras disponibles")
    parser.add_argument("--ver", type=int, help="muestra la imagen de esa cámara")
    args = parser.parse_args()
    if args.ver is None:
        listar()
    else:
        ver(args.ver)


if __name__ == "__main__":
    main()
