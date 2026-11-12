// Dashboard de ClasifIoT: consulta la API cada 1,5 s y envía los comandos.
// Sin frameworks ni websockets, para que sea fácil de leer y explicar.

const REFRESCO_MS = 1500;
const COLOR_BARRA = { rojo: "var(--rojo)", verde: "var(--verde)", amarillo: "var(--amarillo)" };
const NOMBRE_SALIDA = { 1: "1 · defectuosas", 2: "2 · grupo A", 3: "3 · resto" };
const NOMBRE_ESTADO = {
  running: "en marcha", stopped: "detenida", emergency: "EMERGENCIA",
  offline: "sin conexión", desconocido: "sin datos",
};

const $ = (id) => document.getElementById(id);

async function api(ruta, opciones = {}) {
  const resp = await fetch(ruta, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  const datos = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(datos.detail || `Error ${resp.status}`);
  return datos;
}

function mostrarMensaje(texto, esError = false) {
  const el = $("mensaje");
  el.textContent = texto;
  el.style.color = esError ? "var(--mal)" : "var(--dim)";
}

function pastilla(el, texto, clase) {
  el.textContent = texto;
  el.className = "pastilla " + (clase || "");
}

// ---------- Lectura periódica ----------
async function actualizarEstado() {
  try {
    const e = await api("/api/estado");
    const estado = e.banda.state || "desconocido";
    const clase = { running: "ok", emergency: "mal", offline: "mal", stopped: "aviso" }[estado];
    pastilla($("estado-banda"), "banda: " + (NOMBRE_ESTADO[estado] || estado), clase);
    pastilla($("estado-mqtt"), "MQTT: " + (e.mqtt_conectado ? "conectado" : "desconectado"),
             e.mqtt_conectado ? "ok" : "mal");
    $("velocidad-actual").textContent = e.banda.speed ?? "–";
    if (e.error_bd) pastilla($("estado-bd"), "BD: error", "mal");
    actualizarServos(estado, e.servos || {});
  } catch (err) {
    pastilla($("estado-mqtt"), "servidor caído", "mal");
  }
}

function dibujarBarras(contenedor, conteos, nombres = {}, colores = {}) {
  const total = Object.values(conteos).reduce((a, b) => a + b, 0);
  contenedor.innerHTML = "";
  if (!total) {
    contenedor.innerHTML = '<p class="dim">Sin datos.</p>';
    return;
  }
  for (const [clave, n] of Object.entries(conteos)) {
    const pct = (100 * n / total).toFixed(0);
    const fila = document.createElement("div");
    fila.className = "barra";
    fila.innerHTML = `
      <span>${nombres[clave] || clave}</span>
      <span class="pista"><span class="relleno" style="width:${pct}%;background:${colores[clave] || ""}"></span></span>
      <span class="num">${n} (${pct} %)</span>`;
    contenedor.appendChild(fila);
  }
}

async function actualizarEstadisticas() {
  try {
    const s = await api("/api/estadisticas");
    pastilla($("estado-bd"), "BD: conectada", "ok");
    if (!s.lote) return;
    $("lote").textContent = `#${s.lote.id} ${s.lote.ended_at ? "(cerrado)" : "(en curso)"}`;
    $("total").textContent = s.total;
    $("pct-defectuosas").textContent = s.pct_defectuosas + " %";
    $("por-minuto").textContent = s.por_minuto;
    $("confianza").textContent = s.confianza_promedio != null ? s.confianza_promedio.toFixed(2) : "–";
    dibujarBarras($("barras-color"), s.por_color, {}, COLOR_BARRA);
    dibujarBarras($("barras-salida"), s.por_salida, NOMBRE_SALIDA);
  } catch (err) {
    pastilla($("estado-bd"), "BD: sin conexión", "mal");
  }
}

function hora(ts) {
  return ts ? new Date(ts).toLocaleTimeString("es-CL") : "–";
}

async function actualizarHistorial() {
  try {
    const piezas = await api("/api/piezas?limite=20");
    $("historial").innerHTML = piezas.map((p) => `
      <tr>
        <td>${p.piece_id}</td>
        <td>${hora(p.ts)}</td>
        <td>${p.color ?? "–"}</td>
        <td>${p.is_defective == null ? "–" : p.is_defective ? "sí" : "no"}</td>
        <td>${p.confidence != null ? p.confidence.toFixed(2) : "–"}</td>
        <td>${p.output_channel ?? "–"}</td>
        <td>${p.diverted_ts ? hora(p.diverted_ts) : "en banda"}</td>
      </tr>`).join("");

    const rechazadas = await api("/api/rechazadas?limite=12");
    if (rechazadas.length) {
      $("rechazadas").innerHTML = rechazadas.map((r) => `
        <figure>
          <img src="/${r.image_path}" alt="Manzana ${r.piece_id} defectuosa" loading="lazy">
          <figcaption>#${r.piece_id} · ${r.color} · ${hora(r.ts)}</figcaption>
        </figure>`).join("");
    }
  } catch (err) {
    // El error de BD ya se muestra en la pastilla
  }
}

// ---------- Configuración ----------
async function cargarSettings() {
  try {
    const { settings, colores } = await api("/api/settings");
    const grupoA = settings.grupo_a_colores.split(",").map((c) => c.trim());
    $("colores-grupo-a").innerHTML = colores.map((c) => `
      <label class="fila" style="margin:0">
        <input type="checkbox" value="${c}" ${grupoA.includes(c) ? "checked" : ""}> ${c}
      </label>`).join("");
    $("umbral").value = settings.umbral_confianza;
    $("velocidad").value = settings.velocidad_mm_s;
    $("velocidad-valor").textContent = settings.velocidad_mm_s;
  } catch (err) {
    mostrarMensaje("No se pudo leer la configuración: " + err.message, true);
  }
}

$("form-settings").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const colores = [...document.querySelectorAll("#colores-grupo-a input:checked")].map((i) => i.value);
  try {
    await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ grupo_a_colores: colores, umbral_confianza: parseFloat($("umbral").value) }),
    });
    mostrarMensaje("Configuración guardada.");
  } catch (err) {
    mostrarMensaje(err.message, true);
  }
});

// ---------- Prueba de servos ----------
// Mismos ángulos que firmware/control_uno_r4/config.h (ANGULO_P*_ABIERTA / CERRADA)
const ANGULO_ABIERTA = 0;
const ANGULO_CERRADA = 45;
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

// Muestra la última confirmación del Arduino y bloquea los botones si la banda anda
function actualizarServos(estado, servos) {
  const bloqueado = estado !== "stopped";
  $("servos-aviso").hidden = !bloqueado;
  $("servos-aviso").textContent = estado === "running"
    ? "Detén la banda para probar los servos."
    : "El Arduino debe estar conectado y con la banda detenida.";
  document.querySelectorAll(".servo").forEach((div) => {
    div.querySelectorAll("button").forEach((b) => { b.disabled = bloqueado; });
    const c = servos[div.dataset.servo];
    if (!c) return;
    const p = div.querySelector(".confirmacion");
    const hora = new Date(c.recibido * 1000).toLocaleTimeString("es-CL");
    p.className = "confirmacion " + (c.ok ? "ok" : "mal");
    p.textContent = c.ok
      ? `✓ El Arduino movió el servo a ${c.angle}° (${hora})`
      : `✗ Rechazado: ${c.motivo} (${hora})`;
  });
}

async function moverServo(servo, angle) {
  await api("/api/servo", { method: "POST", body: JSON.stringify({ servo, angle }) });
}

document.querySelectorAll(".servo").forEach((div) => {
  const n = Number(div.dataset.servo);
  const rango = div.querySelector(".angulo");
  const valor = div.querySelector(".angulo-valor");
  rango.addEventListener("input", () => { valor.textContent = rango.value + "°"; });
  div.addEventListener("click", async (ev) => {
    const b = ev.target.closest("button[data-accion]");
    if (!b) return;
    const p = div.querySelector(".confirmacion");
    try {
      const accion = b.dataset.accion;
      if (accion === "abrir") await moverServo(n, ANGULO_ABIERTA);
      else if (accion === "cerrar") await moverServo(n, ANGULO_CERRADA);
      else if (accion === "mover") await moverServo(n, Number(rango.value));
      else if (accion === "probar") {
        p.textContent = "Probando: cierra y vuelve a abrir…";
        await moverServo(n, ANGULO_CERRADA);
        await esperar(1200);
        await moverServo(n, ANGULO_ABIERTA);
      }
    } catch (err) {
      p.className = "confirmacion mal";
      p.textContent = err.message;
    }
  });
});

// ---------- Comandos ----------
async function enviarComando(action, value = null) {
  try {
    await api("/api/comando", { method: "POST", body: JSON.stringify({ action, value }) });
    mostrarMensaje(`Comando enviado: ${action}${value != null ? " " + value : ""}`);
  } catch (err) {
    mostrarMensaje(err.message, true);
  }
}

$("btn-iniciar").addEventListener("click", () => enviarComando("start"));
$("btn-detener").addEventListener("click", () => enviarComando("stop"));
$("velocidad").addEventListener("input", (ev) => { $("velocidad-valor").textContent = ev.target.value; });
$("btn-velocidad").addEventListener("click", () => enviarComando("set_speed", parseFloat($("velocidad").value)));
$("btn-emergencia").addEventListener("click", async () => {
  try {
    await api("/api/emergencia", { method: "POST" });
    mostrarMensaje("Parada de emergencia enviada.", true);
  } catch (err) {
    mostrarMensaje(err.message, true);
  }
});

// ---------- Arranque ----------
function refrescar() {
  actualizarEstado();
  actualizarEstadisticas();
  actualizarHistorial();
}
cargarSettings();
refrescar();
setInterval(refrescar, REFRESCO_MS);
