# SortiBandLLM — PC-IA

Esta carpeta es todo lo que corre en el **PC-IA**: la cámara y la IA que decide cada manzana. Necesita una GPU NVIDIA para la IA (SigLIP 2 de Google, en Hugging Face); sin GPU funciona con OpenCV.

Este PC **no toca la base de datos**: lee la configuración del PC-servidor por HTTP (`/api/settings`), le sube cada foto (`/api/imagenes`) y habla con el Arduino por MQTT a través del broker del servidor.

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `vision/clasificador.py` | Programa principal: cámara, MQTT y ventana en vivo |
| `vision/modelo_ia.py` | IA de Hugging Face (SigLIP 2): color y sana/dañada; si falla, usa OpenCV |
| `vision/defectos_entrenados.py` | Modelo sana/dañada entrenado con fotos propias (regresión logística sobre SigLIP 2) |
| `vision/analisis.py` | OpenCV: color HSV, manchas y recorte de la manzana |
| `vision/reglas.py` | Decide la salida: defectuosa → 1, grupo A → 2, resto → 3 |
| `vision/prompts_ia.json`, `vision/calibracion_manzana.json` | Frases de la IA (en español) y rangos de color |
| `vision/calibrar_hsv.py`, `vision/listar_camaras.py` | Calibrar la visión y encontrar la webcam |
| `herramientas/comparar_motores.py` | IA vs OpenCV en las fotos guardadas |
| `herramientas/capturar_fotos.py`, `herramientas/entrenar_defectos.py` | Sacar fotos de manzanas sanas y dañadas, y entrenar con ellas |
| `tests/` | Pruebas unitarias (`python -m pytest tests`) |
| `INICIAR_IA.bat` / `INICIAR_IA_SIN_CAMARA.bat` | Levantar la visión con doble clic (con cámara o simulada) |
| `scripts/iniciar_ia.ps1` | El script que usan los `.bat` |
| `comun/` | Configuración (`.env`) y tópicos MQTT |
| `data/imagenes/` | Copia de cada foto, sirve de dataset (no se sube a git) |
| `data/entrenamiento/` | Fotos para entrenar: `sana/` y `defectuosa/` (no se suben a git) |
| `data/modelo_defectos.npz` | Modelo sana/dañada entrenado (sí se sube: pesa ~3 KB) |

## Levantar: doble clic en `INICIAR_IA.bat`

Hace todo solo:

1. La primera vez crea el entorno de Python e instala las librerías (PyTorch pesa ~2,5 GB: 10–20 min).
2. Si no hay `.env`, lo crea y pregunta la **IP del PC-servidor** (la muestra `INICIAR_SERVIDOR.bat` en ese PC).
3. Comprueba que llega al broker y a la API del servidor. Si no llega (por ejemplo, cambió la red), pide la IP nueva.
4. Levanta la visión con la webcam. Tecla `q` en la ventana de la cámara = cerrar.

**`INICIAR_IA_SIN_CAMARA.bat`** hace lo mismo pero dibuja manzanas falsas: sirve para probar el sistema sin cámara. En ese modo decide OpenCV (los círculos dibujados no parecen manzanas para la IA).

La primera vez que se usa la IA descarga SigLIP 2 (~1,5 GB; tarda unos minutos) y la primera foto tarda ~1 s mientras se calienta la GPU; después, ~30 ms por manzana en una RTX 3050.

## Instalar a mano (si no se usa el .bat)

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

Debe decir `Motor listo: IA siglip2-base-patch16-224 (GPU)` (con `+ defectos entrenados` si existe `data/modelo_defectos.npz`) y `Configuración leída de http://...`.

## Cómo decide si la manzana está sana o dañada

1. **Sin entrenar (frases):** SigLIP 2 compara la foto recortada con frases en español de `vision/prompts_ia.json`: 2 de manzana sana y 6 de defectos (golpe, mancha, podrida, herida, gusano, arrugada). Gana el defecto que más calza contra la frase sana que más calza; si la probabilidad del defecto pasa `umbral_defecto` (0,5), va a la salida 1. La consola muestra cuál defecto vio.
2. **Entrenado con sus fotos (recomendado):** con manzanas reales del grupo, bajo la misma cámara y la misma luz:

```powershell
python -m herramientas.capturar_fotos      # s = sana, d = defectuosa, b = borrar la última, q = salir
python -m herramientas.entrenar_defectos   # mide aciertos, compara con las frases y guarda data/modelo_defectos.npz
```

   - Sacar 30 a 50 fotos de cada clase, con varias manzanas distintas y girándolas entre foto y foto.
   - La etiqueta es lo que **se ve**: si una manzana dañada muestra solo su lado sano, esa foto va como sana (la cámara de la banda solo ve la cara de arriba).
   - El entrenador muestra una tabla con los aciertos de las frases y del modelo entrenado, medidos con fotos que el modelo no vio. Sirve para el informe.
   - Al cambiar la luz o la cámara (por ejemplo, al armar el túnel), volver a sacar las fotos y entrenar.
   - `python -m herramientas.entrenar_defectos --borrar` vuelve a usar las frases.

> `comun/topicos.py` tiene una copia en `servidor/comun/`. Si se cambia un tópico o la lista de colores, cambiarlo en las dos (y en el firmware).
