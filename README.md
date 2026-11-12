# ClasifIoT — clasificadora IoT de manzanas

Banda transportadora impresa en 3D que clasifica manzanas por color y defectos (OpenCV en el PC),
las desvía con dos paletas (Arduino UNO R4 WiFi + servos) y registra cada una en MySQL. Un dashboard web
muestra los datos y controla la banda. El contexto completo está en [CLAUDE.md](CLAUDE.md).

```
Arduino R4 (banda) --MQTT--> Mosquitto <--MQTT-- Visión (webcam + OpenCV)
                            |
                     Servidor FastAPI --> MySQL
                            |
                       Dashboard web
```

## 1. Instalación (una vez)

1. **Python 3.12** y el entorno virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Mosquitto**: instalar desde https://mosquitto.org/download/ y abrir el puerto 1883 en el
   firewall de Windows (para que entre el Arduino).
3. **MySQL 8**: crear la base con el esquema y un usuario para la aplicación:
   ```bash
   mysql -u root -p < server/db/schema.sql
   mysql -u root -p -e "CREATE USER 'clasifiot'@'localhost' IDENTIFIED BY 'una_clave'; GRANT ALL ON clasifiot.* TO 'clasifiot'@'localhost';"
   ```
4. Copiar `.env.example` como `.env` y completar la clave de la BD.

## 2. Correr todo SIN hardware (simulación)

Una terminal por proceso, todas desde la carpeta `proyecto-final/` y con el entorno activado:

| Terminal | Comando | Qué es |
|---|---|---|
| 1 | `mosquitto -c server/mosquitto/mosquitto.conf -v` | Broker MQTT |
| 2 | `python -m server.api.main` | API + dashboard en http://localhost:8000 |
| 3 | `python -m vision.clasificador --simular` | Visión con manzanas dibujadas |
| 4 | `python -m simulador.sim_control` | Banda simulada (reemplaza al Arduino) |
| 5 | `mosquitto_sub -h localhost -t "sorter/#" -v` | Ver todos los mensajes |

Abrir el dashboard y apretar **Iniciar**.

## 3. ¿Llegan los datos? Cómo comprobarlo

**A mano:** en la terminal 5, por cada manzana deben aparecer en orden, con el mismo `piece_id`:
```
sorter/sensor/arrival    {"piece_id": 7, ...}
sorter/vision/result     {"piece_id": 7, "color": "rojo", "output_channel": 2, ...}
sorter/control/diverted  {"piece_id": 7, "output_channel": 2, ...}
```

**Automático:** revisa los mensajes Y la base de datos, y dice OK o qué falló:
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
| Botón de emergencia del dashboard | Aparece `sorter/emergency` y la banda se detiene |

**Pruebas unitarias:** `python -m pytest tests`

## 4. Pasar al hardware real (de a una pieza)

Guía completa de cableado y encendido, con una prueba por paso: [docs/conexion-paso-a-paso.md](docs/conexion-paso-a-paso.md).

1. **Arduino UNO R4 WiFi**: copiar `firmware/control_uno_r4/secrets.h.example` como `secrets.h` y
   completarlo (la IP del PC sale de `ipconfig`). Instalar el paquete de placas "Arduino UNO R4
   Boards" y las librerías PubSubClient y ArduinoJson. Para probarlo sin la banda, activar `MODO_BANCO` en `config.h`:
   cada `m` en el Monitor Serie simula una manzana. Cerrar el simulador (terminal 4) y repetir
   la sección 3: los mensajes deben ser los mismos.
2. **Webcam externa**: conectarla al PC y ver qué índice tiene con `python -m vision.listar_camaras`
   (con `--ver 1` se ve la imagen de la cámara 1). Poner ese número en `CAMERA_INDEX` del `.env`.
   Luego calibrar con manzanas reales y la luz del túnel (`python -m vision.calibrar_hsv`,
   tecla `s` para guardar) y correr la visión sin `--simular`.
3. **Pines** (`config.h`): están marcados POR CONFIRMAR; revisarlos antes de cablear.

> Si el Arduino no llega al PC en la red del laboratorio (puede haber aislamiento entre
> clientes), probar con el hotspot de un celular.
