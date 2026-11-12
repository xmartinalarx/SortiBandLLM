# Imprimir el clasificador en la Creality Ender-3 V3 KE (boquilla 0,4 mm) · versión 2

> **Versión 2:** corrige el error **key:2111**. En la versión 1, la nivelación de la impresora dejaba la boquilla a ~150 °C y el archivo empezaba a extruir sin volver a 240 °C. Ahora cada archivo espera a que la boquilla y la cama lleguen a temperatura después de nivelar, y hace una línea de purga en el borde delantero antes de imprimir.
> **Borra del USB los archivos sin `_v2`.**

Estos archivos `.gcode` están listos para la **Ender-3 V3 KE** (pantalla táctil con Wi-Fi). Usan el código de inicio oficial de Creality (`START_PRINT` / `END_PRINT`), que calienta, nivela y purga solo.

> El manual de papel que hay junto a la impresora es de la **Ender-3 V2**, otra máquina. No lo sigas para esta impresora.
> La impresora **no imprime STL**: solo lee `.gcode`.

## Archivos

| Archivo | Qué imprime | Tiempo | Filamento |
|---|---|---|---|
| `00_prueba_tolerancia_v2.gcode` | Prueba de agujeros 1,9 / 2,0 / 2,1 mm | 10 min | 3 g |
| `01_eslabones_agujero_d20_v2.gcode` | 7 eslabones, agujero 2,0 mm | 5 h 25 min | 95 g |
| `01_eslabones_agujero_d19_v2.gcode` | 7 eslabones, agujero 1,9 mm | 5 h 25 min | 96 g |
| `01_eslabones_agujero_d21_v2.gcode` | 7 eslabones, agujero 2,1 mm | 5 h 25 min | 95 g |
| `02_paletas_A_B_v2.gcode` | 2 partes A + 2 partes B de las paletas (con brim) | 6 h 06 min | 133 g |
| `03_cama_v2.gcode` | 1 tramo de cama de deslizamiento | 1 h 57 min | 41 g |
| `04_soportes_servo_v2.gcode` | 2 soportes para servo MG996R | 3 h 24 min | 67 g |
| `05_pinones_v2.gcode` | 3 piñones | 4 h 10 min | 70 g |

Los tiempos son estimaciones del laminador y pueden variar ±20 %.

## Qué imprime cada integrante

| Integrante | Archivos (en orden) | Tiempo total |
|---|---|---|
| Persona 1 | `00` → `01` ×4 → `02` → `03` | ~30 h |
| Persona 2 | `00` → `01` ×4 → `04` → `03` ×2 | ~29 h |
| Persona 3 | `00` → `01` ×4 → `05` → `03` | ~28 h |
| Persona 4 | `00` → `01` ×4 → `05` → `03` | ~28 h |

Si los 4 usan esta misma impresora por turnos, el total es de unas 115 h (unos 5 días seguidos).

## Configuración usada

| Parámetro | Valor |
|---|---|
| Boquilla | 0,4 mm |
| Material | PETG blanco, 1,75 mm |
| Temperatura | boquilla 240 °C · cama 70 °C |
| Altura de capa | 0,2 mm |
| Perímetros | 3 |
| Relleno | 25 % gyroid |
| Capas superiores / inferiores | 5 / 4 |
| Soportes | No |
| Ventilador | 30–50 % (apagado en la primera capa) |
| Velocidad | perímetros 100 mm/s · externos 60 · relleno 150 · primera capa 35 |

## Paso a paso

### 1. Preparar el USB

1. Usa un pendrive en formato **FAT32**.
2. Copia los archivos `.gcode`. Los nombres ya vienen sin espacios ni tildes; no los cambies.

### 2. Preparar la impresora

1. Enciéndela y confirma el modelo en **Ajustes → Acerca de / Información**: debe decir Ender-3 V3 KE. Si dice otro modelo, no imprimas estos archivos.
2. Saca la placa magnética y límpiala con **alcohol isopropílico**. No la toques con los dedos donde se imprime.
3. Si la superficie de la placa es lisa, pon una capa fina de barra adhesiva: el PETG se pega demasiado a algunas placas y puede arrancarles material. En placas texturadas no hace falta.
4. Vuelve a poner la placa bien alineada con los bordes de la cama.

### 3. Cargar el PETG

1. En la pantalla, entra a **Control** (ícono de los deslizadores) y calienta la boquilla a **240 °C**.
2. Si hay otro filamento puesto, retíralo.
3. Corta la punta del PETG en diagonal y pásala por el sensor de filamento hasta el extrusor.
4. Extruye hasta que salga plástico blanco limpio, sin restos del color anterior.

### 4. Nivelar (solo la primera vez)

Ejecuta la **nivelación automática** desde el menú de ajustes. Después, `START_PRINT` vuelve a medir la cama antes de cada impresión.

### 5. Imprimir la prueba de tolerancia

1. Inserta el USB y entra a **Archivos** (ícono de carpeta) → USB → `00_prueba_tolerancia_v2.gcode` → **Imprimir**.
2. Observa la primera capa:
   - Si las líneas no se pegan o quedan redondas, baja el **Z offset** 0,05 mm desde la pantalla de impresión.
   - Si quedan muy aplastadas o la boquilla raspa, súbelo 0,05 mm.
3. Al terminar, espera a que la cama baje de **40 °C**, saca la placa y flecta para soltar la pieza.

### 6. Elegir el agujero

1. Mete un trozo de filamento de 1,75 mm en los tres agujeros (marcados con 1, 2 y 3 puntos).
2. Elige el más chico por el que el filamento entre con presión suave y gire:

| Agujero elegido | Archivo de eslabones |
|---|---|
| 1 punto (1,9 mm) | `01_eslabones_agujero_d19_v2.gcode` |
| 2 puntos (2,0 mm) | `01_eslabones_agujero_d20_v2.gcode` |
| 3 puntos (2,1 mm) | `01_eslabones_agujero_d21_v2.gcode` |

3. Antes de la tanda completa, une 2 o 3 eslabones de la primera placa y comprueba que las bisagras giran bien.

### 7. Imprimir tu paquete

Sigue el orden de la tabla de tu integrante. Entre impresiones:

- Espera a que la cama se enfríe antes de sacar las piezas.
- Limpia la placa con alcohol cada 2 o 3 impresiones.
- Revisa que quede filamento suficiente: cada placa de eslabones usa ~95 g.

## Problemas comunes

| Problema | Solución |
|---|---|
| Aparece **key:2111** | Estás usando un archivo antiguo: usa solo los que terminan en `_v2` |
| La primera capa no se pega | Limpia la placa con alcohol, baja el Z offset 0,05 mm o sube la cama a 75 °C |
| Muchos hilos entre piezas | El PETG tomó humedad: sécalo a 60 °C por al menos 8 horas |
| Las paletas se mueven o se despegan | Revisa que el brim quedó bien pegado; si persiste, baja la velocidad al 70 % desde la pantalla |
| La pieza se pegó demasiado | Espera a que la cama esté fría y flecta la placa; no uses espátulas metálicas |
| La boquilla raspa la pieza | Sube el Z offset 0,05 mm |

## Si quieres laminar tú mismo

- **Creality Print:** elige la impresora Ender-3 V3 KE, boquilla de 0,4 mm, PETG genérico y capa de 0,2 mm. Abre los STL de tu paquete, lamina y envía por Wi-Fi o exporta al USB.
- **PrusaSlicer:** carga el perfil `perfil_PrusaSlicer_Ender3V3KE_PETG_0.4.ini`.
