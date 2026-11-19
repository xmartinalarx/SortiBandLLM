"""Clasificador sana/defectuosa entrenado con las fotos del grupo.

Idea (se llama "linear probe"): el modelo de Hugging Face (SigLIP 2) convierte cada
foto en un vector de 768 números que resume lo que se ve. Sobre esos vectores se
entrena una regresión logística: aprende qué combinación de esos números indica una
manzana dañada. Con 30-50 fotos por clase entrena en segundos, sin GPU.

No se reentrena el modelo grande: solo se aprenden 768 pesos + 1 sesgo.

Funciones:
- entrenar(X, y)          -> pesos (w, b)
- probabilidad(X, w, b)   -> probabilidad de defecto de cada foto
- validacion_cruzada(...) -> cuánto acierta con fotos que no vio al entrenar
- guardar(...) / cargar(...) el archivo data/modelo_defectos.npz
"""
from datetime import datetime
from pathlib import Path

import numpy as np


def _sigmoide(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def entrenar(X: np.ndarray, y: np.ndarray, regularizacion: float = 1e-3,
             iteraciones: int = 3000, paso: float = 0.5) -> tuple[np.ndarray, float]:
    """Regresión logística por descenso de gradiente.

    X: (n, d) vectores normalizados de las fotos. y: (n,) 1 = defectuosa, 0 = sana.
    Las clases se pesan para que valgan lo mismo aunque haya más fotos de una.
    """
    X = np.asarray(X, np.float64)
    y = np.asarray(y, np.float64)
    n, d = X.shape
    n_def = max(y.sum(), 1)
    n_sana = max(n - y.sum(), 1)
    peso = np.where(y == 1, n / (2 * n_def), n / (2 * n_sana))
    w = np.zeros(d)
    b = 0.0
    escala = 10.0   # los vectores tienen norma 1: se agrandan para que aprenda más rápido
    Xe = X * escala
    for _ in range(iteraciones):
        error = (_sigmoide(Xe @ w + b) - y) * peso
        w -= paso * (Xe.T @ error / n + regularizacion * w)
        b -= paso * error.mean()
    return (w * escala).astype(np.float32), float(b)


def probabilidad(X: np.ndarray, w: np.ndarray, b: float) -> np.ndarray:
    return _sigmoide(np.asarray(X, np.float64) @ np.asarray(w, np.float64) + b)


def validacion_cruzada(X: np.ndarray, y: np.ndarray, grupos: np.ndarray, pliegues: int = 5,
                       umbral: float = 0.5) -> dict:
    """Divide las fotos en `pliegues` partes; entrena con todas menos una y prueba con esa.

    `grupos` dice qué filas son de la misma foto (original y espejada): van siempre
    juntas, para no probar con una foto que el modelo ya vio.
    """
    unicos = np.unique(grupos)
    rng = np.random.default_rng(0)
    rng.shuffle(unicos)
    pliegues = max(2, min(pliegues, len(unicos)))
    prob = np.zeros(len(y))
    for k in range(pliegues):
        prueba = np.isin(grupos, unicos[k::pliegues])
        w, b = entrenar(X[~prueba], y[~prueba])
        prob[prueba] = probabilidad(X[prueba], w, b)
    return metricas(y, prob, umbral)


def metricas(y: np.ndarray, prob: np.ndarray, umbral: float = 0.5) -> dict:
    """Aciertos, y cuántas dañadas detecta (sensibilidad) y cuántas sanas deja pasar bien."""
    y = np.asarray(y).astype(bool)
    pred = np.asarray(prob) >= umbral
    vp, vn = int((pred & y).sum()), int((~pred & ~y).sum())
    fp, fn = int((pred & ~y).sum()), int((~pred & y).sum())
    return {
        "aciertos": (vp + vn) / max(len(y), 1),
        "detecta_dañadas": vp / max(vp + fn, 1),
        "sanas_bien": vn / max(vn + fp, 1),
        "vp": vp, "vn": vn, "fp": fp, "fn": fn,
    }


def guardar(ruta: Path, w: np.ndarray, b: float, modelo: str, producto: str, info: dict):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    np.savez(ruta, w=w, b=np.float32(b), modelo=modelo, producto=producto,
             fecha=datetime.now().isoformat(timespec="seconds"),
             **{k: np.float32(v) if isinstance(v, float) else v for k, v in info.items()})


def cargar(ruta: Path) -> dict | None:
    """Devuelve {"w", "b", "modelo", "producto", ...} o None si no existe el archivo."""
    if not ruta.exists():
        return None
    datos = np.load(ruta, allow_pickle=False)
    return {k: (datos[k].item() if datos[k].ndim == 0 else datos[k]) for k in datos.files}
