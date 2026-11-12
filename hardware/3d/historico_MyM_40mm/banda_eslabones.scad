// Banda transportadora impresa en 3D: eslabones, piñones, cama de deslizamiento y prueba de tolerancia.
// Proyecto ClasificadorIoT. Unidades en mm.
// Para exportar una pieza: cambia "pieza" y usa F6 + Exportar STL,
// o por consola: openscad -D 'pieza="eslabon"' -o eslabon.stl banda_eslabones.scad

pieza = "eslabon"; // "eslabon", "placa", "pinon", "cama", "prueba", "cadena3"

// ---------- Parámetros principales ----------
paso       = 10;    // distancia entre pasadores
ancho      = 40;    // ancho de la banda
espesor    = 2;     // espesor de la placa superior
r_bisagra  = 3;     // radio de cada bisagra (diámetro 6)
z_eje      = 3;     // altura del eje del pasador (bisagra a ras de la cara superior)
d_agujero  = 2.0;   // agujero para filamento de 1,75 mm (ajustar con la prueba: 1.9 / 2.0 / 2.1)
holgura    = 0.4;   // holgura entre piezas móviles
separacion = 0.6;   // separación entre bisagras vecinas en el ancho

// Zonas de bisagras en el ancho (eje Y)
zonas_delanteras = [[0, 8], [32, 40]];                                   // en x = paso
zonas_traseras   = [[8 + separacion, 16 - separacion], [24 + separacion, 32 - separacion]]; // en x = 0

// Piñón
dientes    = 10;
d_eje      = 8.2;   // eje de 8 mm (impreso queda algo más chico)
d_tornillo = 2.8;   // tornillo prisionero M3 autorroscante

// Cama de deslizamiento
largo_cama = 150;
ancho_cama = 36;

$fn = 48;

// ---------- Utilidades ----------
module cilindro_y(x, y0, y1, r, z = z_eje) {
    translate([x, y0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = y1 - y0);
}

// ---------- Eslabón ----------
// Se imprime con la cara de transporte (z = 0) apoyada en la cama de la impresora.
module eslabon() {
    difference() {
        union() {
            // Placa central con holgura alrededor de ambos pasadores
            difference() {
                cube([paso, ancho, espesor]);
                for (x = [0, paso]) cilindro_y(x, -1, ancho + 1, r_bisagra + holgura);
            }
            // Bisagras traseras (x = 0) con su unión a la placa
            for (zn = zonas_traseras) {
                cilindro_y(0, zn[0], zn[1], r_bisagra);
                translate([0, zn[0], 0]) cube([r_bisagra + holgura + 0.2, zn[1] - zn[0], espesor]);
            }
            // Bisagras delanteras (x = paso) con su unión a la placa
            for (zn = zonas_delanteras) {
                cilindro_y(paso, zn[0], zn[1], r_bisagra);
                translate([paso - (r_bisagra + holgura + 0.2), zn[0], 0])
                    cube([r_bisagra + holgura + 0.2, zn[1] - zn[0], espesor]);
            }
        }
        // Agujeros de los pasadores
        for (x = [0, paso]) cilindro_y(x, -1, ancho + 1, d_agujero / 2, z_eje);
    }
}

// Placa de impresión: 4 columnas x 10 filas = 40 eslabones (cabe en 220 x 220 mm)
module placa() {
    for (i = [0 : 9], j = [0 : 3])
        translate([r_bisagra + 2 + i * 18, 2 + j * 44, 0]) eslabon();
}

// Tres eslabones encadenados (solo para visualizar el armado)
module cadena3() {
    for (i = [0 : 2]) translate([i * paso, 0, 0]) eslabon();
    color("orangered") for (i = [0 : 3]) cilindro_y(i * paso, 0, ancho, 1.75 / 2);
}

// ---------- Piñón ----------
// Las bisagras de la banda calzan en las ranuras como rodillos de una cadena.
r_paso   = paso / (2 * sin(180 / dientes));        // radio primitivo (~16,2 mm)
r_ranura = r_bisagra + 0.25;
r_ext    = r_paso * cos(180 / dientes) + (z_eje - espesor) - 0.5; // no toca la placa entre pasadores

module pinon() {
    difference() {
        cylinder(r = r_ext, h = ancho, $fn = 120);
        for (k = [0 : dientes - 1]) rotate([0, 0, k * 360 / dientes]) {
            translate([r_paso, 0, -1]) cylinder(r = r_ranura, h = ancho + 2);
            translate([r_paso + 1.6, 0, -1]) cylinder(r = r_ranura + 0.6, h = ancho + 2); // entrada suave
        }
        // Eje de 8 mm con chaflanes
        translate([0, 0, -1]) cylinder(d = d_eje, h = ancho + 2);
        translate([0, 0, -0.01]) cylinder(d1 = d_eje + 1.6, d2 = d_eje, h = 0.8);
        translate([0, 0, ancho - 0.79]) cylinder(d1 = d_eje, d2 = d_eje + 1.6, h = 0.8);
        // Tornillo prisionero M3 radial (entra por el fondo de una ranura)
        translate([0, 0, 6]) rotate([0, 90, 0]) cylinder(d = d_tornillo, h = r_paso + 2);
    }
}

// ---------- Cama de deslizamiento ----------
// Va bajo el tramo superior para que la banda no se combe. Se usan 3 tramos.
module cama() {
    difference() {
        hull() {
            cube([largo_cama, ancho_cama, 2]);
            translate([2, 0, 0]) cube([largo_cama - 4, ancho_cama, 3]);
        }
        for (x = [8, largo_cama - 8], y = [6, ancho_cama - 6])
            translate([x, y, -1]) cylinder(d = 3.4, h = 5);
    }
}

// ---------- Prueba de tolerancia ----------
// Tres agujeros de 1,9 / 2,0 / 2,1 mm (marcados con 1, 2 y 3 puntos).
// Elige el más chico por el que el filamento pase con presión suave y gire.
module prueba() {
    medidas = [1.9, 2.0, 2.1];
    difference() {
        cube([36, 10, 6]);
        for (i = [0 : 2]) cilindro_y(6 + i * 12, -1, 11, medidas[i] / 2, 3);
    }
    for (i = [0 : 2], k = [0 : i])
        translate([6 + i * 12 - 3 + k * 2.2, 1, 6]) cube([1.2, 1.2, 0.8]);
}

// ---------- Selección ----------
if (pieza == "eslabon") eslabon();
else if (pieza == "placa") placa();
else if (pieza == "pinon") pinon();
else if (pieza == "cama") cama();
else if (pieza == "prueba") prueba();
else if (pieza == "cadena3") cadena3();
