# SortiBandLLM — clasificadora IoT de manzanas

Proyecto semestral del ramo Internet de las Cosas, del grupo **pythonGroup**: Martín Alarcón,
Martín Araya, Vicente Pereira y Reinaldo Castillo.

Banda transportadora impresa en 3D que clasifica manzanas por color y defectos (IA de Hugging Face,
CLIP, con OpenCV de respaldo), las desvía con dos paletas (Arduino UNO R4 WiFi + servos) y registra
cada una en MySQL. Un dashboard web muestra los datos y controla la banda. El contexto completo está
en [CLAUDE.md](CLAUDE.md).

> La base de datos y su usuario se siguen llamando `clasifiot` (nombre anterior del proyecto).

```
Arduino R4 (banda) --MQTT--> Mosquitto <--MQTT-- PC-IA: webcam + CLIP / OpenCV
                                |                    |
                        API FastAPI <------HTTP------+  (configuración y fotos)
                         |        |
                       MySQL   Dashboard web
                   \______ PC-servidor ______/
```

## Dos carpetas, una por equipo

| Carpeta | Se copia al | Contiene | Guía |
|---|---|---|---|
| [`servidor/`](servidor/) | PC-servidor | Broker, BD, API, dashboard, simulador | [servidor/LEEME.md](servidor/LEEME.md) |
| [`ia/`](ia/) | PC-IA (con GPU) | Cámara, IA, OpenCV, pruebas | [ia/LEEME.md](ia/LEEME.md) |
| `firmware/` | Arduino | Control de la banda | [docs/conexion-paso-a-paso.md](docs/conexion-paso-a-paso.md) |
| `hardware/3d/` | Impresora 3D | Piezas, STL y G-code | [hardware/3d/manzanas/LEEME.md](hardware/3d/manzanas/LEEME.md) |
| `docs/` | — | Guías de conexión e informes | — |

Cada carpeta tiene su propio `.env`, `requirements.txt` y entorno de Python, y se levanta sola.
**Con doble clic:** en el PC-servidor `servidor/INICIAR_SERVIDOR.bat` (se apaga con `DETENER_SERVIDOR.bat`); en el PC-IA `ia/INICIAR_IA.bat` (o `INICIAR_IA_SIN_CAMARA.bat` para probar sin cámara). Primero el servidor, después la IA.
Todo se puede correr también en un solo PC, cada parte en su terminal (`MQTT_HOST=localhost` y
`SERVER_URL=http://localhost:8000` en `ia/.env`).

## Correr todo SIN hardware (simulación)

| Terminal | Carpeta | Comando | Qué es |
|---|---|---|---|
| 1 | `servidor/` | `mosquitto -c server/mosquitto/mosquitto.conf -v` | Broker MQTT (o el servicio de Windows) |
| 2 | `servidor/` | `python -m server.api.main` | API + dashboard en http://localhost:8000 |
| 3 | `ia/` | `python -m vision.clasificador --simular` | Visión con manzanas dibujadas |
| 4 | `servidor/` | `python -m simulador.sim_control` | Banda simulada (reemplaza al Arduino) |
| 5 | cualquiera | `mosquitto_sub -h localhost -t "sorter/#" -v` | Ver todos los mensajes |

Abrir el dashboard y apretar **Iniciar**.

## ¿Llegan los datos? Cómo comprobarlo

**A mano:** en la terminal 5, por cada manzana deben aparecer en orden, con el mismo `piece_id`:
```
sorter/sensor/arrival    {"piece_id": 7, ...}
sorter/vision/result     {"piece_id": 7, "color": "rojo", "output_channel": 2, ...}
sorter/control/diverted  {"piece_id": 7, "output_channel": 2, ...}
```

**Automático** (desde `servidor/`): revisa los mensajes Y la base de datos, y dice OK o qué falló:
```bash
python -m herramientas.verificar_flujo --manzanas 10 --velocidad 40
python -m herramientas.verificar_flujo --manzanas 10 --sin-bd      # solo MQTT
```

**En la BD:**
```sql
SELECT piece_id, color, is_defective, confidence, output_channel, diverted_ts
FROM clasifiot.pieces ORDER BY id DESC LIMIT 10;
```

**Pruebas de fallas:**

| Prueba | Qué debe pasar |
|---|---|
| Cerrar el simulador (o desenchufar el Arduino) | El dashboard muestra *banda: sin conexión* (Last Will) |
| Cerrar Mosquitto | La banda se detiene |
| Cerrar la visión | Las manzanas van a la salida 3 y igual quedan registradas |
| Apagar MySQL | La clasificación sigue; el dashboard muestra *BD: sin conexión* |
| Apagar la API | La visión sigue con la última configuración; las fotos no llegan al dashboard |
| Botón de emergencia del dashboard | Aparece `sorter/emergency` y la banda se detiene |

**Pruebas unitarias** (desde `ia/`): `python -m pytest tests`

## Pasar al hardware real

Guía completa de cableado y encendido, con una prueba por paso: [docs/conexion-paso-a-paso.md](docs/conexion-paso-a-paso.md).

1. **Arduino UNO R4 WiFi**: copiar `firmware/control_uno_r4/secrets.h.example` como `secrets.h` y
   completarlo con la IP del PC-servidor. Instalar el paquete de placas "Arduino UNO R4 Boards" y las
   librerías PubSubClient, ArduinoJson y Servo. Para probarlo sin la banda, activar `MODO_BANCO` en
   `config.h`: cada `m` en el Monitor Serie simula una manzana.
2. **Webcam externa** (en el PC-IA): ver su índice con `python -m vision.listar_camaras` y ponerlo en
   `CAMERA_INDEX` de `ia/.env`. Calibrar con manzanas reales y la luz del túnel
   (`python -m vision.calibrar_hsv`, tecla `s` para guardar).
3. **Pines** (`config.h`): revisarlos antes de cablear.

> Si el Arduino no llega al PC en la red del laboratorio (puede haber aislamiento entre
> clientes), probar con el hotspot de un celular.
