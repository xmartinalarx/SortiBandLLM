"""Compara la IA (CLIP) con OpenCV sobre las fotos guardadas en data/imagenes.

Muestra, foto por foto, qué decidió cada motor y cuánto tardó. Sirve para revisar
la IA y como tabla para el informe.

Uso (desde proyecto-final/, en el PC con la IA):
    python -m herramientas.comparar_motores                 # las 20 fotos más recientes
    python -m herramientas.comparar_motores --todas
    python -m herramientas.comparar_motores --foto data/imagenes/20261105_110157_1.jpg
"""
import argparse
import time
from pathlib import Path

import cv2

from comun import config
from vision.analisis import cargar_calibracion
from vision.modelo_ia import crear_motor


def resumen(r: dict) -> str:
    if r["color"] == "desconocido":
        return "desconocido"
    estado = "DEFECT" if r["is_defective"] else "sana"
    return f"{r['color']} {r['confidence']:.2f} {estado}"


def main():
    parser = argparse.ArgumentParser(description="Compara IA y OpenCV en fotos guardadas")
    parser.add_argument("--todas", action="store_true")
    parser.add_argument("--foto", help="analizar una sola foto")
    args = parser.parse_args()

    calib = cargar_calibracion()
    opencv, _, _ = crear_motor(calib, motor="opencv")
    ia, etiqueta_ia, modelo_ia = crear_motor(calib, motor="ia")
    if modelo_ia == "opencv":
        raise SystemExit("La IA no está disponible (revisa requirements-ia.txt). Nada que comparar.")

    if args.foto:
        fotos = [Path(args.foto)]
    else:
        fotos = sorted(config.IMAGES_DIR.glob("*.jpg"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not args.todas:
            fotos = fotos[:20]
    if not fotos:
        raise SystemExit(f"No hay fotos en {config.IMAGES_DIR}")

    ia(cv2.imread(str(fotos[0])))   # la primera pasada carga la GPU: no se cuenta en el tiempo

    print(f"Producto: {config.PRODUCTO} | IA: {etiqueta_ia}\n")
    print(f"{'foto':34} {'OpenCV':26} {'IA':26} {'ms IA':>6}")
    tiempos = []
    for f in fotos:
        img = cv2.imread(str(f))
        if img is None:
            continue
        r_cv = opencv(img)
        t0 = time.perf_counter()
        r_ia = ia(img)
        ms = (time.perf_counter() - t0) * 1000
        tiempos.append(ms)
        print(f"{f.name:34} {resumen(r_cv):26} {resumen(r_ia):26} {ms:6.0f}")
    print(f"\n{len(tiempos)} fotos. IA: {sum(tiempos) / len(tiempos):.0f} ms promedio, {max(tiempos):.0f} ms máximo.")


if __name__ == "__main__":
    main()
