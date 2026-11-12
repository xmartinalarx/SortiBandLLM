# CLAUDE.md

Contexto completo del proyecto para Claude Code y para el equipo. Actualizar cada vez que cambie una decisión, un tópico MQTT, una tabla o una medida.

## Proyecto

**Clasificador automático IoT de manzanas sobre banda transportadora (MVP).** Una banda de eslabones impresa en 3D lleva manzanas, de a una, bajo una cámara. El PC las clasifica por color y detecta las defectuosas. Dos paletas movidas por servos las desvían a tres salidas. Cada manzana queda registrada en una base de datos, y el proceso se monitorea y controla desde un dashboard web. Un modelo de visión local (Ollama) supervisa la banda completa con una cámara de vista general.

Contexto académico: proyecto semestral del ramo **Internet de las Cosas** (Área de Informática). Docente: Paola Celis. Grupo de 4 integrantes. Se entrega un informe (Parte 1) y un prototipo funcional a fin de semestre.

Nombre: **SortiBandLLM**, del grupo **pythonGroup** (Martín Alarcón, Martín Araya, Vicente Pereira y Reinaldo Castillo). La base de datos y algunos archivos conservan el nombre anterior `clasifiot`.

## Requisitos del ramo (no negociables)

- Resuelve una problemática real y es replicable en otros espacios.
- Hay conexión IoT entre dispositivos (varios nodos que se comunican por red).
- Los datos se visualizan en un dashboard.
- Los datos se guardan en una BD (servidor del laboratorio de Hardware o nube).
- Hay un prototipo funcional al final del semestre.
- El informe incluye: problemática, solución propuesta, diagrama de la solución y materiales.

## Problemática

Los pequeños productores clasifican la fruta a mano, lo que es lento, cansador y subjetivo, y no deja registro de cuántas piezas se procesaron ni de cuántas salieron defectuosas. Las clasificadoras industriales son caras y grandes. Este sistema es de bajo costo, usa piezas comunes y una estructura impresa en 3D, y sus criterios son configurables: se puede replicar con otra fruta cambiando reglas, guías y rampas.

## Alcance del MVP

- **Producto:** manzanas de 7 a 8,5 cm y 150 a 250 g.
- **Salidas:** 3. Salida 1 (derecha, paleta 1): defectuosas. Salida 2 (izquierda, paleta 2): grupo de colores A (configurable). Salida 3 (final de la banda): resto.
- **Flujo:** una manzana a la vez bajo la cámara, separadas al menos ~280 mm.
- **Clasificación:** la decide un modelo de IA de **Hugging Face** (CLIP zero-shot, `ia/vision/modelo_ia.py`) en el PC-IA, con la GPU. Compara la foto con frases (`ia/vision/prompts_ia.json`) para el color y para sana/dañada. OpenCV (HSV, `ia/vision/analisis.py`) queda de respaldo automático y para recortar el producto. Todo motor respeta el contrato de `ia/vision/analisis.py::clasificar_imagen` (entra una imagen BGR; sale `color`, `is_defective`, `confidence`, `bbox`). Las fotos de cada manzana se guardan sin dibujos en `data/imagenes/` y sirven de dataset.
- **Prioridad si falta tiempo:** banda y clasificación local → BD y dashboard → supervisión con Ollama. Los reportes en lenguaje natural quedan fuera del MVP.

## Arquitectura

| Nodo | Hardware | Función | Comunicación |
|---|---|---|---|
| PC-servidor | PC con Windows | Broker Mosquitto, MySQL (XAMPP), API FastAPI y dashboard (y Ollama, fuera del MVP) | Red WiFi |
| PC-IA | PC con GPU NVIDIA (RTX 3050) + webcam (por ahora la integrada; después la externa del túnel) | Visión: IA de Hugging Face (CLIP) que mira la cámara y decide | MQTT al broker + HTTP al servidor (configuración y fotos) |
| Control | Arduino UNO R4 WiFi | Motor 28BYJ-48 (placa ULN2003), 2 servos MG996R, sensor IR y pulsador de emergencia | MQTT por WiFi |
| Supervisión | Segunda webcam USB en un poste (por confirmar) | Foto de vista general para el supervisor | USB al PC |
| Usuario | Navegador en PC o celular | Ver datos y controlar la banda | HTTP |

**Dos equipos, dos carpetas:** el código está separado en `servidor/` (se copia al PC-servidor) e `ia/` (se copia al PC-IA). Cada carpeta tiene su `.env`, `requirements.txt`, entorno de Python y `LEEME.md`, y se levanta sola. El PC-IA no toca la BD: lee la configuración con `GET /api/settings` y sube cada foto con `POST /api/imagenes` (`SERVER_URL` y `MQTT_HOST` en `ia/.env` = IP del PC-servidor). Para probar en un solo PC se levantan las dos carpetas con `localhost`. Instalación del PC-servidor: `servidor/scripts/instalar_servidor.ps1`.

La clasificación usará una **webcam USB externa** montada en el túnel y conectada al PC. **Por ahora se usa la webcam integrada del PC** (`CAMERA_INDEX=0`) hasta tener la externa. Evitar la cámara virtual de NVIDIA Broadcast: aplica efectos y cambia los colores. Su índice se configura en `CAMERA_INDEX` (`.env`); para encontrarlo: `python -m vision.listar_camaras`. La Raspberry Pi como nodo de visión independiente queda para una versión posterior.

### Flujo por manzana

1. El sensor IR (x = 170 mm) detecta la manzana. El Arduino le asigna un `piece_id` y guarda la posición del motor (en pasos).
2. Cuando la manzana avanzó 110 mm (centrada en el túnel, x = 280 mm), el Arduino publica `sorter/sensor/arrival` y la webcam externa captura la imagen.
3. El PC clasifica y publica `sorter/vision/result` con la salida asignada.
4. El Arduino cierra la paleta correspondiente según los mm avanzados (no según la hora) y la mantiene cerrada mientras sale. Si el resultado no llega antes del punto de cierre de la paleta 1, la manzana va a la salida 3.
5. El Arduino publica `sorter/control/diverted` con la salida real, el PC registra la manzana en la BD y el dashboard se actualiza.

**Seguimiento por pasos del motor:** como el Arduino mueve el 28BYJ-48 (cada medio paso lo da un timer por hardware), sabe cuántos mm avanzó cada manzana. Así no depende de relojes sincronizados, del retardo de MQTT ni de cambios de velocidad. Distancias en `firmware/control_uno_r4/config.h` (iguales en `servidor/simulador/sim_control.py`).

### Tiempos (a 30 mm/s, velocidad por defecto del 28BYJ-48)

| Tramo | Distancia | Tiempo disponible |
|---|---|---|
| Sensor IR → centro del túnel | 110 mm | 3,7 s |
| Cámara → paleta 1 debe estar cerrada | 227 mm | 7,6 s |
| Cámara → paleta 2 debe estar cerrada | 527 mm | 17,6 s |

- **Tiempo necesario:** clasificación (~50 ms) + MQTT (20–200 ms) + giro del servo a 45° (~0,15 s) ≈ 0,4 s.
- **Salida de una manzana desviada:** se desliza por la paleta a ~0,7 × la velocidad de la banda y tarda ~280 mm / v (≈ 9,3 s a 30 mm/s). La paleta sigue cerrada todo ese tiempo.
- **Capacidad:** cada paleta queda cerrada ~310 mm de recorrido (280 mm de salida + 30 mm de margen del servo), así que la separación mínima entre manzanas es ~310 mm: unas 6 manzanas por minuto a 30 mm/s (máximo ~7–8 a 40 mm/s). Con menos separación, la manzana siguiente se desvía por la misma paleta (`verificar_flujo` lo muestra como aviso).
- Las distancias reales se calibran con pruebas, no solo con cálculo.

## Reglas de diseño de IA

1. **La clasificación de cada manzana es visión local, no LLM.** Un modelo de Hugging Face (CLIP) corre en la GPU del PC-IA: ~20–50 ms por foto y sin internet una vez descargado. Si la IA no carga o falla, decide OpenCV (`crear_motor` en `ia/vision/modelo_ia.py`).
2. **El LLM es un supervisor asíncrono.** Recibe una foto de la cámara de supervisión cada 10–30 s, o ante un evento (banda en marcha sin manzanas, varias seguidas con baja confianza, alza de defectuosas). Nunca está en el camino crítico.
3. **Ollama local** en el mismo PC, sin internet ni clave de API. El modelo debe ser de visión (por ejemplo, Gemma 3 o Qwen2.5-VL en versión pequeña).
4. **Respuesta estructurada:** pasar el esquema JSON en el parámetro `format` de Ollama y usar temperatura 0. Esquema: `{"status": "normal|jam|foreign_object|other", "description": "...", "recommend_stop": true|false}`. Validar el JSON y manejar timeouts y respuestas inválidas.
5. **Degradación segura:** si falla Ollama, la clasificación sigue y solo se pausa la supervisión.
6. **El LLM no es el único freno:** hay parada de emergencia física y parada desde el dashboard.
7. **Configuración por variables de entorno** (`LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_HOST`), nunca escrita en el código.

## MQTT

| Tópico | Publica | Payload |
|---|---|---|
| `sorter/sensor/arrival` | Control (manzana centrada bajo la cámara) | `piece_id, ts` |
| `sorter/vision/result` | Visión (PC-IA) | `piece_id, ts, color, is_defective, confidence, output_channel, image_path, model` (`model` = quién decidió: `openai/clip-vit-base-patch32` u `opencv`) |
| `sorter/control/command` | Servidor/web | `action` (`start`, `stop`, `set_speed`, `servo`), `value`; con `servo` además `servo` (1 o 2) y `value` = ángulo |
| `sorter/control/servo` | Control | `servo, angle, ok, motivo?, ts`: confirma la prueba manual de un servo (solo con la banda detenida) |
| `sorter/control/status` | Control (retenido; Last Will `{"state":"offline"}`) | `state` (`running`, `stopped`, `emergency`, `offline`), `speed, ts` |
| `sorter/control/diverted` | Control | `piece_id, output_channel` (salida real), `ts` |
| `sorter/supervision/event` | Servidor | `status, description, recommend_stop, image_path, ts` |
| `sorter/emergency` | Cualquier nodo | `source, ts` |

- Mensajes en JSON, con QoS 1 en comandos y emergencia.
- Las fotos de supervisión las toma el PC directamente (webcam USB); no viajan por MQTT.
- Si el Arduino pierde la conexión con el broker, detiene la banda.
- El `ts` del Arduino viene de NTP (`WiFi.getTime()`) (0 si no hay). La BD guarda la hora del PC al recibir cada mensaje.

## Base de datos

- **Motor:** MySQL 8. Esquema en `servidor/server/db/schema.sql`.
- **Ubicación:** servidor del laboratorio de Hardware; durante el desarrollo, copia local en el PC.
- **Imágenes:** se guarda la ruta, no la imagen.

| Tabla | Campos |
|---|---|
| `batches` | id, started_at, ended_at, product |
| `pieces` | id, batch_id, piece_id, ts, color, is_defective, confidence, output_channel, image_path, diverted_ts, true_color, true_defective |
| `supervision_events` | id, ts, status, description, recommend_stop, image_path |
| `settings` | key, value (mapeo color a salida, velocidad, umbral de confianza) |

`true_color` y `true_defective` se anotan a mano en las pruebas (matriz de confusión). `diverted_ts` viene de `sorter/control/diverted` (latencia).

## Dashboard web

- **Muestra:** total procesado, conteo y % por color, % de defectuosas, manzanas por minuto, confianza promedio, estado y velocidad de la banda, historial, fotos de rechazadas y línea de tiempo del supervisor.
- **Controla:** iniciar/detener, velocidad, mapeo color → salida, parada de emergencia y **prueba de servos** (abrir, cerrar, probar o mover a un ángulo cada paleta; el Arduino confirma; solo con la banda detenida).
- **Tecnología:** FastAPI (`servidor/server/api`) sirve la API y la página (`servidor/web/`, HTML + JS sin frameworks, consulta la API cada 1,5 s).

## Mecánica (impresa en 3D)

### Medidas generales

| Elemento | Medida |
|---|---|
| Banda armada | 1.070 × 200 × 73 mm (largo × ancho × alto) |
| Distancia entre ejes | 1.000 mm (50 eslabones por tramo recto, 110 en total) |
| Conjunto con paletas, servos y motor | ~1.080 × 330 × 170 mm |
| Superficie de transporte sobre el centro del eje | 36 mm |
| Túnel de cámara (espacio reservado) | 160 × 260 × 220 mm |

### Distribución a lo largo de la banda

Medido desde el eje del piñón tensor (x = 0), en el sentido de avance.

| Zona | Posición |
|---|---|
| Carga | 0–150 mm |
| Sensor IR | 170 mm |
| Túnel de cámara | 200–360 mm (cámara en 280 mm, a ~200 mm de altura) |
| Paleta 1 (pivote lado izquierdo) | 450 mm; salida derecha en 560–670 mm |
| Paleta 2 (pivote lado derecho) | 750 mm; salida izquierda en 860–960 mm |
| Salida 3 | después de 1.000 mm |

### Piezas

| Pieza | Cantidad | Medidas / detalle |
|---|---|---|
| Eslabón | 112 (110 + 2 de repuesto) | 28 × 200 × 8 mm; paso 20 mm; placa de 2 mm; bisagras Ø 8 mm alternadas; agujero Ø 2,1 mm |
| Pasador | 110 | Filamento PLA+ Ø 1,75 × 202 mm |
| Piñón | 6 (3 por eje, en y = 29, 100 y 171 mm) | Ø 64 × 14 mm; 10 dientes; radio primitivo 32,4 mm; eje 8 mm; prisionero M3 |
| Tramo de cama de deslizamiento | 5 (de x = 50 a 950) | Escalera de 180 × 198 × 3 mm, rieles bajo las bisagras |
| Paleta | 2 | 300 × 46 × 4 mm; se imprime en parte A (202 mm) y parte B (144 mm) unidas por traslape con 2 M3 |
| Soporte de servo | 2 | 70 × 45 × 85 mm; servo invertido, con ranuras M4 para ajustar la altura |

### Desviadores

- Funcionan como compuerta, no como empujador: el servo gira la paleta 45° y el avance de la banda lleva la manzana a la salida.
- El pivote va 12 mm fuera del borde. La paleta queda a 2 mm sobre la banda.
- El MG996R (9–11 kg·cm, 0,15–0,19 s/60°) va invertido sobre la paleta, con el cuerpo aguas abajo del pivote (su eje está a 10,2 mm de un extremo).
- El brazo doble del servo calza en un bolsillo del cubo de la paleta y se fija con 2 autorroscantes de 2 mm.

### Validación en simulación

- Los eslabones no chocan entre sí, ni en recta ni doblados hasta 45°.
- Los eslabones no chocan con los piñones.
- El diente del piñón engancha la bisagra hasta su eje (punta a 32,3 mm; eje de la bisagra a 32,4 mm).

## Electrónica y compras

| Material | Cantidad | Nodo |
|---|---|---|
| PC (16 GB RAM; ideal con GPU de 6–8 GB) | 1 | Servidor |
| Webcam USB externa | 1 | Servidor (túnel) |
| Iluminación LED blanca | 1 | Túnel |
| Arduino UNO R4 WiFi | 1 | Control |
| Motor paso a paso 28BYJ-48 (5 V) + placa ULN2003 | 1 | Control |
| Servo MG996R | 2 | Control |
| Sensor IR de barrera | 1 | Control |
| Pulsador de emergencia (push button) | 1 | Control |
| Webcam USB de supervisión (por confirmar) | 1 | Supervisión |
| Cargador de celular 5 V (≥ 2 A, ideal 3 A) para los servos y el motor | 1 | Potencia |
| Eje de acero de 8 × 260 mm | 2 | Mecánica |
| Rodamiento 608 | 4 | Mecánica |
| Acople flexible de 5 a 8 mm | 1 | Mecánica |
| Tornillos M3 × 16 con tuerca (~30) y M4 (4) | — | Mecánica |
| PETG blanco 1,75 mm | ~2,2 kg (medio rollo por persona) | Impresión |

## Impresión: reparto entre los 4 integrantes

Cada integrante imprime 28 eslabones (4 placas de 7) más un subsistema, con el mismo perfil y PETG blanco. Se imprime en la **Creality Ender-3 V3 KE del laboratorio** (cama 220 × 220 mm, Klipper).

| Integrante | Imprime | Tiempo en la KE |
|---|---|---|
| Persona 1 | Eslabones + 2 paletas (A y B) + 1 cama | ~30 h |
| Persona 2 | Eslabones + 2 soportes de servo + 2 camas | ~29 h |
| Persona 3 | Eslabones + 3 piñones (eje tensor) + 1 cama | ~28 h |
| Persona 4 | Eslabones + 3 piñones (eje motriz) + 1 cama | ~28 h |
| **Total** | | **~115 h**, ~2,1 kg de PETG + ~70 g de pasadores |

- **Avance (2026-11-12):** prueba de tolerancia hecha y **4 placas de eslabones impresas** (28 de 112). Faltan 12 placas de eslabones (~65 h) + paletas, 5 camas, soportes y 2 placas de piñones (~27,5 h): ~92 h en total, ~46 h por impresora con las **2 impresoras** disponibles (modelo de la segunda: por confirmar; los G-code `_v2` son solo para la KE).
- **La KE solo lee `.gcode`**, desde un USB FAT32 con nombres sin espacios ni tildes. Usar solo los de `hardware/3d/manzanas/gcode_Ender3V3KE_0.4_v2/` (terminan en `_v2`); guía en su `PASO_A_PASO.md`.
- **Error key:2111:** lo daban los G-code v1, que extruían antes de que la boquilla volviera a 240 °C después de nivelar. Los v2 calientan (`M190`/`M109`) después de `START_PRINT`.
- **Perfil (PrusaSlicer):** PETG blanco 240/70 °C, capa 0,2 mm, 3 perímetros, relleno 25 % gyroid, sin soportes; brim de 6 mm solo en las paletas.
- **Agujero de los eslabones: 2,1 mm** (`01_eslabones_agujero_d21_v2.gcode`). Con 2,0 mm el pasador se traba al pasar por las 9 bisagras; esos eslabones sirven si se repasan con una broca de 2 mm, y se pueden mezclar.
- **Pasadores:** filamento PLA+ de 1,75 mm, enderezado, punta en diagonal, metido girando y cortado a ras.
- **Armado de la banda:** cada uno arma su tramo de 28 eslabones (bisagras hacia abajo); al final se unen los 4 tramos.
- Si se acaba el filamento, el sensor pausa la impresión: cargar uno nuevo y reanudar.

## Hardware y seguridad

- Prototipo en baja tensión (5 V); nada de 220 V en la banda, los servos ni la iluminación.
- Motor y servos con fuentes separadas de la electrónica, uniendo las tierras (GND).
- **Parada de emergencia:** pulsador entre D7 y GND (patas en diagonal). Detiene la banda por software; no corta la energía. Para un corte físico haría falta un hongo con contacto NC en el + del cargador.
- Protoboard: riel rojo de arriba = 5 V del cargador (servos y motor); riel rojo de abajo = 5 V del Arduino (lógica). Los + nunca se unen; los GND sí (puente entre rieles azules). Detalle en `docs/conexion-paso-a-paso.md`.
- Iluminación constante y sin reflejos dentro del túnel (opaco, interior blanco mate).
- La cámara de supervisión sirve para ver la banda completa, no para distinguir colores con precisión.
- El UNO R4 trabaja con lógica de 5 V: conecta directo a la ULN2003, los servos y el sensor IR.
- Webcam externa: si el driver lo permite, fijar el enfoque, la exposición y el balance de blancos (sin modo automático) para que el color no cambie entre fotos.
- La visión con fruta es más difícil que con objetos de color parejo: calibrar HSV con manzanas reales y bajo la luz del túnel.
- Velocidad sugerida: 30 mm/s (~9 rpm en el piñón). El 28BYJ-48 llega a ~12 rpm (40 mm/s); más rápido pierde pasos.
- **Riesgo del motor:** el 28BYJ-48 da ~0,03 N·m y la banda de 1 m podría necesitar ~0,15–0,25 N·m (estimación). Probar primero; si no alcanza: reducción adicional (más lenta), banda más liviana o volver a NEMA 17 + A4988.

## Estructura del repositorio

El proyecto vive en `proyecto-final/`. Afuera, en la carpeta del ramo, quedan las actividades de clase (`15-10-2026/`, `22-10-2026/`), `driver/` y `herramientas/midi_a_arduino.py`.

```
proyecto-final/
├── CLAUDE.md
├── README.md
├── .env.example
├── docs/
│   ├── informe-parte1.md        # aún en versión M&M: actualizar a manzanas
│   ├── informes/                # Word exportados: informe de la segunda entrega y sensores/seguimiento
│   ├── conexion-paso-a-paso.md  # cableado y encendido de los nodos, con pruebas
│   └── conexiones-clasifiot.html # guía visual del protoboard (abrir en el navegador)
├── hardware/
│   └── 3d/
│       └── manzanas/            # versión vigente
│           ├── LEEME.md
│           ├── banda_manzanas.scad
│           ├── gcode_Ender3V3KE_0.4_v2/ # G-code listos para la KE + PASO_A_PASO.md + perfil
│           ├── stl/             # piezas/ (sueltas) y placas/ (cama de 220 × 220)
│           ├── blender/         # escena .blend/.glb, renders y script
│           ├── imagenes/        # renders para el informe
│           └── impresion/       # REPARTO.md y persona_1 … persona_4
├── firmware/
│   └── control_uno_r4/          # Arduino UNO R4 WiFi
├── servidor/                    # PC-SERVIDOR (se copia a ese PC; ver servidor/LEEME.md)
│   ├── comun/                   # config (.env), tópicos MQTT (+ COLORES) y conexión a MySQL
│   ├── server/
│   │   ├── api/                 # FastAPI + puente MQTT -> MySQL
│   │   ├── db/                  # schema.sql
│   │   ├── supervisor/          # cliente de Ollama (fuera del MVP)
│   │   └── mosquitto/           # mosquitto.conf
│   ├── web/                     # dashboard
│   ├── simulador/               # sim_control.py: reemplaza al Arduino para probar sin hardware
│   ├── herramientas/            # verificar_flujo.py (punta a punta)
│   ├── scripts/                 # instalar_servidor.ps1 (deja listo el PC-servidor)
│   ├── data/imagenes/           # fotos que sube el PC-IA
│   └── requirements.txt, .env.example, LEEME.md
└── ia/                          # PC-IA (se copia a ese PC; ver ia/LEEME.md)
    ├── comun/                   # config (.env) y tópicos MQTT (+ COLORES): copia de servidor/comun/topicos.py
    ├── vision/                  # clasificador.py, modelo_ia.py (CLIP), prompts_ia.json, analisis.py (OpenCV), reglas.py, calibrar_hsv.py, listar_camaras.py
    ├── herramientas/            # comparar_motores.py (IA vs OpenCV)
    ├── tests/                   # pytest
    ├── data/imagenes/           # copia de cada foto (dataset)
    └── requirements.txt, requirements-ia.txt, .env.example, LEEME.md
```

## Convenciones

- Documentación, comentarios, commits y textos de la interfaz en español.
- Identificadores de código, tópicos MQTT, claves JSON y columnas de BD en inglés (`snake_case`).
- Secretos solo en `.env` (uno en `servidor/` y otro en `ia/`), nunca en el repositorio. Mantener los dos `.env.example` al día.
- `comun/topicos.py` está duplicado en `servidor/comun/` e `ia/comun/` (para que cada carpeta funcione sola): todo cambio de tópicos o de `COLORES` se hace en los dos y en el firmware. El servidor no importa nada de `ia/` ni al revés.
- Cada componente debe poder probarse sin hardware (modo simulación que publique resultados falsos por MQTT).
- Código simple y comentado donde no sea obvio: el equipo debe poder explicarlo en la evaluación.
- Todo cambio en tópicos, payloads, tablas o medidas se actualiza en este archivo.

## Planificación (16 semanas, ajustar al calendario real)

| Semanas | Fase | Entregable |
|---|---|---|
| 1–2 | Definición | Informe Parte 1 |
| 3–4 | Mecánica e impresión 3D | Banda impresa y armada (3 días de impresión en paralelo), bastidor, túnel |
| 5–6 | Visión | Clasificación de manzanas por color y defectos, medición de aciertos |
| 7–8 | Comunicación y datos | MQTT PC-Arduino, BD, registro por manzana |
| 9–10 | Desviadores | Servos y paletas con tiempos calibrados |
| 11–12 | Dashboard y supervisión | Web con conteos y control, pruebas con Ollama |
| 13 | Integración | **Hito: MVP integrado** |
| 14 | Mejoras (fuera del MVP) | Opcional |
| 15–16 | Cierre | Informe final, demo y documentación para replicar |

## Medición de resultados

Registrar una matriz de confusión (color real vs. clasificado; buena vs. defectuosa), la latencia entre la clasificación y el desvío, y la tasa de manzanas que llegan a la salida correcta.

## Historial de decisiones

| Cambio | Motivo |
|---|---|
| M&M → manzanas | El grupo eligió un producto más cercano a un caso real |
| Banda de 40 mm → 200 mm de ancho | Tamaño de la manzana y paletas que cruzan toda la banda |
| 500 → 800 → 1.000 mm entre ejes | Más zona de carga, margen entre túnel y paletas, y salidas alejadas del final |
| Banda de goma → banda de eslabones impresa | Todo el prototipo se imprime en 3D |
| SG90 → MG996R | La paleta de 300 mm con una manzana requiere ~2–3 kg·cm |
| Proveedor del LLM → Ollama local | Sin internet, sin clave de API y sin costo por uso |
| Seguimiento por tiempo → por pasos del motor | No depende de relojes, retardo de MQTT ni cambios de velocidad |
| `arrival` en el IR → `arrival` bajo la cámara, con `piece_id` | El Arduino avisa cuándo sacar la foto y numera las manzanas |
| ESP32 → Arduino UNO R4 WiFi (control) | Decisión del grupo (anotar el motivo) |
| ESP32-CAM → webcam USB de supervisión | Se quitan los ESP32 del proyecto; la cámara va conectada al PC |
| Webcam en el PC (por confirmar) → webcam USB externa | Se monta en el túnel, con luz controlada (por ahora: webcam integrada del PC) |
| Archivos del proyecto → carpeta `proyecto-final/` | Separar el proyecto de las actividades del ramo |
| NEMA 17 + A4988 → 28BYJ-48 + ULN2003 (5 V) | Es el motor que tiene el grupo; no necesita fuente de 12 V. Velocidad máxima 40 mm/s |
| Servos con fuente propia → cargador de celular 5 V | Es la fuente disponible; alimenta servos y motor desde el riel de arriba |
| Manzanas → latas de bebida (temporal, perfil `PRODUCTO=lata`) | Probar el sistema mientras no hay manzanas; se vuelve con `PRODUCTO=manzana` |
| MySQL Server → MariaDB de XAMPP (desarrollo) | Ya estaba instalado y no requiere administrador; mismo SQL |
| Hongo de emergencia → pulsador común (D7 a GND) | Es el botón que tiene el grupo. Detiene por software; no corta la energía |
| Clasificación OpenCV → IA de Hugging Face (CLIP) con OpenCV de respaldo | El grupo quiere que una IA mire la cámara y decida; CLIP funciona sin entrenar |
| Un PC → dos (PC-IA con GPU y webcam; PC-servidor con lo demás) | La IA usa la GPU sin competir con la BD y el servidor; suma un nodo a la red IoT |
| Red de la U → hotspot del celular POCOX7Pro | La red de la U es de 5 GHz y abierta; el R4 solo usa 2,4 GHz. Plan B probado: zona WiFi del PC |
| Impresora genérica tipo Ender-3 → Ender-3 V3 KE del laboratorio, G-code `_v2` | Es la máquina real; los G-code v1 daban el error key:2111 |
| Agujero del eslabón 2,0 → 2,1 mm | Con 2,0 mm el pasador se traba en las 9 bisagras |
| Repositorio `Reicas23/IOT-PROYECT` → `xmartinalarx/SortiBandLLM` | El oficial es SortiBandLLM (2026-11-12) |
| Código en la raíz → carpetas `servidor/` e `ia/` | Cada PC recibe solo lo suyo y se levanta solo; `comun/topicos.py` queda duplicado. El PC-IA ya no lee MySQL (2026-11-12) |

## Decisiones

- [x] Producto del MVP: manzanas
- [x] Proveedor del LLM: Ollama local en el PC
- [ ] Modelo de visión de Ollama (probar Gemma 3 o Qwen2.5-VL pequeños)
- [x] Clasificación con IA de Hugging Face: CLIP zero-shot en la GPU (después, opcional: modelo entrenado con las fotos propias)
- [x] Dos equipos: PC-IA (cámara + IA) y PC-servidor (broker, BD, API, dashboard)
- [x] Salidas: 3, con 2 paletas y servos MG996R
- [x] Estructura y banda: impresas en 3D (PETG)
- [x] Reparto de impresión entre los 4 integrantes
- [x] Visión: webcam USB externa conectada al PC (por ahora, la integrada del PC)
- [x] Control: Arduino UNO R4 WiFi (reemplaza al ESP32)
- [ ] Cámara de supervisión (supuesto: segunda webcam USB en el PC)
- [ ] Criterio de colores y de defecto para manzanas
- [x] Motor de BD: MySQL
- [ ] Confirmar con la docente que la BD en el servidor del laboratorio cumple el requisito
- [x] Dashboard: FastAPI + página web
- [x] Seguimiento de cada manzana por pasos del motor
- [ ] Confirmar que el 28BYJ-48 mueve la banda cargada (si no: reducción, banda más liviana o NEMA 17)
- [x] Nombre del proyecto: SortiBandLLM (grupo pythonGroup)
- [ ] Reparto de roles del grupo (fuera de la impresión)

## Estado actual (2026-11-04)

**MVP funcionando de punta a punta con el Arduino real** (en modo banco, sin sensor IR ni banda montada):
Arduino UNO R4 WiFi → MQTT → visión (webcam del PC) → MQTT → Arduino decide la paleta → MySQL → dashboard.
Prueba del 2026-11-04: 4 piezas, cada una con `arrival` → `result` (~20 ms) → `diverted`, salida real = pedida,
guardadas en el lote 6 (`product = lata`) con su foto.

| Parte | Estado |
|---|---|
| Firmware `control_uno_r4` | Compila y está cargado en el Arduino. `MODO_BANCO` **activo** (cada `m` por serie = una pieza) |
| Red | Hotspot del celular **POCOX7Pro** (2,4 GHz), red elegida por el grupo. La red de la U no sirve (5 GHz, abierta). Si el hotspot aísla a los equipos, reiniciarlo (ver Problemas conocidos) |
| Broker | Mosquitto instalado como servicio de Windows, con `listener 1883 0.0.0.0` en su `mosquitto.conf` |
| BD | MariaDB de XAMPP (compatible con MySQL 8), base `clasifiot` |
| Visión | Webcam integrada del PC (`CAMERA_INDEX=0`), ventana en vivo con rectángulo; perfil `PRODUCTO=manzana` con `ia/vision/calibracion_manzana.json` (verde desde tono 23) |
| Producto de prueba | **Manzana real** desde el 2026-11-05: manzana verde → "verde, sana, 0,99" → salida 3. El perfil `lata` (latas de bebida) queda disponible con `PRODUCTO=lata` |
| Motor | 28BYJ-48 + ULN2003, 30 mm/s. **No probado con la banda cargada** (riesgo de fuerza) |

**Próximos pasos:**
1. Probar más manzanas (rojas, amarillas, con manchas reales) y ajustar `ia/vision/calibracion_manzana.json`; anotar `true_color`/`true_defective` para la matriz de confusión.
2. Confirmar físicamente LEDs A–D, giro del motor y movimiento de los servos (con el cargador enchufado).
3. Conectar el sensor IR, quitar `MODO_BANCO` y montar la banda.
4. Probar si el 28BYJ-48 mueve la banda cargada.
5. Reemplazar OpenCV por un modelo de Hugging Face respetando el contrato de `clasificar_imagen`.

**Guía visual de armado:** `docs/conexiones-clasifiot.html` (protoboard paso a paso; se abre en el navegador). Versión en texto: `docs/conexion-paso-a-paso.md`.

## Problemas conocidos y soluciones

- **Windows Defender, "acceso controlado a carpetas":** impide que Arduino escriba en *Documentos*. Las librerías van en `C:\Users\<usuario>\Arduino`; en el IDE: *Archivo → Preferencias → Ubicación del sketchbook* = esa carpeta.
- **Librerías del firmware:** PubSubClient, ArduinoJson y **Servo** (Servo no viene con el paquete UNO R4).
- **El Arduino IDE retiene el puerto COM** aunque se cierre el Monitor Serie: para usar el puerto desde otro programa hay que cerrar el IDE completo.
- **`struct Pieza` va antes de cualquier función** en el `.ino`: el IDE genera prototipos automáticos al inicio y fallan si el tipo se define después.
- **Mosquitto 2 solo acepta conexiones locales** si no se declara `listener 1883 0.0.0.0`. Abrir el puerto 1883 (y 8000 para el dashboard) en el firewall.
- **La IP del PC cambia** con la red: revisar con `ipconfig` y actualizar `MQTT_HOST` en `firmware/control_uno_r4/secrets.h` (en POCOX7Pro fue 10.157.200.37 los días 4 y 5 de noviembre).
- **Hotspot del celular con aislamiento de clientes:** el Arduino entra al WiFi pero da `MQTT falló (estado -2)` y el PC no lo ve (ni ping ni ARP). Solución: apagar y encender la zona Wi-Fi del celular (el 2026-11-05 bastó con eso). Plan B: zona WiFi del propio PC (Configuración → Red e Internet → Zona con cobertura inalámbrica móvil, banda 2,4 GHz; PC = 192.168.137.1). El Monitor Serie muestra la IP del Arduino y del broker en cada intento fallido.
- **Cámara virtual de NVIDIA Broadcast:** aparece como otra cámara (hoy la 1) y altera los colores. Usar la real (hoy la 0).
- **Color corrido por la cámara:** la webcam del PC ve una manzana verde con tono 22–31 (el perfil por defecto pone el verde desde 35). Se corrige en `ia/vision/calibracion_manzana.json`, no en el código.
- **Sombras confundidas con manchas:** con luz de arriba, la mitad inferior de la manzana se oscurece. Las manchas se detectan comparando cada zona con su alrededor (`manchas_locales`, parámetro `defecto_ratio`), así una sombra suave no cuenta como defecto.
- **Cerrar la ventana de la visión (tecla q) apaga la visión:** las piezas siguen, pero van a la salida 3 por falta de resultado.

## Pendiente de diseño

- Bastidor: laterales con alojamiento para rodamientos 608, ranura del tensor y patas.
- Túnel de cámara (160 × 260 × 220 mm, en paneles impresos) con soporte de webcam y LED.
- Rampas de salida y contenedores.
- Barandas laterales y guías de carga para poner las manzanas en fila.
- Poste de la webcam de supervisión.
- Actualizar el informe Parte 1 de M&M a manzanas.

## Cómo trabajar en este proyecto

- Responder en español.
- Si falta un dato (pines, modelo de sensor, estructura de tablas, tópicos), preguntar en vez de inventarlo.
- Proponer antes de cambiar la arquitectura, los tópicos MQTT o las medidas mecánicas.
- Mantener las soluciones simples y explicar brevemente el porqué: es un proyecto de estudiantes.
- Al entregar código, indicar cómo probarlo y cómo simularlo sin hardware.
- Verificar que cada cambio siga cumpliendo los requisitos del ramo.

## Comandos

```bash
# Regenerar una pieza 3D (piezas: eslabon, placa, pinon, cama, paleta_a, paleta_b, soporte_servo, prueba)
openscad -D 'pieza="eslabon"' -o eslabon.stl hardware/3d/manzanas/banda_manzanas.scad

# Regenerar la escena de Blender (y renderizar con --render)
blender -b --python hardware/3d/manzanas/blender/armar_manzanas.py -- --render

# Supervisor local
ollama serve
ollama pull <modelo-de-vision>
```

```bash
# Una terminal por proceso, con el entorno virtual de esa carpeta (.venv\Scripts\activate).
# --- Desde servidor/ (PC-servidor) ---
mosquitto -c server/mosquitto/mosquitto.conf -v     # broker (o el servicio de Windows)
python -m server.api.main                           # API + dashboard en http://localhost:8000
python -m simulador.sim_control                     # banda simulada (o el Arduino real)
python -m herramientas.verificar_flujo --manzanas 10 --velocidad 40   # prueba de punta a punta
mosquitto_sub -h localhost -t "sorter/#" -v         # ver todos los mensajes
# --- Desde ia/ (PC-IA) ---
python -m vision.clasificador                       # visión con ventana en vivo (motor según VISION_MOTOR: ia u opencv; q = salir)
python -m vision.clasificador --simular             # visión sin cámara (manzanas dibujadas)
python -m herramientas.comparar_motores            # IA vs OpenCV en las fotos guardadas, con tiempos
python -m pytest tests                              # pruebas unitarias
python -m vision.listar_camaras                     # ver qué índice tiene la webcam externa
python -m vision.calibrar_hsv                       # calibrar la visión con la webcam
```

```powershell
# PC-IA, desde ia/: dependencias (PyTorch con CUDA + transformers). PYTHONUTF8 evita un error de pip con tildes.
$env:PYTHONUTF8 = "1"; pip install -r requirements.txt -r requirements-ia.txt
# PC-servidor, desde servidor/: instalación completa (Mosquitto, XAMPP, firewall, BD, venv, .env)
powershell -ExecutionPolicy Bypass -File scripts\instalar_servidor.ps1
```

```powershell
# Compilar y subir el firmware sin abrir el IDE (arduino-cli viene dentro del Arduino IDE)
$cli = "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
$env:ARDUINO_DIRECTORIES_USER = "C:\Users\<usuario>\Arduino"
& $cli compile --fqbn arduino:renesas_uno:unor4wifi firmware/control_uno_r4
& $cli upload -p COM8 --fqbn arduino:renesas_uno:unor4wifi firmware/control_uno_r4
& $cli board list   # ver en qué COM está el Arduino
```
