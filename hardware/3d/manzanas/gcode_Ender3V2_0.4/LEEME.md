# G-code para la Creality Ender-3 V2 (boquilla 0,4 mm)

Segunda impresora del grupo (agregada el 2026-11-17). Mismas piezas y mismo PETG que la KE, laminadas con `perfil_PrusaSlicer_Ender3V2_PETG_0.4.ini` (PrusaSlicer 2.8.1).

**Las copias ordenadas para la tarjeta están en `../impresion_usb/<A o B>/Ender3_V2/`.** Ahí también está `REPARTO.txt`, que dice qué imprime cada impresora.

## Diferencias con la KE

| | Ender-3 V3 KE | Ender-3 V2 |
|---|---|---|
| Firmware | Klipper (`START_PRINT`) | Marlin (`G28`, `M190`, `M109`) |
| Nivelación | Automática | A mano con papel (salvo que tenga BLTouch; el G-code manda `M420 S1`, que se ignora si no lo tiene) |
| Extrusor | Directo, retracción 0,8 mm | Bowden, retracción 5 mm |
| Velocidad | Perímetros 100 mm/s, relleno 150, aceleración 3000 | Perímetros 50 mm/s, relleno 70, aceleración 500 |
| Tiempo | 1× | ~1,9× (eslabones: 5 h 25 min → 10 h 22 min) |
| Archivos | Pendrive USB | Tarjeta microSD |

Los archivos `*_E3V2.gcode` **no sirven en la KE** y los de la KE no sirven en la V2.

| Archivo | Tiempo | Filamento |
|---|---|---|
| `portarod_motor_ir_E3V2.gcode` | 12 h 35 min | 125 g |
| `paletas_A_B_E3V2.gcode` (con brim) | 11 h 55 min | 133 g |
| `rampa_final_E3V2.gcode` | 10 h 46 min | 130 g |
| `eslabones_d21_E3V2.gcode` | 10 h 22 min | 95 g |
| `guia_carga_E3V2.gcode` | 8 h 40 min | 76 g |
| `barandas_ir_E3V2.gcode` | 8 h 21 min | 75 g |
| `barandas_final_E3V2.gcode` | 8 h 03 min | 70 g |
| `rampa_lateral_E3V2.gcode` | 7 h 58 min | 97 g |
| `pinones_E3V2.gcode` | 7 h 53 min | 70 g |
| `soportes_servo_E3V2.gcode` | 6 h 20 min | 67 g |
| `cama_E3V2.gcode` | 3 h 38 min | 41 g |
