# SortiBandLLM — PC-servidor

Esta carpeta es todo lo que corre en el **PC-servidor**: el broker MQTT (Mosquitto), la base de datos (MySQL), la API con el puente MQTT → MySQL y el dashboard web. No necesita GPU.

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `server/api/` | API FastAPI + puente MQTT → MySQL (`python -m server.api.main`) |
| `server/db/schema.sql` | Esquema de la base `clasifiot` |
| `server/mosquitto/mosquitto.conf` | Configuración del broker (acepta conexiones de la red) |
| `server/supervisor/` | Supervisor con Ollama (fuera del MVP) |
| `web/` | Dashboard (lo sirve la API en el puerto 8000) |
| `comun/` | Configuración (`.env`), tópicos MQTT y conexión a MySQL |
| `simulador/` | Arduino falso, para probar sin hardware |
| `herramientas/verificar_flujo.py` | Prueba de punta a punta (MQTT + BD) |
| `INICIAR_SERVIDOR.bat` / `DETENER_SERVIDOR.bat` | Levantar o apagar todo con doble clic |
| `scripts/` | `instalar_servidor.ps1` (instalación) y los scripts que usan los `.bat` |
| `data/imagenes/` | Fotos que sube el PC-IA (no se suben a git) |

## Instalar (una vez)

Copiar esta carpeta `servidor/` al PC-servidor y, en PowerShell dentro de ella:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_servidor.ps1
```

Instala Mosquitto y XAMPP si faltan, abre los puertos 1883 y 8000 en el firewall, crea la base de datos, el entorno de Python y el `.env`. Al final muestra **la IP de este PC**, que va en el `.env` del PC-IA y en el `secrets.h` del Arduino.

## Levantar: doble clic en `INICIAR_SERVIDOR.bat`

Hace todo solo: instala si es la primera vez, levanta Mosquitto y MySQL si no están corriendo, inicia la API en su propia ventana, abre el dashboard en el navegador y muestra la IP que va en el PC-IA y en el Arduino.

Para apagar: doble clic en **`DETENER_SERVIDOR.bat`** (apaga MySQL de forma ordenada). No cerrar MySQL a la fuerza: daña sus tablas internas.

A mano, con Mosquitto y MySQL encendidos:

```powershell
.venv\Scripts\activate
python -m server.api.main          # dashboard en http://<IP>:8000
```

## Probar sin hardware

```powershell
python -m simulador.sim_control                      # reemplaza al Arduino
python -m herramientas.verificar_flujo --manzanas 10  # revisa MQTT y la BD
```

Para la visión simulada, en el PC-IA: `python -m vision.clasificador --simular`.

> `comun/topicos.py` tiene una copia en `ia/comun/`. Si se cambia un tópico o la lista de colores, cambiarlo en las dos (y en el firmware).
