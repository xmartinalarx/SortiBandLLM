# Conexión paso a paso de ClasifIoT

Guía para conectar los nodos IoT y probarlos **de a uno**. Si algo falla, se sabe en qué paso fue.
Versión visual con el protoboard dibujado: la página "Conexiones ClasifIoT" (pedir el link al grupo).

> Los pines son los de `firmware/control_uno_r4/config.h` (marcados POR CONFIRMAR).
> Si el grupo cambia un pin, se cambia en `config.h` y en esta guía.

---

## Parte A — Lo que se conecta

```
                 WiFi 2,4 GHz (misma red)
   ┌────────────────────────┐         ┌──────────────────────────────┐
   │ PC                     │  MQTT   │ Arduino UNO R4 WiFi          │
   │ - Mosquitto (broker)   │◄───────►│ - motor 28BYJ-48 (ULN2003)   │
   │ - MySQL (XAMPP)        │  1883   │ - 2 servos (paletas)         │
   │ - Servidor + dashboard │         │ - sensor IR                  │
   │ - Visión + webcam      │         │ - botón de emergencia        │
   └──────────┬─────────────┘         └──────────────────────────────┘
              │ HTTP 8000
        Navegador (PC o celular)
```

| Nodo | Qué hace | Cómo se comunica |
|---|---|---|
| PC | Visión, broker, BD, servidor y dashboard | — |
| Arduino UNO R4 WiFi | Mueve la banda y las paletas, lee el sensor y la emergencia | MQTT por WiFi al PC |
| Celular o PC | Ver datos y controlar | Navegador al PC (puerto 8000) |
| Webcam | Foto de cada manzana | USB al PC (por ahora la integrada del PC) |

---

## Parte B — Cableado (todo SIN energía)

**Regla de oro:** se cablea con todo desenchufado. Los **+** de las fuentes nunca se juntan; los **−** (GND) siempre se juntan.

### B1. Las 2 fuentes y el protoboard

| Fuente | Alimenta | En el protoboard |
|---|---|---|
| 5 V del **Arduino** (USB del PC) | Lógica: el sensor IR | Riel rojo de **abajo** |
| 5 V de un **cargador de celular** (≥ 2 A, ideal 3 A) | Los 2 servos y el motor (placa ULN2003) | Riel rojo de **arriba** |

```
 Riel rojo  ARRIBA ═══ 5V CARGADOR  → servos y placa ULN2003 del motor
 Riel azul  ARRIBA ═══ GND ─┐
                            │  puente GND (obligatorio)
 Riel azul  ABAJO  ═══ GND ─┘  ← GND del Arduino
 Riel rojo  ABAJO  ═══ 5V ARDUINO → VCC del sensor IR
        ✖ los dos rieles rojos NUNCA se unen
```

- Marca cada riel rojo con cinta ("CARGADOR" / "ARDUINO").
- Si las líneas de los rieles se cortan a la mitad del protoboard, une las dos mitades con un cable.
- Cargador: cortar un cable USB y usar el **rojo (+5 V)** y el **negro (−)**; aislar el verde y el blanco. Medir ~5 V antes de conectar nada.
- El protoboard aguanta ~1 A: sirve para probar. En la versión final, servos y motor van con bornes.

### B2. Motor 28BYJ-48 y placa ULN2003

La placa es verde, con un chip ULN2003, LEDs **A, B, C, D**, pines **IN1–IN4** y una entrada **5-12V** (+ y −).
El chip tiene 7 canales (IN1–IN7), pero el motor usa solo IN1–IN4.

| Pin de la placa | Va a |
|---|---|
| IN1 | **D6** |
| IN2 | **D5** |
| IN3 | **D4** |
| IN4 | **D3** |
| + (5-12V) | Riel rojo de arriba (cargador) |
| − (5-12V) | Riel azul de arriba |
| Conector blanco | El cable del motor (entra de una sola forma) |

- Si la placa tiene un **puente ON/OFF** junto a la entrada de energía, déjalo puesto.
- El motor es de **5 V** (lo dice su etiqueta). Consume ~0,25 A.
- Los LEDs A–D parpadean cuando el motor gira: sirven para comprobar las señales aunque el motor no se mueva.
- Si la banda avanza al revés, cambia `SENTIDO_INVERTIDO` a 1 en `config.h`.
- **Fuerza limitada:** el 28BYJ-48 da ~0,03 N·m. Probarlo primero con la banda sola y después con manzanas. Si zumba y no avanza, bajar la velocidad (20 mm/s); si aun así no puede, ver `CLAUDE.md` (riesgo del motor).

### B3. Servos MG996R (paletas)

| Cable del servo | Paleta 1 (defectuosas) | Paleta 2 (grupo A) |
|---|---|---|
| Rojo (+) | Riel rojo de arriba (cargador) | Riel rojo de arriba (cargador) |
| Marrón (–) | Riel azul de arriba | Riel azul de arriba |
| Naranjo (señal) | **D9** | **D10** |

- Los servos **no** se alimentan del 5 V del Arduino: cada MG996R puede pedir hasta 2,5 A.
- Recomendado: condensador de 470–1000 µF entre los rieles de arriba.

### B4. Sensor IR de barrera

| Sensor | Va a |
|---|---|
| VCC | Riel rojo de abajo (5 V Arduino) |
| GND | Riel azul de abajo |
| OUT | **D2** |

- Emisor y receptor enfrentados a cada lado de la banda, en **x = 170 mm**, a la altura del centro de una manzana (~35–40 mm sobre la banda).
- El firmware asume **LOW = haz cortado**. Si el sensor da al revés, se cambia en el firmware.
- El modelo del sensor aún no está definido: si tiene otros pines, avisar antes de conectar.

### B5. Botón de emergencia (pulsador)

Es un pulsador común de 4 patas (push button). Va entre **D7** y **GND**:

| Pata del pulsador | Va a |
|---|---|
| Una pata | **D7** |
| La pata **en diagonal** | Riel azul (GND) |
| Las otras dos | Sin usar |

- Por dentro las 4 patas van unidas de a pares: usando dos patas **en diagonal** siempre quedan en lados distintos del interruptor. Si el pulsador tiene 2 patas, se usan esas dos.
- El Arduino usa la resistencia interna (`INPUT_PULLUP`): no hace falta resistencia externa. Apretado = D7 en LOW = emergencia.
- **Detiene la banda por software** (para el motor, abre las paletas y publica `sorter/emergency`); **no corta la energía**. Si el Arduino se cuelga, desenchufar el cargador.
- Para volver a andar: soltar el botón y apretar **Iniciar** en el dashboard.

### B6. Alimentación del Arduino

- Para desarrollar: **cable USB-C al PC** (además sirve para el Monitor Serie).

---

## Dos PCs: PC-IA y PC-servidor

| Equipo | Corre | Configuración |
|---|---|---|
| **PC-servidor** (Windows) | Mosquitto, MySQL (XAMPP), servidor y dashboard | `powershell -ExecutionPolicy Bypass -File scripts\instalar_servidor.ps1`: instala todo y muestra su IP |
| **PC-IA** (con GPU NVIDIA y la webcam) | Visión con IA (CLIP) | `.env`: `VISION_MOTOR=ia`, `MQTT_HOST=<IP del servidor>`, `SERVER_URL=http://<IP del servidor>:8000` |
| **Arduino** | Banda, paletas y sensores | `secrets.h`: `MQTT_HOST` = IP del PC-servidor |

- Los tres en la misma red (hotspot POCOX7Pro, 2,4 GHz).
- Copiar la carpeta `proyecto-final` al PC-servidor **sin** `.venv` ni `data\imagenes`.
- Prueba: en el PC-IA, `python -m vision.clasificador` debe decir `Motor listo: IA clip-vit-base-patch32 (GPU)` y `Configuración leída de http://...`; la foto de cada manzana aparece en el dashboard del PC-servidor.

## Parte C — Preparar el PC (una vez)

1. **Entorno de Python** (desde `proyecto-final/`):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Base de datos:** abrir el panel de XAMPP y apretar *Start* en **MySQL**.
   La base `clasifiot` ya está creada (en otro PC: ver README, sección 1).
3. **Mosquitto:** instalar desde https://mosquitto.org/download/.
4. **Firewall de Windows** (PowerShell como administrador), para que entren el Arduino y el celular:
   ```powershell
   netsh advfirewall firewall add rule name="Mosquitto 1883" dir=in action=allow protocol=TCP localport=1883
   netsh advfirewall firewall add rule name="ClasifIoT web 8000" dir=in action=allow protocol=TCP localport=8000
   ```
5. **Webcam:** por ahora la integrada del PC. Revisar cuál es:
   ```bash
   python -m vision.listar_camaras          # lista las cámaras que responden
   python -m vision.listar_camaras --ver 0  # muestra la imagen (q = salir)
   ```
   Poner el índice correcto en `CAMERA_INDEX` del `.env`. **No usar la cámara virtual de NVIDIA
   Broadcast** (aplica efectos al fondo y cambia los colores).
6. **IP del PC:** `ipconfig` → "Dirección IPv4" del adaptador WiFi. Puede cambiar de un día a otro.

## Parte D — Preparar el Arduino (una vez)

1. Arduino IDE → *Gestor de placas* → instalar **Arduino UNO R4 Boards**.
2. *Gestor de librerías* → instalar **PubSubClient** (Nick O'Leary) y **ArduinoJson** (Benoit Blanchon).
3. En `firmware/control_uno_r4/`, copiar `secrets.h.example` como **`secrets.h`** y completar
   la red, la clave y la IP del PC.
   - La red debe ser de **2,4 GHz** (el R4 no se conecta a 5 GHz).
   - Redes con usuario y clave personal **no funcionan**: usar el hotspot de un celular.

---

## Parte E — Encender y probar, de a un nodo

**No pasar al siguiente paso si el anterior falla.**

| # | Qué hacer | Cómo se comprueba |
|---|---|---|
| 1 | Terminal 1: `mosquitto -c server/mosquitto/mosquitto.conf -v` | Dice `Opening ipv4 listen socket on port 1883` |
| 2 | Terminal 2: `mosquitto_sub -h localhost -t "sorter/#" -v` | Queda esperando (aquí se ve todo lo que viaja) |
| 3 | Terminal 3: `python -m server.api.main` | En http://localhost:8000: *MQTT: conectado* y *BD: conectada* |
| 4 | Terminal 4: `python -m vision.clasificador` | Dice `Visión lista (webcam 0)` |
| 5 | Arduino: activar `#define MODO_BANCO`, conectar **solo** el USB (cargador desenchufado) y subir el programa | Monitor Serie (115200): `WiFi conectado`, `MQTT conectado` |
| 6 | Mirar el dashboard | *banda: detenida* (el Arduino está en línea) |
| 7 | **Iniciar** en el dashboard; luego `m` en el Monitor Serie | En la terminal 2: `arrival` → `result` → `diverted` con el mismo `piece_id`. Los LEDs A–D de la ULN2003 parpadean |
| 8 | Desenchufar el USB del Arduino | El dashboard muestra *banda: sin conexión* (Last Will) |
| 9 | Enchufar el **cargador** (servos y motor, sin la banda montada) | Con **Iniciar**, el eje del motor gira; las paletas parten abiertas y la paleta 1 se mueve con una manzana defectuosa |
| 10 | Apretar el **botón de emergencia** | La banda se detiene, el dashboard muestra *EMERGENCIA* y en la terminal 2 aparece `sorter/emergency` |
| 11 | Quitar `MODO_BANCO`, conectar el sensor IR y montar la banda | Pasar la mano por el sensor: el Monitor Serie dice `Manzana en el sensor IR` |
| 12 | Banda montada: **Iniciar** sin manzanas y después con manzanas | La banda avanza sin trabarse. Si el motor zumba y no avanza, bajar a 20 mm/s |
| 13 | Prueba completa | `python -m herramientas.verificar_flujo --manzanas 10` termina en `RESULTADO: OK` |

**Desde el celular:** conectado a la misma red, abrir `http://<IP-del-PC>:8000`.

---

## Problemas comunes

| Síntoma | Causa probable |
|---|---|
| El Arduino no pasa de `Conectando a ...` | Red de 5 GHz, clave mal escrita o red con usuario personal |
| `MQTT falló (estado -2)` | IP del PC mal escrita en `secrets.h`, Mosquitto apagado o firewall bloqueando el 1883 |
| El dashboard dice *BD: sin conexión* | MySQL apagado en XAMPP, o clave del `.env` incorrecta |
| Los LEDs A–D no parpadean | IN1–IN4 mal conectados o banda detenida (apretar Iniciar) |
| Los LEDs parpadean pero el motor no gira | Falta energía en la placa (cargador, puente ON/OFF) o el conector del motor está suelto |
| El motor zumba y no avanza | La banda pesa demasiado o la velocidad es muy alta: bajar a 20 mm/s |
| Los servos tiemblan o el Arduino se reinicia | Servos alimentados desde el Arduino, rieles rojos unidos o falta el puente de GND |
| Todas las manzanas van a la salida 3 | La visión no está corriendo o la confianza queda bajo el umbral |
| Los colores salen raros | Cámara equivocada (virtual de NVIDIA) o luz que cambia: calibrar con `python -m vision.calibrar_hsv` |
