# SortiBandLLM — PC-IA

Esta carpeta es todo lo que corre en el **PC-IA**: la cámara y la IA que decide cada manzana. Necesita una GPU NVIDIA para la IA (CLIP); sin GPU funciona con OpenCV.

Este PC **no toca la base de datos**: lee la configuración del PC-servidor por HTTP (`/api/settings`), le sube cada foto (`/api/imagenes`) y habla con el Arduino por MQTT a través del broker del servidor.

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `vision/clasificador.py` | Programa principal: cámara, MQTT y ventana en vivo |
| `vision/modelo_ia.py` | IA de Hugging Face (CLIP); si falla, usa OpenCV |
| `vision/analisis.py` | OpenCV: color HSV, manchas y recorte de la manzana |
| `vision/reglas.py` | Decide la salida: defectuosa → 1, grupo A → 2, resto → 3 |
| `vision/prompts_ia.json`, `vision/calibracion_manzana.json` | Frases de la IA y rangos de color |
| `vision/calibrar_hsv.py`, `vision/listar_camaras.py` | Calibrar la visión y encontrar la webcam |
| `herramientas/comparar_motores.py` | IA vs OpenCV en las fotos guardadas |
| `tests/` | Pruebas unitarias (`python -m pytest tests`) |
| `comun/` | Configuración (`.env`) y tópicos MQTT |
| `data/imagenes/` | Copia de cada foto, sirve de dataset (no se sube a git) |

## Instalar (una vez)

Copiar esta carpeta `ia/` al PC-IA y, en PowerShell dentro de ella:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
$env:PYTHONUTF8 = "1"; pip install -r requirements.txt -r requirements-ia.txt
copy .env.example .env
```

En el `.env`, poner la **IP del PC-servidor** (la muestra su instalador, o `ipconfig` en ese PC):

```
MQTT_HOST=<IP del PC-servidor>
SERVER_URL=http://<IP del PC-servidor>:8000
```

Si la webcam no es la 0: `python -m vision.listar_camaras` y cambiar `CAMERA_INDEX`.

## Levantar

```powershell
.venv\Scripts\activate
python -m vision.clasificador             # webcam + ventana en vivo (q = salir)
python -m vision.clasificador --simular   # sin cámara: manzanas dibujadas
```

Debe decir `Motor listo: IA clip-vit-base-patch32 (GPU)` y `Configuración leída de http://...`.

> `comun/topicos.py` tiene una copia en `servidor/comun/`. Si se cambia un tópico o la lista de colores, cambiarlo en las dos (y en el firmware).
