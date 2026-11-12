# Clasificador de manzanas: banda de 200 mm × 1.000 mm entre ejes

Versión para manzanas de 7 a 8,5 cm y 150 a 250 g. La banda es de eslabones impresos de 20 mm de paso, unidos con filamento de 1,75 mm, y la mueven 3 piñones por eje. Dos paletas de 300 mm, cada una con un servo MG996R, desvían las manzanas a las salidas laterales.

## Contenido

| Carpeta o archivo | Qué es |
|---|---|
| `gcode_Ender3V3KE_0.4_v2/` | G-code listos para la Ender-3 V3 KE del laboratorio, con guía paso a paso |
| `stl/piezas/` y `stl/placas/` | Piezas sueltas y placas armadas para cama de 220 × 220 mm |
| `imagenes/` | Renders y diagrama de armado de eslabones |
| `impresion/REPARTO.md` | Reparto de todas las piezas entre los 4 integrantes |
| `impresion/persona_1` a `persona_4` | STL listos para imprimir, perfil del laminador e instrucciones de cada uno |
| `blender/` | Escena armada (`.blend` y `.glb`), renders y script que la genera |
| `banda_manzanas.scad` | Modelo paramétrico en OpenSCAD de todas las piezas |

## Medidas generales

| Elemento | Medida |
|---|---|
| Banda armada | 1.070 × 200 × 73 mm (largo × ancho × alto) |
| Distancia entre ejes | 1.000 mm (50 eslabones por tramo recto, 110 en total) |
| Conjunto con paletas, servos y motor | ~1.080 × 330 × 170 mm |
| Superficie de transporte sobre el centro del eje | 36 mm |

## Distribución a lo largo de la banda

Medido desde el eje del piñón tensor (x = 0), en el sentido de avance.

| Zona | Posición |
|---|---|
| Carga de manzanas | 0 a 150 mm |
| Sensor IR | ~170 mm |
| Túnel de cámara (volumen reservado) | 200 a 360 mm; 260 de ancho × 220 de alto |
| Paleta 1: pivote en el lado izquierdo | x = 450; manda a la salida derecha (~560 a 670 mm) |
| Paleta 2: pivote en el lado derecho | x = 750; manda a la salida izquierda (~860 a 960 mm) |
| Salida 3: fin de la banda | después de 1.000 mm |

## Tiempos de reacción a 30 mm/s (motor 28BYJ-48)

| Tramo | Distancia | Tiempo disponible |
|---|---|---|
| Cámara → paleta 1 cerrada | 227 mm | 7,6 s |
| Cámara → paleta 2 cerrada | 527 mm | 17,6 s |

La clasificación, el mensaje MQTT y el giro del servo suman ~0,4 s. Lo que limita la capacidad es la separación entre manzanas: una manzana desviada tarda ~9,3 s en salir por la paleta, así que la siguiente debe venir al menos ~310 mm atrás (unas 6 manzanas por minuto). Detalle y firmware: `CLAUDE.md` en la raíz del proyecto.

## Piezas del sistema completo

| Pieza | Cantidad | Medidas |
|---|---|---|
| Eslabón (en placas de 7) | 112 (110 + 2 de repuesto) | 28 × 200 × 8 mm |
| Piñón | 6 (3 por eje) | Ø 64 × 14 mm, 10 dientes |
| Tramo de cama de deslizamiento | 5 | 180 × 198 × 3 mm |
| Paleta, parte A y parte B | 2 de cada una | 202 × 16 × 46 mm y 144 × 8 × 46 mm |
| Soporte de servo MG996R | 2 | 70 × 45 × 85 mm |
| Prueba de tolerancia | 1 por integrante | 36 × 12 × 9 mm |

Filamento total: ~2,1 kg de PETG, más ~70 g para los pasadores (PLA+ de 1,75 mm). Tiempo total en la Ender-3 V3 KE del laboratorio: ~115 h, ~28–30 h por integrante (el cálculo inicial con otro perfil daba ~157 h).

## Compras adicionales

| Material | Cantidad |
|---|---|
| Servo MG996R (9 a 11 kg·cm) | 2 |
| Eje de acero de 8 mm × 260 mm | 2 |
| Rodamiento 608 | 4 |
| Acople flexible de 5 a 8 mm | 1 |
| Motor 28BYJ-48 (5 V) + placa ULN2003 | 1 |
| Tornillos M3 × 16 con tuerca | ~30 |
| Tornillos M4 | 4 |
| Cargador de celular 5 V (≥ 2 A) para los servos y el motor | 1 |

## Armado

1. Cada integrante arma su tramo de 28 eslabones; luego se unen los 4 tramos y se cierra la banda con 110 eslabones.
2. Los piñones van en los ejes a 29, 100 y 171 mm desde un borde de la banda, fijados con prisioneros M3.
3. Los 5 tramos de cama van uno tras otro entre x = 50 y x = 950.
4. Las partes A y B de cada paleta se unen por el traslape con 2 tornillos M3. El brazo doble del servo calza en el bolsillo del cubo.
5. Los servos van invertidos en su soporte, con el cuerpo aguas abajo del pivote y la paleta a 2 mm de la banda.

## Pendiente

El bastidor (laterales con rodamientos, tensor y patas), el túnel de cámara, las rampas de salida y las barandas laterales.
