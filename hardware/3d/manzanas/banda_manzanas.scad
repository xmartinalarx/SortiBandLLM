// Clasificador de manzanas: banda de eslabones de 200 mm, piñones, cama, paletas desviadoras y soporte de servo.
// Unidades en mm. Exportar: openscad -D 'pieza="eslabon"' -o eslabon.stl banda_manzanas.scad
// Piezas: "eslabon", "placa", "pinon", "cama", "paleta_a", "paleta_b", "paleta", "soporte_servo", "prueba", "cadena3"
// Piezas para la base de madera: "portarod_motriz", "portarod_tensor", "soporte_motor", "soporte_ir",
//   "baranda_carga_d", "baranda_carga_i", "baranda_ir_d", "baranda_ir_i", "baranda_final_d", "baranda_final_i",
//   "rampa", "soporte_rampa_lateral", "soporte_rampa_final"

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

// =====================================================================================
// PIEZAS PARA LA BASE DE MADERA (2026-11-16)
// Referencias del montaje (mm): centro de los ejes en z = 0; banda centrada en y = 0;
// eje tensor en x = 0 y motriz en x = 1000. Base de madera: cara de arriba en z = -70.
// Laterales de 112 x 9,4 x 1,8 cm: caras interiores en y = ±105, exteriores en ±123, borde de arriba en z = +24.
// =====================================================================================
z_sup    = r_paso + z_eje;   // superficie de la banda sobre el eje (~36,4)
lat_top  = 24;               // borde de arriba de los laterales
lat_in   = 105;              // cara interior del lateral
lat_g    = 18;               // grosor de la madera
d_608    = 22.3;             // rodamiento 608 (22 x 8 x 7) a presión
h_608    = 7.3;
d_torn   = 4.2;              // tornillo para madera de 4 mm (o M4)

// ---------- PORTA-RODAMIENTO 608 ----------
// Se atornilla por FUERA del lateral, centrado en el agujero (motriz) o en la ranura (tensor).
// El rodamiento queda atrapado entre la pieza y la madera. El del eje tensor tiene ranuras
// de ±10 mm para correr el eje y tensar la banda. Se imprime con la cara exterior abajo.
module porta_rodamiento(tensor = false) {
    L = tensor ? 70 : 50; H = 58; E = 12;   // z del montaje: de -34 a +24 (no sobresale del lateral)
    sx = tensor ? 25 : 18;
    difference() {
        translate([-L / 2, -34, 0]) cube([L, H, E]);
        translate([0, 0, E - h_608]) cylinder(d = d_608, h = h_608 + 1);            // rodamiento (cara hacia la madera)
        translate([0, 0, -1]) cylinder(d = 12, h = E + 2);                          // paso del eje
        for (zz = [-26, 16], s = [-1, 1]) {
            if (tensor) hull() for (dx = [-10, 10]) translate([s * sx + dx, zz, -1]) cylinder(d = d_torn, h = E + 2);
            else translate([s * sx, zz, -1]) cylinder(d = d_torn, h = E + 2);
            if (tensor) hull() for (dx = [-10, 10]) translate([s * sx + dx, zz, -0.01]) cylinder(d1 = 8.6, d2 = d_torn, h = 2.2);
            else translate([s * sx, zz, -0.01]) cylinder(d1 = 8.6, d2 = d_torn, h = 2.2);
        }
    }
}

// ---------- SOPORTE DEL MOTOR 28BYJ-48 ----------
// Coordenadas propias: cara de arriba de la base en z = 0, eje del motor en z = 70 (igual que los ejes).
// Placa vertical: las orejas del motor se atornillan por delante (lado del acople, y < 0) y el cuerpo
// pasa por el agujero hacia atrás. El eje del 28BYJ-48 está 8 mm sobre el centro del cuerpo.
// El pie va hacia el lateral, con ranuras de ±6 mm para alinear el motor con el acople.
m_eje = 70; m_cuerpo = m_eje - 8; m_orejas = 35;
module soporte_motor() {
    difference() {
        union() {
            translate([-25, 0, 0]) cube([50, 5, m_eje + 12]);                        // placa
            translate([-25, -28, 0]) cube([50, 33, 5]);                             // pie
            for (x = [-25, 21]) hull() {                                            // escuadras
                translate([x, 0, 5]) cube([4, 1, 32]);
                translate([x, -26, 5]) cube([4, 1, 1]);
            }
        }
        translate([0, -1, m_cuerpo]) rotate([-90, 0, 0]) cylinder(d = 29, h = 7, $fn = 96);   // cuerpo
        translate([-9, -1, m_cuerpo - 26]) cube([18, 7, 26]);                                // caja de cables
        for (s = [-1, 1]) translate([s * m_orejas / 2, -1, m_cuerpo]) rotate([-90, 0, 0]) cylinder(d = d_torn, h = 7);
        for (s = [-1, 1]) hull() for (y = [-22, -10]) translate([s * 15, y, -1]) cylinder(d = d_torn, h = 7);
    }
}
module imprimir_soporte_motor() { rotate([-90, 0, 0]) translate([0, -5, 0]) soporte_motor(); }

// ---------- SOPORTE DEL SENSOR IR ----------
// Uno a cada lado (emisor y receptor), sobre el borde de arriba del lateral en x = 170.
// Coordenadas propias: borde del lateral en z = 0, cara interior en y = 0 (la madera va de y = 0 a 18).
// Supuesto: emisor y receptor de 5 mm (LED IR + fototransistor). Si el sensor es otro, cambiar d_ir.
d_ir = 5;
z_haz = 56 - lat_top;   // el haz cruza a 56 mm sobre el eje (~20 mm sobre la banda, a media manzana)
module soporte_ir() {
    difference() {
        union() {
            translate([-15, 0, 0]) cube([30, lat_g, 4]);
            translate([-7, 0, 0]) cube([14, 10, z_haz + 10]);
        }
        translate([0, -1, z_haz]) rotate([-90, 0, 0]) cylinder(d = d_ir + 0.2, h = 12);       // sensor
        translate([0, 8.5, z_haz]) rotate([-90, 0, 0]) cylinder(d = d_ir + 1.4, h = 2);       // pestaña del LED
        translate([-2, 7.5, 4]) cube([4, 3, z_haz - 4]);                                       // canal de cables
        for (s = [-1, 1]) {
            translate([s * 10.5, lat_g / 2 + 2, -1]) cylinder(d = 3.8, h = 6);
            translate([s * 10.5, lat_g / 2 + 2, 2.2]) cylinder(d1 = 3.8, d2 = 7.6, h = 1.9);
        }
    }
}

// ---------- BARANDAS Y GUÍA DE CARGA ----------
// Mantienen las manzanas centradas y en fila desde la carga (x = 0) hasta antes de la paleta 1 (x = 430).
// Pared colgada 2 mm sobre la banda, sostenida por brazos desde postes atornillados al borde del lateral.
// La guía de carga (embudo) estrecha el paso de 184 a 100 mm. Hay piezas derechas (+y) e izquierdas (-y).
canal   = 100;            // paso libre entre barandas (manzanas de 70-85 mm)
bar_bot = z_sup + 2;      // la pared no toca la banda
bar_top = 72;
esp_bar = 3;
function y_embudo(x) = 92 + (canal / 2 - 92) * x / 150;

module poste_baranda(x) {
    difference() {
        translate([x - 5, lat_in, lat_top]) cube([10, lat_g, bar_top - lat_top]);
        translate([x, lat_in + lat_g / 2, lat_top - 1]) cylinder(d = 3.8, h = bar_top);
        translate([x, lat_in + lat_g / 2, lat_top + 10]) cylinder(d = 8, h = bar_top);
    }
}
module brazo_baranda(x, yw) { translate([x - 5, yw, bar_top - 4]) cube([10, lat_in + lat_g - yw, 4]); }

module baranda_seg(tipo) {
    if (tipo == "carga") {
        hull() for (x = [0, 150]) translate([x, y_embudo(x) + esp_bar / 2, bar_bot]) cylinder(d = esp_bar, h = bar_top - bar_bot);
        for (x = [10, 140]) { poste_baranda(x); brazo_baranda(x, y_embudo(x)); }
    } else if (tipo == "ir") {
        difference() {
            translate([150, canal / 2, bar_bot]) cube([150, esp_bar, bar_top - bar_bot]);
            translate([170, canal / 2 - 1, 56]) rotate([-90, 0, 0]) cylinder(d = 8, h = esp_bar + 2);   // paso del haz IR
        }
        for (x = [205, 290]) { poste_baranda(x); brazo_baranda(x, canal / 2); }
    } else {
        translate([300, canal / 2, bar_bot]) cube([130, esp_bar, bar_top - bar_bot]);
        for (x = [310, 420]) { poste_baranda(x); brazo_baranda(x, canal / 2); }
    }
}
// lado: 1 = derecha (+y), -1 = izquierda (-y). Se imprime boca abajo (cara de arriba sobre la cama, sin soportes).
module baranda_impresa_derecha(tipo) {
    x0 = tipo == "carga" ? 0 : tipo == "ir" ? 150 : 300;
    translate([-x0 + 5, lat_in + lat_g + 5, bar_top]) rotate([180, 0, 0]) baranda_seg(tipo);
}
module imprimir_baranda(tipo, lado) {
    if (lado > 0) baranda_impresa_derecha(tipo);
    else translate([0, 100, 0]) mirror([0, 1, 0]) baranda_impresa_derecha(tipo);   // pieza izquierda (espejo)
}

// ---------- RAMPAS DE SALIDA ----------
// Canaleta (la misma para las 3 salidas) + soportes. Pendiente de 20°.
// Salidas 1 y 2: la canaleta empieza en el borde de la banda (y = 102, 1 mm bajo la superficie), pasa sobre
// el lateral y baja hacia afuera; 2 soportes por rampa enganchan el lateral (arriba y por fuera).
// Salida 3: la canaleta recibe la manzana al final de la banda; 2 soportes enganchan la punta de la base.
ang_r   = 20;
t_r     = tan(ang_r);
esp_r   = 2.5;
e_f     = esp_r / cos(ang_r);
ancho_r = 116;            // 110 libres + 2 paredes de 3 mm (ventana de salida de 110 mm)
largo_r = 180;
s_torn  = 45;             // tornillos de la canaleta, medido a lo largo de la pendiente
module rampa() {
    difference() {
        union() {
            cube([ancho_r, largo_r, esp_r]);
            for (x = [0, ancho_r - 3]) cube([3, largo_r, esp_r + 25]);
        }
        translate([-1, 0, 0]) rotate([45, 0, 0]) cube([ancho_r + 2, 4, 4]);          // bisel del borde de entrada
        for (s = [-1, 1]) translate([ancho_r / 2 + s * 45, s_torn, -1]) cylinder(d = 3.4, h = esp_r + 2);
    }
}
// Perfil en el plano (y, z) del montaje; se extruye 12 mm (se imprime acostado, sin soportes).
z0_lat = 35.5;   // cara de arriba de la canaleta en su borde de entrada (y = 102)
function u_lat(y) = z0_lat - (y - 102) * t_r - e_f;
module soporte_rampa_lateral() {
    p = [[105, lat_top], [105, u_lat(105)], [170, u_lat(170)], [127, -36], [123, -36], [123, lat_top]];
    yt = 102 + s_torn * cos(ang_r); zt = z0_lat - s_torn * sin(ang_r);
    difference() {
        linear_extrude(12) polygon(p);
        translate([110, -15, 6]) rotate([0, 90, 0]) cylinder(d = d_torn, h = 20);   // tornillo al costado del lateral
        translate([127, -15, 6]) rotate([0, 90, 0]) cylinder(d = 8.5, h = 60);      // acceso del destornillador
        translate([114, lat_top - 1, 6]) rotate([-90, 0, 0]) cylinder(d = 3.8, h = 40);   // tornillo al borde del lateral
        translate([114, lat_top + 4, 6]) rotate([-90, 0, 0]) cylinder(d = 8, h = 40);
        translate([yt, zt + 0.5, 6]) rotate([0, 0, -90 - ang_r]) rotate([0, 90, 0]) cylinder(d = 2.8, h = 16);   // M3 de la canaleta
    }
}
z0_fin = 20;     // cara de arriba de la canaleta en su borde de entrada (x = 1042)
function u_fin(x) = z0_fin - (x - 1042) * t_r - e_f;
module soporte_rampa_final() {
    p = [[1045, -70], [1045, u_fin(1045)], [1110, u_fin(1110)], [1079, -88], [1075, -88], [1075, -70]];
    xt = 1042 + s_torn * cos(ang_r); zt = z0_fin - s_torn * sin(ang_r);
    difference() {
        linear_extrude(12) polygon(p);
        translate([1060, -79, 6]) rotate([0, 90, 0]) cylinder(d = d_torn, h = 30);   // tornillo a la punta de la base
        translate([1079, -79, 6]) rotate([0, 90, 0]) cylinder(d = 8.5, h = 60);
        translate([1060, -71, 6]) rotate([-90, 0, 0]) cylinder(d = 3.8, h = 100);    // tornillo a la cara de arriba de la base
        translate([1060, -62, 6]) rotate([-90, 0, 0]) cylinder(d = 8, h = 100);
        translate([xt, zt + 0.5, 6]) rotate([0, 0, -90 - ang_r]) rotate([0, 90, 0]) cylinder(d = 2.8, h = 16);
    }
}

// ---------- MONTAJE (para revisar en Blender; coordenadas del montaje en mm) ----------
// openscad -D 'pieza="montaje_rampas"' -o rampas.stl banda_manzanas.scad   (grupos: portarod, motor, ir, barandas, rampas)
module en_lado(s) { if (s > 0) children(); else mirror([0, 1, 0]) children(); }
module montaje(grupo) {
    if (grupo == "portarod") for (s = [-1, 1]) en_lado(s) {
        multmatrix([[1, 0, 0, 0], [0, 0, -1, lat_in + lat_g + 12], [0, 1, 0, 0]]) porta_rodamiento(true);
        multmatrix([[1, 0, 0, 1000], [0, 0, -1, lat_in + lat_g + 12], [0, 1, 0, 0]]) porta_rodamiento(false);
    }
    if (grupo == "motor") translate([1000, 173, -70]) soporte_motor();
    if (grupo == "ir") for (s = [-1, 1]) en_lado(s) translate([170, lat_in, lat_top]) soporte_ir();
    if (grupo == "barandas") for (s = [-1, 1]) en_lado(s) for (tp = ["carga", "ir", "final"]) baranda_seg(tp);
    if (grupo == "rampas") {
        // salida 1 (+y, x = 560-670) y salida 2 (-y, x = 855-965): canaleta + 2 soportes
        for (r = [[615, 1], [910, -1]]) en_lado(r[1]) {
            o = [r[0] - ancho_r / 2, 102 - esp_r * sin(ang_r), z0_lat - esp_r * cos(ang_r)];
            multmatrix([[1, 0, 0, o[0]], [0, cos(ang_r), sin(ang_r), o[1]], [0, -sin(ang_r), cos(ang_r), o[2]]]) rampa();
            for (dx = [-45, 45]) multmatrix([[0, 0, 1, r[0] + dx - 6], [1, 0, 0, 0], [0, 1, 0, 0]]) soporte_rampa_lateral();
        }
        // salida 3 (al final de la banda)
        o3 = [1042 - esp_r * sin(ang_r), ancho_r / 2, z0_fin - esp_r * cos(ang_r)];
        multmatrix([[0, cos(ang_r), sin(ang_r), o3[0]], [-1, 0, 0, o3[1]], [0, -sin(ang_r), cos(ang_r), o3[2]]]) rampa();
        for (yb = [-45, 45]) multmatrix([[1, 0, 0, 0], [0, 0, -1, yb + 6], [0, 1, 0, 0]]) soporte_rampa_final();
    }
}

// ---------- PLACAS PARA IMPRIMIR (cama de 220 x 220 mm) ----------
// Cada placa junta varias piezas ya orientadas para imprimir, sin salirse de la cama.
module placa_base(n) {
    if (n == 6) {   // 4 porta-rodamientos + soporte del motor + 2 soportes IR
        translate([35, 34, 0]) porta_rodamiento(true);
        translate([110, 34, 0]) porta_rodamiento(true);
        translate([175, 34, 0]) porta_rodamiento(false);
        translate([25, 97, 0]) porta_rodamiento(false);
        translate([80, 63, 0]) imprimir_soporte_motor();
        translate([125, 63, 0]) soporte_ir();
        translate([160, 63, 0]) soporte_ir();
    }
    if (n == 7 || n == 8 || n == 9) {   // baranda derecha + izquierda del mismo tramo
        tp = n == 7 ? "carga" : n == 8 ? "ir" : "final";
        imprimir_baranda(tp, 1);
        translate([0, 61, 0]) imprimir_baranda(tp, -1);
    }
    if (n == 10) {   // rampa de una salida lateral + sus 2 soportes
        rampa();
        for (k = [0, 1]) translate([122 - 105, 36 + k * 75, 0]) soporte_rampa_lateral();
    }
    if (n == 11) {   // rampa de la salida 3 + sus 2 soportes
        rampa();
        for (k = [0, 1]) translate([122 - 1045, 88 + k * 110, 0]) soporte_rampa_final();
    }
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
else if (pieza == "portarod_motriz") porta_rodamiento(false);
else if (pieza == "portarod_tensor") porta_rodamiento(true);
else if (pieza == "soporte_motor") imprimir_soporte_motor();
else if (pieza == "soporte_ir") soporte_ir();
else if (pieza == "baranda_carga_d") imprimir_baranda("carga", 1);
else if (pieza == "baranda_carga_i") imprimir_baranda("carga", -1);
else if (pieza == "baranda_ir_d") imprimir_baranda("ir", 1);
else if (pieza == "baranda_ir_i") imprimir_baranda("ir", -1);
else if (pieza == "baranda_final_d") imprimir_baranda("final", 1);
else if (pieza == "baranda_final_i") imprimir_baranda("final", -1);
else if (pieza == "rampa") rampa();
else if (pieza == "soporte_rampa_lateral") soporte_rampa_lateral();
else if (pieza == "soporte_rampa_final") soporte_rampa_final();
else if (pieza == "placa_06") placa_base(6);
else if (pieza == "placa_07") placa_base(7);
else if (pieza == "placa_08") placa_base(8);
else if (pieza == "placa_09") placa_base(9);
else if (pieza == "placa_10") placa_base(10);
else if (pieza == "placa_11") placa_base(11);
else if (pieza == "montaje_portarod") montaje("portarod");
else if (pieza == "montaje_motor") montaje("motor");
else if (pieza == "montaje_ir") montaje("ir");
else if (pieza == "montaje_barandas") montaje("barandas");
else if (pieza == "montaje_rampas") montaje("rampas");
