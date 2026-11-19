"""Entrena el modelo sana/defectuosa con las fotos de data/entrenamiento/.

1. Recorta cada foto (igual que en la banda) y la pasa por SigLIP 2 para obtener su
   vector. Cada foto se usa también espejada (el doble de ejemplos).
2. Mide cuánto acierta con validación cruzada: entrena con una parte de las fotos
   y prueba con las que no vio. Lo compara con las frases sin entrenar.
3. Entrena con todas y guarda data/modelo_defectos.npz. La visión lo usa sola
   al reiniciarse (python -m vision.clasificador).

Uso (desde ia/):
    python -m herramientas.capturar_fotos      # primero, sacar las fotos
    python -m herramientas.entrenar_defectos
    python -m herramientas.entrenar_defectos --borrar   # volver a usar solo las frases
"""
import argparse
import time

import cv2
import numpy as np

from comun import config
from vision import defectos_entrenados as de
from vision.analisis import cargar_calibracion
from vision.modelo_ia import ClasificadorIA, a_pil, recortar

MINIMO_POR_CLASE = 8


def porcentaje(x: float) -> str:
    return f"{x * 100:5.1f} %"


def linea(nombre: str, m: dict) -> str:
    return (f"  {nombre:34} aciertos {porcentaje(m['aciertos'])} | detecta dañadas {porcentaje(m['detecta_dañadas'])}"
            f" | sanas bien {porcentaje(m['sanas_bien'])}  (falsas alarmas {m['fp']}, dañadas que pasan {m['fn']})")


def main():
    parser = argparse.ArgumentParser(description="Entrena sana/defectuosa con fotos propias")
    parser.add_argument("--borrar", action="store_true", help="borra el modelo entrenado (vuelven las frases)")
    args = parser.parse_args()

    if args.borrar:
        config.MODELO_DEFECTOS.unlink(missing_ok=True)
        print(f"Borrado {config.MODELO_DEFECTOS}. La visión vuelve a usar las frases de prompts_ia.json.")
        return

    fotos = {c: sorted((config.ENTRENAMIENTO_DIR / c).glob("*.jpg")) for c in ("sana", "defectuosa")}
    print(f"Fotos en {config.ENTRENAMIENTO_DIR}: {len(fotos['sana'])} sanas, {len(fotos['defectuosa'])} defectuosas")
    if min(len(f) for f in fotos.values()) < MINIMO_POR_CLASE:
        raise SystemExit(f"Hacen falta al menos {MINIMO_POR_CLASE} fotos de cada clase (ideal 30-50). "
                         "Sacarlas con: python -m herramientas.capturar_fotos")

    calib = cargar_calibracion()
    print(f"Cargando {config.HF_MODELO}...")
    ia = ClasificadorIA(calib, defectos=None)   # sin el modelo entrenado anterior

    X, y, grupos, sin_recorte = [], [], [], 0
    prob_frases, y_frases = [], []
    t0 = time.perf_counter()
    for clase, lista in fotos.items():
        for i, f in enumerate(lista):
            img = cv2.imread(str(f))
            if img is None:
                print(f"  [AVISO] no se pudo leer {f.name}")
                continue
            recorte, bbox = recortar(img, calib)
            sin_recorte += bbox is None
            vecs = ia.cod.imagenes([a_pil(recorte), a_pil(cv2.flip(recorte, 1))])   # original y espejada
            etiqueta = 1 if clase == "defectuosa" else 0
            X += list(vecs)
            y += [etiqueta, etiqueta]
            grupos += [f"{clase}/{i}"] * 2
            prob_frases.append(ia.defecto_por_frases(vecs[0])[0])
            y_frases.append(etiqueta)
    X, y, grupos = np.array(X), np.array(y), np.array(grupos)
    print(f"Vectores listos en {time.perf_counter() - t0:.1f} s"
          + (f" ({sin_recorte} fotos sin recorte: no se encontró la manzana)" if sin_recorte else ""))

    # Frases sin entrenar: con el umbral actual y con el mejor umbral posible
    prob_frases, y_frases = np.array(prob_frases), np.array(y_frases)
    m_frases = de.metricas(y_frases, prob_frases, ia.umbral_defecto)
    umbrales = np.round(np.arange(0.05, 0.96, 0.05), 2)
    # a igual acierto, se prefiere el umbral más cercano al actual
    mejor_u = max(umbrales, key=lambda u: (round(de.metricas(y_frases, prob_frases, u)["aciertos"], 6),
                                           -abs(u - ia.umbral_defecto)))
    m_frases_mejor = de.metricas(y_frases, prob_frases, mejor_u)

    m_cv = de.validacion_cruzada(X, y, grupos)

    print("\nResultados (con fotos que el modelo NO vio al entrenar):")
    print(linea(f"Frases, umbral {ia.umbral_defecto}", m_frases))
    print(linea(f"Frases, mejor umbral {mejor_u}", m_frases_mejor))
    print(linea("Entrenado con sus fotos", m_cv))

    w, b = de.entrenar(X, y)
    de.guardar(config.MODELO_DEFECTOS, w, b, modelo=ia.nombre_modelo, producto=ia.producto,
               info={"umbral": 0.5, "aciertos_cv": float(m_cv["aciertos"]),
                     "n_sanas": len(fotos["sana"]), "n_defectuosas": len(fotos["defectuosa"])})
    print(f"\nGuardado {config.MODELO_DEFECTOS}. Reiniciar la visión para usarlo.")
    if m_cv["aciertos"] < m_frases_mejor["aciertos"]:
        print(f"[AVISO] Las frases aciertan más que el entrenado. Mejor borrar el modelo (--borrar) y poner "
              f"\"umbral_defecto\": {mejor_u} en vision/prompts_ia.json, o sacar más fotos.")
    elif mejor_u != ia.umbral_defecto:
        print(f"(Si se borra el modelo entrenado, conviene poner \"umbral_defecto\": {mejor_u} en prompts_ia.json.)")


if __name__ == "__main__":
    main()
