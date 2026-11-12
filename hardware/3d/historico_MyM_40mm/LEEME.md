# Banda transportadora impresa en 3D

Banda de eslabones de 10 mm de paso y 40 mm de ancho, unidos con filamento de 1,75 mm como pasador. Los piñones empujan la banda por sus bisagras, como una cadena, así que no patina.

Todas las piezas se probaron en simulación: los eslabones no chocan entre sí (en recta ni doblados hasta 50°) y calzan en el piñón sin interferir.

## Archivos

| Archivo | Imprimir | Para qué |
|---|---|---|
| `stl/1_prueba_tolerancia.stl` | 1 | Elegir el diámetro de agujero correcto (imprimir primero) |
| `stl/2_eslabon_agujero_2.0.stl` | 3 de prueba | Un eslabón suelto |
| `stl/3_placa_40_eslabones_agujero_2.0.stl` | 3 placas | 120 eslabones listos para imprimir (se usan 110) |
| `stl/4_pinon_imprimir_2.stl` | 2 | Piñón motriz y piñón tensor (son iguales) |
| `stl/5_cama_deslizamiento_imprimir_3.stl` | 3 | Soporte bajo el tramo superior de la banda |
| `stl/variantes/` | — | Eslabón y placa con agujero de 1,9 o 2,1 mm |
| `banda_eslabones.scad` | — | Modelo editable en OpenSCAD (todas las medidas son parámetros) |

## Paso 1: prueba de tolerancia

1. Imprime `1_prueba_tolerancia.stl`. Tiene tres agujeros de 1,9 / 2,0 / 2,1 mm, marcados con 1, 2 y 3 puntos.
2. Mete filamento de 1,75 mm en cada agujero.
3. Elige el más chico por el que el filamento entre con presión suave y gire sin trabarse.
4. Si es el de 2,0 mm, usa los archivos principales. Si es otro, usa los de `variantes/`.

## Paso 2: imprimir

- **Material:** PETG (se quiebra menos que el PLA en las bisagras). Color blanco o gris claro mate.
- **Capa:** 0,2 mm · **Paredes:** 4 · **Relleno:** 40 % (eslabones) y 30 % (piñones y cama).
- **Soportes:** no hacen falta.
- **Orientación:** los STL ya vienen orientados. Los eslabones se imprimen con la cara de transporte apoyada en la cama; así queda lisa. Los piñones, de pie.
- **Filamento total:** unos 300 g.

Antes de imprimir las 3 placas, imprime 3 eslabones sueltos y únelos para comprobar que las bisagras giran bien.

## Paso 3: armar la banda

1. Pon los eslabones en fila con las bisagras hacia arriba, intercalando las bisagras de uno con las del siguiente.
2. Pasa un trozo de filamento de unos 42 mm por las bisagras y córtalo a ras con un alicate de corte.
3. Si un pasador queda suelto, derrite la punta con un cautín o un lápiz 3D, o pon una gota de pegamento.
4. Une **110 eslabones** en un circuito cerrado (unos 1.100 mm). Se usan unos 4,6 m de filamento para los pasadores.

## Paso 4: montar

- La distancia entre los ejes de los piñones es de **500 mm** (50 eslabones por tramo recto). El piñón tensor debe ir en una ranura que se desliza ±10 mm para tensar la banda.
- Los piñones van en ejes de acero de 8 mm, que giran en rodamientos 608 montados en los laterales. Cada piñón se fija al eje con un tornillo prisionero M3 (autorroscante en el agujero radial).
- El motor NEMA 17 se une al eje del piñón motriz con un acople de 5 a 8 mm.
- Los 3 tramos de cama de deslizamiento van uno tras otro bajo el tramo superior, atornillados a los laterales con M3. Sus extremos tienen chaflán para que las bisagras entren suaves.
- La banda va con las bisagras hacia abajo (hacia los piñones) y la cara lisa hacia arriba.

Los laterales y soportes del bastidor todavía no están en este paquete.

## Medidas principales

| Parámetro | Valor |
|---|---|
| Paso | 10 mm |
| Ancho | 40 mm |
| Espesor de la placa | 2 mm |
| Bisagras | Ø 6 mm (alto total del eslabón 6 mm) |
| Piñón | 10 dientes, diámetro primitivo 32,4 mm, exterior 31,1 mm, 40 mm de largo, eje 8 mm |
| Cama de deslizamiento | 150 × 36 × 3 mm |

Para cambiar cualquier medida, abre `banda_eslabones.scad` en OpenSCAD (gratis), edita los parámetros del inicio, presiona F6 y exporta el STL.
