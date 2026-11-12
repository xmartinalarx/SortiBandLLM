// Clasificador de manzanas: banda de eslabones de 200 mm, piñones, cama, paletas desviadoras y soporte de servo.
// Unidades en mm. Exportar: openscad -D 'pieza="eslabon"' -o eslabon.stl banda_manzanas.scad
// Piezas: "eslabon", "placa", "pinon", "cama", "paleta_a", "paleta_b", "paleta", "soporte_servo", "prueba", "cadena3"

pieza = "eslabon";

// ---------- Banda ----------
paso      = 20;     // distancia entre pasadores
ancho     = 200;    // ancho de la banda
espesor   = 2;      // placa superior
r_bis     = 4;      // radio de bisagra (Ø 8)
z_eje     = 4;      // eje del pasador: bisagra a ras de la cara superior
d_agujero = 2.0;    // para filamento de 1,75 mm (1.9 / 2.0 / 2.1 según la prueba)
holgura   = 0.4;
ancho_bis = 12;     // largo de cada bisagra en el ancho
// Centros de bisagras: delanteras (x = paso) y traseras (x = 0), alternadas en el ancho
centros_del = [6, 52, 100, 148, 194];
centros_tra = [29, 76, 124, 171];

// ---------- Piñón ----------
dientes   = 10;
ancho_pin = 14;     // se usan 3 por eje, en y = 29, 100 y 171
d_eje     = 8.2;
d_prision = 2.8;    // prisionero M3 autorroscante

// ---------- Cama de deslizamiento (escalera) ----------
largo_cama = 180;
rieles_y   = [6, 52, 100, 148, 194];   // bajo las bisagras delanteras
alto_cama  = 3;

// ---------- Paleta desviadora ----------
largo_paleta = 300;   // desde el pivote hasta la punta (cruza 200 mm a 45° con el pivote 12 mm fuera del borde)
alto_paleta  = 46;    // queda a 2 mm de la banda
esp_paleta   = 4;
corte        = 150;   // la paleta se imprime en 2 partes
traslape     = 25;

// ---------- Servo MG996R ----------
servo_l = 40.7; servo_w = 19.7;
servo_aguj_x = 49.5; servo_aguj_y = 10;   // agujeros de las orejas
servo_eje = 10.2;                           // eje de salida desde un extremo del cuerpo

$fn = 48;

module cil_y(x, y0, y1, r, z = z_eje) {
    translate([x, y0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = y1 - y0);
}

// ================= ESLABÓN =================
// Se imprime con la cara de transporte (z = 0) sobre la cama de la impresora.
module eslabon() {
    union_tab = r_bis + holgura + 0.3;
    difference() {
        union() {
            difference() {
                cube([paso, ancho, espesor]);
                for (x = [0, paso]) cil_y(x, -1, ancho + 1, r_bis + holgura);
            }
            for (c = centros_tra) {
                cil_y(0, c - ancho_bis / 2, c + ancho_bis / 2, r_bis);
                translate([0, c - ancho_bis / 2, 0]) cube([union_tab, ancho_bis, espesor]);
            }
            for (c = centros_del) {
                y0 = max(0, c - ancho_bis / 2); y1 = min(ancho, c + ancho_bis / 2);
                cil_y(paso, y0, y1, r_bis);
                translate([paso - union_tab, y0, 0]) cube([union_tab, y1 - y0, espesor]);
            }
        }
        for (x = [0, paso]) cil_y(x, -1, ancho + 1, d_agujero / 2);
    }
}

// 7 eslabones por placa (caben en una cama de 220 x 220 mm)
module placa() { for (i = [0 : 6]) translate([r_bis + 2 + i * 30, 10, 0]) eslabon(); }

module cadena3() {
    for (i = [0 : 2]) translate([i * paso, 0, 0]) eslabon();
    for (i = [0 : 3]) cil_y(i * paso, 0, ancho, 1.75 / 2);
}

// ================= PIÑÓN =================
r_paso   = paso / (2 * sin(180 / dientes));                 // ~32,4 mm
r_ranura = r_bis + 0.25;
r_ext    = r_paso * cos(180 / dientes) + (z_eje - espesor) - 0.5;

module pinon() {
    difference() {
        cylinder(r = r_ext, h = ancho_pin, $fn = 160);
        for (k = [0 : dientes - 1]) rotate([0, 0, k * 360 / dientes]) {
            translate([r_paso, 0, -1]) cylinder(r = r_ranura, h = ancho_pin + 2);
            translate([r_paso + 2, 0, -1]) cylinder(r = r_ranura + 0.7, h = ancho_pin + 2);
        }
        translate([0, 0, -1]) cylinder(d = d_eje, h = ancho_pin + 2);
        translate([0, 0, -0.01]) cylinder(d1 = d_eje + 1.6, d2 = d_eje, h = 0.8);
        translate([0, 0, ancho_pin - 0.79]) cylinder(d1 = d_eje, d2 = d_eje + 1.6, h = 0.8);
        translate([0, 0, ancho_pin / 2]) rotate([0, 90, 0]) cylinder(d = d_prision, h = r_paso + 2);
        // aligerado
        for (k = [0 : 4]) rotate([0, 0, 36 + k * 72])
            translate([17, 0, -1]) cylinder(d = 11, h = ancho_pin + 2);
    }
}

// ================= CAMA (escalera) =================
module cama() {
    difference() {
        union() {
            for (y = rieles_y) translate([0, y - 5, 0]) cube([largo_cama, 10, alto_cama]);
            for (x = [0, (largo_cama - 10) / 2, largo_cama - 10]) translate([x, 1, 0]) cube([10, ancho - 2, alto_cama]);
        }
        // M3 para fijarla al bastidor (entre rieles)
        for (x = [5, largo_cama - 5], y = [29, 171]) translate([x, y, -1]) cylinder(d = 3.4, h = alto_cama + 2);
        // chaflán de entrada en los extremos de los rieles
        for (x = [0, largo_cama]) translate([x, -1, alto_cama]) rotate([-90, 0, 0])
            cylinder(r = 1.5, h = ancho + 2, $fn = 4);
    }
}

// ================= PALETA =================
// Pivote en el origen. La paleta corre por +X. Se muestra en posición de uso: z = 0 abajo (2 mm sobre la banda).
// El cubo superior lleva el bolsillo para el brazo doble del servo y el acceso al tornillo central.
module paleta_completa() {
    difference() {
        union() {
            translate([-27, -esp_paleta / 2, 0]) cube([largo_paleta + 27 - 8, esp_paleta, alto_paleta]);
            translate([largo_paleta - 8, 0, 0]) cylinder(r = esp_paleta / 2, h = alto_paleta);   // punta redondeada
            hull() for (x = [-19, 19]) translate([x, 0, alto_paleta - 6]) cylinder(d = 16, h = 6);
            // nervio inferior para rigidez
            translate([20, -esp_paleta, 0]) cube([largo_paleta - 40, esp_paleta * 2, 4]);
        }
        translate([-24, -5.25, alto_paleta - 4.5]) cube([48, 10.5, 5]);   // brazo doble del servo
        translate([0, 0, -1]) cylinder(d = 6.5, h = alto_paleta + 2);    // acceso al tornillo del eje
        for (x = [-15, 15]) translate([x, 0, alto_paleta - 14]) cylinder(d = 1.8, h = 15);  // M2 autorroscante
    }
}

module agujeros_union() {
    for (z = [13, 33]) translate([corte + traslape / 2, -10, z]) rotate([-90, 0, 0]) cylinder(d = 3.3, h = 20);
}

module paleta_a() {
    difference() {
        intersection() {
            paleta_completa();
            union() {
                translate([-40, -20, -1]) cube([corte + 40, 40, 80]);
                translate([corte, 0, -1]) cube([traslape, 20, 80]);   // medio traslape
            }
        }
        agujeros_union();
    }
}

module paleta_b() {
    difference() {
        intersection() {
            paleta_completa();
            union() {
                translate([corte + traslape, -20, -1]) cube([largo_paleta, 40, 80]);
                translate([corte, -20, -1]) cube([traslape, 20, 80]);
            }
        }
        agujeros_union();
    }
}

// Orientación para imprimir: canto superior sobre la cama, sin soportes
module imprimir_paleta(parte) {
    translate([0, 0, alto_paleta]) rotate([180, 0, 0]) if (parte == "a") paleta_a(); else paleta_b();
}

// ================= SOPORTE DEL SERVO =================
// El servo va invertido (eje hacia abajo) sobre la paleta. La placa sostiene las orejas
// y la pata baja hasta el bastidor, con ranuras para ajustar la altura.
module soporte_servo() {
    placa_x = 70; placa_y = 40; e = 5;
    difference() {
        union() {
            translate([-placa_x / 2, -placa_y / 2, 0]) cube([placa_x, placa_y, e]);
            translate([-placa_x / 2, -placa_y / 2 - e, -80]) cube([placa_x, e, 80 + e]);     // pata
            for (x = [-placa_x / 2, placa_x / 2 - e])                                         // escuadras
                hull() {
                    translate([x, -placa_y / 2 - e, -30]) cube([e, e, 30 + e]);
                    translate([x, -placa_y / 2 - e, 0]) cube([e, 25, e]);
                }
        }
        translate([-(servo_l + 0.6) / 2, -(servo_w + 0.6) / 2, -1]) cube([servo_l + 0.6, servo_w + 0.6, e + 2]);
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * servo_aguj_x / 2, sy * servo_aguj_y / 2, -1]) cylinder(d = 3.2, h = e + 2);
        for (x = [-18, 18]) hull() for (z = [-70, -45])                                       // ranuras M4
            translate([x, -placa_y / 2 + 1, z]) rotate([90, 0, 0]) cylinder(d = 4.4, h = e + 2);
    }
}

// ================= PRUEBA DE TOLERANCIA =================
module prueba() {
    medidas = [1.9, 2.0, 2.1];
    difference() {
        cube([36, 12, 8]);
        for (i = [0 : 2]) cil_y(6 + i * 12, -1, 13, medidas[i] / 2, 4);
    }
    for (i = [0 : 2], k = [0 : i]) translate([6 + i * 12 - 3 + k * 2.2, 1, 8]) cube([1.2, 1.2, 0.8]);
}

if (pieza == "eslabon") eslabon();
else if (pieza == "placa") placa();
else if (pieza == "pinon") pinon();
else if (pieza == "cama") cama();
else if (pieza == "paleta_a") imprimir_paleta("a");
else if (pieza == "paleta_b") imprimir_paleta("b");
else if (pieza == "paleta") paleta_completa();
else if (pieza == "soporte_servo") soporte_servo();
else if (pieza == "prueba") prueba();
else if (pieza == "cadena3") cadena3();
