"""Dibuja sobre la imagen lo que ve el clasificador: rectángulo, color, confianza y manchas.

Se usa en la ventana en vivo de la visión (python -m vision.clasificador).
"""
import cv2
import numpy as np

# Color del rectángulo según lo detectado (OpenCV usa BGR)
COLOR_BGR = {
    "rojo": (40, 40, 230),
    "verde": (60, 190, 60),
    "naranjo": (0, 140, 255),
    "amarillo": (0, 210, 240),
    "azul": (220, 110, 30),
    "desconocido": (160, 160, 160),
}


def _texto(img, texto, x, y, escala=0.6, color=(255, 255, 255), fondo=(0, 0, 0)):
    """Texto con un recuadro de fondo para que se lea sobre cualquier imagen."""
    (ancho, alto), base = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, 2)
    cv2.rectangle(img, (x, y - alto - 6), (x + ancho + 8, y + base), fondo, thickness=-1)
    cv2.putText(img, texto, (x + 4, y - 2), cv2.FONT_HERSHEY_SIMPLEX, escala, color, 2, cv2.LINE_AA)


def _barras_probabilidades(vista: np.ndarray, r: dict) -> None:
    """Panel arriba a la derecha con lo que "piensa" la IA: probabilidad de cada opción."""
    probs = r.get("probabilidades")
    if not probs:
        return
    filas = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:4]
    if r.get("prob_defecto") is not None:
        filas.append(("dañada", r["prob_defecto"]))
    ancho_panel, x0, y0 = 200, vista.shape[1] - 210, 8
    cv2.rectangle(vista, (x0, y0), (x0 + ancho_panel, y0 + 24 * len(filas) + 8), (25, 25, 25), -1)
    for k, (nombre, p) in enumerate(filas):
        y = y0 + 22 + 24 * k
        largo = int(110 * float(p))
        color = COLOR_BGR.get(nombre, (200, 200, 200) if nombre != "dañada" else (255, 0, 255))
        cv2.rectangle(vista, (x0 + 80, y - 12), (x0 + 80 + largo, y + 2), color, -1)
        cv2.putText(vista, nombre.replace("ñ", "n"), (x0 + 6, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (240, 240, 240), 1, cv2.LINE_AA)
        cv2.putText(vista, f"{p:.2f}", (x0 + 80 + max(largo, 0) + 4, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (240, 240, 240), 1, cv2.LINE_AA)


def dibujar_deteccion(imagen: np.ndarray, r: dict) -> np.ndarray:
    """Copia de la imagen con el rectángulo del producto, su color, las manchas (OpenCV)
    o las probabilidades (IA), y el nombre del motor que decidió."""
    vista = imagen.copy()
    alto = vista.shape[0]
    if r.get("motor"):
        _texto(vista, r["motor"], 10, alto - 50, escala=0.5, fondo=(60, 60, 60))
    _barras_probabilidades(vista, r)

    if r.get("color", "desconocido") == "desconocido":
        _texto(vista, "Sin manzana a la vista", 10, 30)
        return vista

    # Manchas (defectos) pintadas de magenta: se distingue sobre manzanas de cualquier color
    if r.get("manchas") is not None:
        vista[r["manchas"] > 0] = (255, 0, 255)

    color = COLOR_BGR.get(r["color"], COLOR_BGR["desconocido"])
    estado = "DEFECTUOSA" if r["is_defective"] else "sana"
    texto = f"{r['color']}  {r['confidence']:.2f}  {estado}"
    color_letra = (0, 0, 0) if r["color"] == "amarillo" else (255, 255, 255)
    if r.get("bbox") is not None:
        x, y, w, h = r["bbox"]
        cv2.rectangle(vista, (x, y), (x + w, y + h), color, 3)
        _texto(vista, texto, x, max(y - 8, 24), fondo=color, color=color_letra)
    else:
        # La IA vio el producto, pero OpenCV no pudo marcar dónde: texto arriba
        _texto(vista, texto, 10, 30, fondo=color, color=color_letra)
    return vista


def dibujar_aviso_foto(vista: np.ndarray, piece_id, r: dict, salida: int) -> None:
    """Franja inferior que avisa la última foto tomada por pedido del Arduino."""
    alto = vista.shape[0]
    cv2.rectangle(vista, (0, alto - 42), (vista.shape[1], alto), (20, 20, 20), thickness=-1)
    cv2.putText(vista, f"FOTO manzana {piece_id}: {r['color']} -> salida {salida}",
                (10, alto - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
