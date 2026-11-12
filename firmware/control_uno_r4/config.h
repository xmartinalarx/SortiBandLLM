// Configuración del Arduino UNO R4 WiFi de control. Distancias en mm; calibrar con la banda real.
#pragma once

// ---------- Modo banco ----------
// Descomentar para probar el Arduino suelto, sin sensor IR: cada 'm' que se escribe
// en el Monitor Serie simula una manzana cruzando el sensor.
#define MODO_BANCO   // ACTIVO para la primera prueba; comentar cuando el sensor IR esté conectado

// ---------- Pines (POR CONFIRMAR con el grupo antes de cablear) ----------
// El UNO R4 trabaja con lógica de 5 V: sirve directo para la placa ULN2003, los servos y el sensor IR.
// No usar D0 y D1 (puerto serie).
#define PIN_IN1         6    // placa ULN2003 del motor 28BYJ-48
#define PIN_IN2         5
#define PIN_IN3         4
#define PIN_IN4         3
#define PIN_SERVO_1     9    // paleta 1 (salida derecha, defectuosas)
#define PIN_SERVO_2     10   // paleta 2 (salida izquierda, grupo A)
#define PIN_IR          2    // sensor de barrera: LOW = haz cortado (verificar con el sensor real)
#define PIN_EMERGENCIA  7    // pulsador de emergencia entre D7 y GND (patas en diagonal); apretado = LOW

// ---------- Motor 28BYJ-48 (5 V) con placa ULN2003 ----------
// Se mueve en medio paso: 8 pasos por ciclo, reductora de 63,68:1 -> 4076 medios pasos por vuelta
// del eje de salida. Una vuelta del piñón mueve 2·π·32,4 mm = 203,6 mm de banda.
#define PASOS_POR_VUELTA   4076
#define MM_POR_VUELTA      203.6f
#define PASOS_POR_MM       (PASOS_POR_VUELTA / MM_POR_VUELTA)   // ≈ 20
#define SENTIDO_INVERTIDO  0      // 1 si la banda avanza al revés
// El 28BYJ-48 tiene poca fuerza y llega a ~12 rpm: velocidades bajas.
#define VELOCIDAD_INICIAL  30     // mm/s (~9 rpm en el piñón)
#define VELOCIDAD_MIN      10
#define VELOCIDAD_MAX      40     // ~12 rpm: más rápido pierde pasos
#define ACELERACION_MM_S2  40     // arranque suave: el motor no pierde pasos y las manzanas no ruedan

// ---------- Recorrido de cada manzana (medido con los pasos del motor) ----------
#define DIST_IR_A_CAMARA   110    // sensor IR (x=170) -> centro del túnel (x=280)
#define MARGEN_SERVO       30     // se cierra antes: el servo tarda ~0,15 s en girar
// Desde la cámara:
#define CIERRE_P1   (227 - MARGEN_SERVO)   // paleta 1 cerrada antes de +227 mm
#define APERTURA_P1 507                    // +227 + ~280 mm que tarda en salir
#define CIERRE_P2   (527 - MARGEN_SERVO)
#define APERTURA_P2 807

#define DISTANCIA_MIN_IR   40     // ignora otro corte del IR en menos de 40 mm (la misma manzana)

// ---------- Servos (calibrar ángulos con la paleta montada) ----------
#define ANGULO_P1_ABIERTA  0
#define ANGULO_P1_CERRADA  45
#define ANGULO_P2_ABIERTA  0
#define ANGULO_P2_CERRADA  45

// ---------- MQTT ----------
#define MQTT_PUERTO        1883
#define MQTT_CLIENT_ID     "control_uno_r4"
#define PERIODO_STATUS_MS  2000
