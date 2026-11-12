"""Calibración de la visión con manzanas reales bajo la luz del túnel.

Abre la webcam y muestra en vivo: la imagen con el resultado, la máscara de la
manzana y las manchas detectadas. Con los deslizadores se ajustan los umbrales.

Teclas:  s = guardar en vision/calibracion.json   q = salir

Uso:  python -m vision.calibrar_hsv
Los rangos de tono por color (rangos_hue) se editan a mano en calibracion.json.
"""
import cv2

from comun import config
from vision.analisis import cargar_calibracion, clasificar_imagen, guardar_calibracion

VENTANA = "Calibracion (s = guardar, q = salir)"
DESLIZADORES = [  # (nombre, clave en la calibración, máximo)
    ("fondo S min", "fondo_s_min", 255),
    ("fondo V min", "fondo_v_min", 255),
    ("mancha % alrededor", "defecto_ratio", 100),   # 60 = más oscuro que el 60 % del vecindario
    ("mancha por mil", "defecto_fraccion", 200),  # 30 por mil = 0,03 (3 %)
]


def main():
    calib = cargar_calibracion()
    camara = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camara.isOpened():
        raise SystemExit(f"No se pudo abrir la webcam {config.CAMERA_INDEX}")

    cv2.namedWindow(VENTANA)
    for nombre, clave, maximo in DESLIZADORES:
        escala = {"defecto_fraccion": 1000, "defecto_ratio": 100}.get(clave, 1)
        valor = int(calib[clave] * escala)
        cv2.createTrackbar(nombre, VENTANA, valor, maximo, lambda _: None)

    while True:
        ok, imagen = camara.read()
        if not ok:
            break
        for nombre, clave, _ in DESLIZADORES:
            valor = cv2.getTrackbarPos(nombre, VENTANA)
            escala = {"defecto_fraccion": 1000, "defecto_ratio": 100}.get(clave, 1)
            calib[clave] = valor / escala if escala != 1 else valor

        r = clasificar_imagen(imagen, calib)
        texto = f"{r['color']}  conf={r['confidence']:.2f}  defectuosa={r['is_defective']}"
        cv2.putText(imagen, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
        cv2.putText(imagen, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1)
        cv2.imshow(VENTANA, imagen)
        if r["mascara"] is not None:
            cv2.imshow("Mascara de la manzana", r["mascara"])
            cv2.imshow("Manchas", r["manchas"])

        tecla = cv2.waitKey(30) & 0xFF
        if tecla == ord("s"):
            guardar_calibracion({k: v for k, v in calib.items()})
            print("Calibración guardada en vision/calibracion.json")
        elif tecla == ord("q"):
            break

    camara.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
