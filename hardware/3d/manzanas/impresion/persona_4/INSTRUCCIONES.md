# Persona 4: banda, piñones del eje motriz y cama

Total: **7 impresiones · 38 h 11 min · ~493 g de PETG**. Con 2 impresiones al día (una de día y una de noche) terminas en 3 días y te queda 1 de margen.

## Qué imprimir

| Archivo | Veces | Tiempo c/u | Filamento c/u | Qué es |
|---|---|---|---|---|
| `00_prueba_tolerancia.stl` | 1 | 0 h 15 min | 4 g | Prueba de agujeros 1,9 / 2,0 / 2,1 mm |
| `01_eslabones_7_x4.stl` | 4 | 7 h 23 min | 95 g | 7 eslabones por placa (28 en total) |
| `02_pinones_x1.stl` | 1 | 5 h 41 min | 69 g | 3 piñones (eje motriz) |
| `03_cama_x1.stl` | 1 | 2 h 42 min | 42 g | 1 tramo de cama de deslizamiento |

Los tiempos son estimaciones de PrusaSlicer para una impresora tipo Ender-3 con el perfil incluido. En tu laminador pueden variar ±20 %.

## Plan por día

| Día | Impresiones |
|---|---|
| Día 1 | Prueba de tolerancia y luego eslabones #1 (día) · eslabones #2 (noche) |
| Día 2 | Piñones (día) · eslabones #3 (noche) |
| Día 3 | Cama (día) · eslabones #4 (noche) |
| Día 4 | Margen para reimprimir fallas y armar su tramo de banda |

## Configuración (todas las piezas)

| Parámetro | Valor |
|---|---|
| Material | PETG blanco, 1,75 mm |
| Temperatura | boquilla 240 °C · cama 80 °C |
| Altura de capa | 0,28 mm (si falla, usa 0,2 mm: tarda ~35 % más) |
| Perímetros | 3 |
| Relleno | 25 % gyroid |
| Capas superiores / inferiores | 4 / 3 |
| Soportes | No |
| Velocidad | perímetros 55 mm/s · externos 35 · relleno 80 |

Si usas PrusaSlicer, carga `perfil_PETG_PrusaSlicer.ini`. En Cura o Creality Print, copia los valores de la tabla. Las piezas ya vienen orientadas y centradas: no las gires.

## Paso 1: la prueba de tolerancia (obligatoria)

Cada impresora queda un poco distinta, así que **cada integrante** imprime su propia prueba, con este mismo perfil, antes de los eslabones.

1. Mete filamento de 1,75 mm en los tres agujeros (marcados con 1, 2 y 3 puntos).
2. Elige el más chico por el que el filamento entre con presión suave y gire.
3. 2 puntos (2,0 mm): usa `01_eslabones_7_x4.stl`. 1 punto (1,9 mm) o 3 puntos (2,1 mm): usa el archivo de `variantes/`.

## Al terminar

Arma tu tramo de **28 eslabones** con pasadores de filamento de 202 mm (corta a ras), con las bisagras hacia abajo. Al juntar los 4 tramos quedan 112 eslabones: la banda usa 110 y sobran 2 de repuesto.
