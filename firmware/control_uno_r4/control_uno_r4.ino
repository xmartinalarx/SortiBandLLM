// ClasifIoT - Arduino UNO R4 WiFi de control: banda (28BYJ-48 + ULN2003), 2 paletas (MG996R),
// sensor IR y parada de emergencia.
//
// Seguimiento por pasos del motor: cuando una manzana corta el sensor IR se guarda la
// posición del motor (en pasos). Como el Arduino mueve el motor, sabe exactamente
// cuántos mm avanzó cada manzana, aunque cambie la velocidad o MQTT se atrase.
//
// Los pulsos del motor los genera un TIMER por hardware (FspTimer), no el loop():
// el WiFi del R4 va por un módulo aparte y sus llamadas pueden bloquear varios ms.
// Con el timer, el motor gira parejo y el conteo de pasos es exacto.
//
// MQTT:
//   publica   sorter/sensor/arrival    {piece_id, ts}             manzana centrada bajo la cámara
//   publica   sorter/control/diverted  {piece_id, output_channel, ts}
//   publica   sorter/control/status    {state, speed, ts}         retenido; Last Will = offline
//   publica   sorter/emergency         {source, ts}               al apretar el hongo
//   escucha   sorter/vision/result, sorter/control/command, sorter/emergency
//
// Placa: "Arduino UNO R4 WiFi" (paquete "Arduino UNO R4 Boards" en el Gestor de placas).
// Librerías (Gestor de librerías): PubSubClient (Nick O'Leary), ArduinoJson 7 (Benoit Blanchon), Servo.
// WiFiS3 y FspTimer vienen con el paquete de la placa.
//
// Prueba sin banda: activar MODO_BANCO en config.h y ver los mensajes con
//   mosquitto_sub -h <ip-del-pc> -t "sorter/#" -v

#include <WiFiS3.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Servo.h>
#include <FspTimer.h>

#include "config.h"
#include "secrets.h"   // copiar secrets.h.example como secrets.h

// ---------- Tópicos ----------
const char* T_ARRIVAL   = "sorter/sensor/arrival";
const char* T_RESULT    = "sorter/vision/result";
const char* T_COMMAND   = "sorter/control/command";
const char* T_STATUS    = "sorter/control/status";
const char* T_DIVERTED  = "sorter/control/diverted";
const char* T_EMERGENCY = "sorter/emergency";
const char* T_SERVO     = "sorter/control/servo";   // confirmación de la prueba manual de servos

// ---------- Estado ----------
enum Estado { DETENIDA, EN_MARCHA, EMERGENCIA };
Estado estado = DETENIDA;
float velocidadObjetivo = VELOCIDAD_INICIAL;   // mm/s pedida
float velocidadActual = 0;                     // mm/s real (sube y baja con la rampa)

WiFiClient wifi;
PubSubClient mqtt(wifi);
Servo servo1, servo2;

// Una manzana en la banda. Va antes de cualquier función: el IDE de Arduino declara
// las funciones automáticamente al inicio y necesita conocer este tipo.
struct Pieza {
  bool activa;
  uint32_t id;
  int32_t posIr;       // posición del motor (pasos) cuando cortó el IR
  int8_t salida;       // salida pedida por la visión (-1 = aún sin resultado)
  bool enCamara;       // ya se publicó arrival
  bool pasoP1;         // ya pasó el punto de decisión de la paleta 1
};

// ---------- Motor 28BYJ-48 por timer ----------
// La placa ULN2003 enciende las 4 bobinas según IN1..IN4. En medio paso se recorre
// esta secuencia de 8 combinaciones; cada una avanza un medio paso.
const uint8_t PINES_MOTOR[4] = {PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4};
const uint8_t SECUENCIA[8] = {0b1000, 0b1100, 0b0100, 0b0110, 0b0010, 0b0011, 0b0001, 0b1001};

FspTimer timerMotor;
volatile bool motorGirando = false;
volatile int32_t posicion = 0;     // medios pasos dados desde el encendido (lo usa el seguimiento)
volatile uint8_t fase = 0;

void escribirBobinas(uint8_t patron) {
  for (int i = 0; i < 4; i++) digitalWrite(PINES_MOTOR[i], (patron >> (3 - i)) & 1);
}

void apagarBobinas() {
  escribirBobinas(0);   // detenido sin corriente: el 28BYJ-48 no se calienta
}

// Se ejecuta en cada interrupción del timer: un medio paso por interrupción.
void pulsoMotor(timer_callback_args_t* __attribute__((unused)) args) {
  if (!motorGirando) return;
  fase = SENTIDO_INVERTIDO ? (fase + 7) & 7 : (fase + 1) & 7;
  escribirBobinas(SECUENCIA[fase]);
  posicion++;
}

int32_t posicionMotor() { return posicion; }   // lectura de 32 bits: atómica en el R4

void fijarFrecuenciaMotor(float mmPorSegundo) {
  timerMotor.set_frequency(mmPorSegundo * PASOS_POR_MM);   // medios pasos por segundo
}

// Rampa de velocidad: se llama desde loop() y acerca la velocidad real a la pedida
unsigned long ultimaRampa = 0;
void actualizarRampa() {
  unsigned long ahora = millis();
  float dt = (ahora - ultimaRampa) / 1000.0f;
  if (dt < 0.01f) return;   // cada 10 ms
  ultimaRampa = ahora;

  float meta = (estado == EN_MARCHA) ? velocidadObjetivo : 0;
  float paso = ACELERACION_MM_S2 * dt;
  if (velocidadActual < meta) velocidadActual = min(meta, velocidadActual + paso);
  else if (velocidadActual > meta) velocidadActual = max(meta, velocidadActual - paso);

  if (velocidadActual < VELOCIDAD_MIN && meta == 0) {   // terminó de frenar
    velocidadActual = 0;
    if (motorGirando) {
      motorGirando = false;
      apagarBobinas();
    }
    return;
  }
  if (velocidadActual > 0) {
    fijarFrecuenciaMotor(max(velocidadActual, (float)VELOCIDAD_MIN));
    motorGirando = true;
  }
}

// ---------- Manzanas en la banda ----------
// Cola (cabe de sobra: con ~310 mm entre manzanas hay ~4 a la vez)
const int MAX_PIEZAS = 16;
Pieza piezas[MAX_PIEZAS];
uint32_t siguienteId = 1;

// Posición del motor en la que se abre cada paleta (-1 = abierta)
int32_t p1AbrirEn = -1;
int32_t p2AbrirEn = -1;

int32_t posUltimoIr = -1000000;
bool irAnterior = false;
unsigned long ultimoStatus = 0;
unsigned long ultimoIntentoMqtt = 0;

// Hora Unix: se pide una vez al módulo WiFi (NTP) y luego se suma millis()
unsigned long horaBase = 0, millisBase = 0;

// ---------- Utilidades ----------
int32_t mmAPasos(float mm) { return (int32_t)(mm * PASOS_POR_MM); }
float pasosAMm(int32_t pasos) { return pasos / PASOS_POR_MM; }

// Hora Unix si hay NTP; si no, 0 (el servidor usa su propia hora al guardar)
unsigned long horaUnix() {
  return horaBase ? horaBase + (millis() - millisBase) / 1000 : 0;
}

const char* nombreEstado() {
  switch (estado) {
    case EN_MARCHA:  return "running";
    case EMERGENCIA: return "emergency";
    default:         return "stopped";
  }
}

void publicar(const char* topico, JsonDocument& doc, bool retener = false) {
  char buffer[256];
  size_t n = serializeJson(doc, buffer);
  mqtt.publish(topico, (const uint8_t*)buffer, n, retener);
  Serial.print("-> "); Serial.print(topico); Serial.print(" "); Serial.println(buffer);
}

void publicarStatus() {
  JsonDocument doc;
  doc["state"] = nombreEstado();
  doc["speed"] = velocidadObjetivo;
  doc["ts"] = horaUnix();
  publicar(T_STATUS, doc, true);
  ultimoStatus = millis();
}

// ---------- Banda y paletas ----------
void arrancarBanda() {
  if (estado == EMERGENCIA && digitalRead(PIN_EMERGENCIA) == LOW) {
    Serial.println("No se puede arrancar: boton de emergencia apretado");
    return;
  }
  abrirPaletas();                  // por si quedaron movidas en una prueba manual
  estado = EN_MARCHA;              // la rampa acelera el motor desde actualizarRampa()
}

// Prueba manual de un servo desde el dashboard (acción "servo" en sorter/control/command).
// Solo con la banda detenida, para no chocar con las paletas que mueve la clasificación.
// Responde en sorter/control/servo: {servo, angle, ok, motivo?, ts}
void probarServo(int n, int angulo) {
  const char* motivo = nullptr;
  if (estado != DETENIDA) motivo = "la banda debe estar detenida";
  else if (n != 1 && n != 2) motivo = "servo invalido (1 o 2)";
  else if (angulo < 0 || angulo > 180) motivo = "angulo fuera de 0-180";

  if (!motivo) {
    Servo& s = (n == 1) ? servo1 : servo2;
    s.write(angulo);
    Serial.print("Prueba: servo "); Serial.print(n); Serial.print(" -> "); Serial.print(angulo); Serial.println(" grados");
  } else {
    Serial.print("Prueba de servo rechazada: "); Serial.println(motivo);
  }
  JsonDocument doc;
  doc["servo"] = n;
  doc["angle"] = angulo;
  doc["ok"] = motivo == nullptr;
  if (motivo) doc["motivo"] = motivo;
  doc["ts"] = horaUnix();
  publicar(T_SERVO, doc);
}

void detenerBanda() {
  estado = DETENIDA;               // la rampa lo frena suave
}

void abrirPaletas() {
  servo1.write(ANGULO_P1_ABIERTA);
  servo2.write(ANGULO_P2_ABIERTA);
  p1AbrirEn = -1;
  p2AbrirEn = -1;
}

void emergencia(const char* origen, bool publicarAviso) {
  estado = EMERGENCIA;
  motorGirando = false;            // sin rampa: se detiene de inmediato
  velocidadActual = 0;
  apagarBobinas();
  abrirPaletas();
  Serial.print("EMERGENCIA desde "); Serial.println(origen);
  if (publicarAviso && mqtt.connected()) {
    JsonDocument doc;
    doc["source"] = origen;
    doc["ts"] = horaUnix();
    publicar(T_EMERGENCY, doc);
  }
  publicarStatus();
}

// ---------- Seguimiento de manzanas ----------
void nuevaPieza() {
  int32_t pos = posicionMotor();
  if (pos - posUltimoIr < mmAPasos(DISTANCIA_MIN_IR)) return;   // es la misma manzana
  posUltimoIr = pos;
  for (int i = 0; i < MAX_PIEZAS; i++) {
    if (!piezas[i].activa) {
      piezas[i] = {true, siguienteId++, pos, -1, false, false};
      Serial.print("Manzana en el sensor IR: "); Serial.println(piezas[i].id);
      return;
    }
  }
  Serial.println("AVISO: cola de manzanas llena");
}

void publicarDesvio(Pieza& p, int salida, const char* motivo) {
  JsonDocument doc;
  doc["piece_id"] = p.id;
  doc["output_channel"] = salida;
  doc["ts"] = horaUnix();
  publicar(T_DIVERTED, doc);
  Serial.print("Manzana "); Serial.print(p.id); Serial.print(" -> salida ");
  Serial.print(salida); Serial.print(" ("); Serial.print(motivo); Serial.println(")");
  p.activa = false;
}

void procesarPiezas() {
  int32_t pos = posicionMotor();

  // Abrir paletas cuando la última manzana desviada ya salió
  if (p1AbrirEn >= 0 && pos >= p1AbrirEn) { servo1.write(ANGULO_P1_ABIERTA); p1AbrirEn = -1; }
  if (p2AbrirEn >= 0 && pos >= p2AbrirEn) { servo2.write(ANGULO_P2_ABIERTA); p2AbrirEn = -1; }

  for (int i = 0; i < MAX_PIEZAS; i++) {
    Pieza& p = piezas[i];
    if (!p.activa) continue;
    float desdeCamara = pasosAMm(pos - p.posIr) - DIST_IR_A_CAMARA;

    // 1) Llegó al centro del túnel: la visión toma la foto
    if (!p.enCamara && desdeCamara >= 0) {
      p.enCamara = true;
      JsonDocument doc;
      doc["piece_id"] = p.id;
      doc["ts"] = horaUnix();
      publicar(T_ARRIVAL, doc);
    }

    // 2) Punto de decisión de la paleta 1
    if (!p.pasoP1 && desdeCamara >= CIERRE_P1) {
      p.pasoP1 = true;
      if (p.salida < 0) {
        p.salida = 3;   // sin resultado a tiempo: no se desvía
        Serial.print("AVISO: sin resultado para la manzana "); Serial.println(p.id);
      }
      if (p1AbrirEn >= 0) {   // la paleta sigue cerrada por la anterior
        publicarDesvio(p, 1, "paleta 1 ocupada");
      } else if (p.salida == 1) {
        servo1.write(ANGULO_P1_CERRADA);
        p1AbrirEn = p.posIr + mmAPasos(DIST_IR_A_CAMARA + APERTURA_P1);
        publicarDesvio(p, 1, "defectuosa");
      }
      continue;
    }

    // 3) Punto de decisión de la paleta 2
    if (p.pasoP1 && desdeCamara >= CIERRE_P2) {
      if (p2AbrirEn >= 0) {
        publicarDesvio(p, 2, "paleta 2 ocupada");
      } else if (p.salida == 2) {
        servo2.write(ANGULO_P2_CERRADA);
        p2AbrirEn = p.posIr + mmAPasos(DIST_IR_A_CAMARA + APERTURA_P2);
        publicarDesvio(p, 2, "grupo A");
      } else {
        publicarDesvio(p, 3, "sigue al final");
      }
    }
  }
}

// ---------- Mensajes recibidos ----------
void alRecibir(char* topico, byte* payload, unsigned int largo) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, largo)) {
    Serial.print("JSON inválido en "); Serial.println(topico);
    return;
  }

  if (strcmp(topico, T_RESULT) == 0) {
    uint32_t id = doc["piece_id"];
    for (int i = 0; i < MAX_PIEZAS; i++) {
      if (piezas[i].activa && piezas[i].id == id) {
        if (piezas[i].pasoP1) { Serial.print("AVISO: resultado tardío de la manzana "); Serial.println(id); }
        else piezas[i].salida = doc["output_channel"] | 3;
        return;
      }
    }
  } else if (strcmp(topico, T_COMMAND) == 0) {
    const char* accion = doc["action"] | "";
    if (strcmp(accion, "start") == 0) arrancarBanda();
    else if (strcmp(accion, "stop") == 0) detenerBanda();
    else if (strcmp(accion, "set_speed") == 0)
      velocidadObjetivo = constrain((float)(doc["value"] | velocidadObjetivo), VELOCIDAD_MIN, VELOCIDAD_MAX);
    else if (strcmp(accion, "servo") == 0) {
      probarServo(doc["servo"] | 0, doc["value"] | -1);
      return;   // no cambia el estado de la banda
    }
    publicarStatus();
  } else if (strcmp(topico, T_EMERGENCY) == 0) {
    const char* origen = doc["source"] | "";
    if (strcmp(origen, MQTT_CLIENT_ID) != 0) emergencia(origen, false);   // ignora la propia
  }
}

// ---------- Conexiones ----------
void conectarWifi() {
  Serial.print("Conectando a "); Serial.print(WIFI_SSID);
  // Red abierta (sin clave): se usa la versión de begin() sin contraseña
  bool redAbierta = strlen(WIFI_PASSWORD) == 0;
  while ((redAbierta ? WiFi.begin(WIFI_SSID) : WiFi.begin(WIFI_SSID, WIFI_PASSWORD)) != WL_CONNECTED) {
    Serial.print(".");
    delay(1000);
  }
  Serial.print("\nWiFi conectado, IP "); Serial.println(WiFi.localIP());

  // Hora por NTP (el módulo WiFi la obtiene); puede tardar unos segundos o no estar
  for (int i = 0; i < 10 && horaBase == 0; i++) {
    horaBase = WiFi.getTime();
    millisBase = millis();
    if (horaBase == 0) delay(500);
  }
  if (horaBase == 0) Serial.println("Sin hora NTP: se enviará ts = 0");
}

void mantenerMqtt() {
  if (mqtt.connected()) {
    mqtt.loop();
    return;
  }
  // Regla del proyecto: sin broker, la banda se detiene
  if (estado == EN_MARCHA) {
    detenerBanda();
    Serial.println("Broker perdido: banda detenida");
  }
  if (millis() - ultimoIntentoMqtt < 2000) return;   // reintenta cada 2 s
  ultimoIntentoMqtt = millis();
  // Last Will: si el Arduino se desconecta, el broker publica {"state":"offline"} retenido
  if (mqtt.connect(MQTT_CLIENT_ID, T_STATUS, 1, true, "{\"state\":\"offline\"}")) {
    Serial.println("MQTT conectado");
    mqtt.subscribe(T_RESULT, 1);
    mqtt.subscribe(T_COMMAND, 1);
    mqtt.subscribe(T_EMERGENCY, 1);
    publicarStatus();
  } else {
    Serial.print("MQTT falló (estado "); Serial.print(mqtt.state());
    Serial.print(") | WiFi "); Serial.print(WiFi.status() == WL_CONNECTED ? "conectado" : "DESCONECTADO");
    Serial.print(", IP "); Serial.print(WiFi.localIP());
    Serial.print(", broker "); Serial.print(MQTT_HOST); Serial.println(" | reintentando");
  }
}

// ---------- Entradas ----------
void leerSensores() {
  // Pulsador de emergencia entre D7 y GND: apretado = LOW
  bool botonApretado = digitalRead(PIN_EMERGENCIA) == LOW;
  static bool botonAnterior = false;
  if (botonApretado != botonAnterior) {   // diagnóstico: avisa cada cambio del pin D7
    Serial.println(botonApretado ? "Boton D7: APRETADO" : "Boton D7: suelto");
    botonAnterior = botonApretado;
  }
  if (botonApretado && estado != EMERGENCIA) {
    emergencia(MQTT_CLIENT_ID, true);
  }

#ifdef MODO_BANCO
  if (Serial.available() && Serial.read() == 'm') nuevaPieza();
#else
  bool irCortado = digitalRead(PIN_IR) == LOW;
  if (irCortado && !irAnterior && estado == EN_MARCHA) nuevaPieza();   // flanco: recién cortado
  irAnterior = irCortado;
#endif
}

void iniciarTimerMotor() {
  uint8_t tipo;
  int8_t canal = FspTimer::get_available_timer(tipo);
  if (canal < 0) {
    Serial.println("ERROR: no hay timer libre para el motor");
    while (true) {}
  }
  timerMotor.begin(TIMER_MODE_PERIODIC, tipo, canal,
                   VELOCIDAD_INICIAL * PASOS_POR_MM, 0.0f, pulsoMotor);
  timerMotor.setup_overflow_irq();
  timerMotor.open();
  timerMotor.start();
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(PINES_MOTOR[i], OUTPUT);
  apagarBobinas();                  // motor sin corriente hasta el primer start
  pinMode(PIN_IR, INPUT_PULLUP);
  pinMode(PIN_EMERGENCIA, INPUT_PULLUP);

  servo1.attach(PIN_SERVO_1, 500, 2400);
  servo2.attach(PIN_SERVO_2, 500, 2400);
  abrirPaletas();

  iniciarTimerMotor();
  conectarWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PUERTO);
  mqtt.setBufferSize(512);
  mqtt.setCallback(alRecibir);
#ifdef MODO_BANCO
  Serial.println("MODO BANCO: escribe 'm' para simular una manzana");
#endif
}

void loop() {
  if (WiFi.status() != WL_CONNECTED && estado == EN_MARCHA) detenerBanda();
  mantenerMqtt();
  leerSensores();
  actualizarRampa();
  procesarPiezas();
  if (mqtt.connected() && millis() - ultimoStatus >= PERIODO_STATUS_MS) publicarStatus();
}
