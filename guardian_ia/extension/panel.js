// Panel lateral del Guardián: enseña la última respuesta de la IA con tus datos reales.
// Todo se escribe con textContent (nunca innerHTML): una respuesta de la IA no puede meter código aquí.
"use strict";

const $ = (id) => document.getElementById(id);
const URL_PRUEBA = chrome.runtime.getURL("prueba.html");
let enPestana = false; // true si el panel se ha abierto como una pestaña normal y no al lado de la web

function pedir(mensaje) {
  return new Promise((resolver) => {
    chrome.runtime.sendMessage(mensaje, (r) => {
      if (chrome.runtime.lastError) resolver({ ok: false, error: chrome.runtime.lastError.message });
      else resolver(r || { ok: false, error: "sin respuesta" });
    });
  });
}

async function pestanaActiva() {
  const [pestana] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return pestana;
}

async function comprobarServicio() {
  const r = await pedir({ tipo: "salud" });
  $("punto").className = `punto ${r.ok ? "ok" : "mal"}`;
  $("estado-texto").textContent = r.ok
    ? `Conectado al Guardián ${r.version} de tu PC${r.ia_local ? " · con IA local" : " · solo reglas"}`
    : r.error;
}

function pintar(ultima) {
  if (!ultima) {
    $("respuesta").classList.add("oculto");
    $("sin-respuesta").classList.remove("oculto");
    return;
  }
  $("sin-respuesta").classList.add("oculto");
  $("respuesta").classList.remove("oculto");
  if (ultima.error) {
    $("nivel").className = "nivel AVISO";
    $("nivel").textContent = "ERROR";
    $("origen").textContent = "";
    $("hallazgos").replaceChildren();
    $("texto").textContent = ultima.error;
    return;
  }
  $("nivel").className = `nivel ${ultima.nivel}`;
  $("nivel").textContent = ultima.nivel;
  $("origen").textContent = `${ultima.origen} · ${new Date(ultima.hora).toLocaleTimeString()}`;
  $("hallazgos").replaceChildren(...(ultima.hallazgos || []).map((h) => {
    const caja = document.createElement("div");
    caja.className = `hallazgo ${h.gravedad}`;
    caja.textContent = h.explicacion;
    if (h.fragmento) {
      const codigo = document.createElement("code");
      codigo.textContent = h.fragmento;
      caja.appendChild(codigo);
    }
    return caja;
  }));
  $("texto").textContent = ultima.texto;
}

async function mostrarDeLaPestana() {
  if (enPestana) {
    // Abierto en su propia pestaña: se enseña la respuesta más reciente de cualquier pestaña
    const todo = await chrome.storage.session.get(null);
    const ultimas = Object.entries(todo).filter(([k]) => k.startsWith("ultima_")).map(([, v]) => v);
    ultimas.sort((a, b) => (b.hora || 0) - (a.hora || 0));
    pintar(ultimas[0]);
    return;
  }
  const pestana = await pestanaActiva();
  if (!pestana) return;
  const clave = `ultima_${pestana.id}`;
  pintar((await chrome.storage.session.get(clave))[clave]);
}

// En las webs de chatbots contesta el script de la página; la página de prueba es de la propia extensión
// y contesta por el canal de la extensión (sin el permiso "tabs" no se puede saber la dirección de la pestaña).
function preguntarALaPestana(tabId) {
  return new Promise((resolver) => {
    chrome.tabs.sendMessage(tabId, { tipo: "ultima_respuesta" }, (x) => {
      resolver(chrome.runtime.lastError ? null : x);
    });
  });
}

$("leer").addEventListener("click", async () => {
  const pestana = await pestanaActiva();
  if (!pestana) return;
  let r = await preguntarALaPestana(pestana.id);
  if (!r || !r.ok) r = await pedir({ tipo: "ultima_respuesta", tabId: pestana.id });
  if (!r || !r.ok) {
    pintar({ error: "Esta página no es un chatbot conocido. Selecciona el texto y usa el clic derecho → " +
      "«Guardián: ver con mis datos».", hora: Date.now() });
    return;
  }
  if (!r.texto) {
    pintar({ error: "No he encontrado ninguna respuesta de la IA en esta página.", hora: Date.now() });
    return;
  }
  const g = await pedir({ tipo: "respuesta", tabId: pestana.id, texto: r.texto, origen: "última respuesta" });
  if (!g.ok) pintar({ error: g.error, hora: Date.now() });
});

$("copiar").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("texto").textContent);
  $("copiar").textContent = "Copiado ✓";
  setTimeout(() => { $("copiar").textContent = "Copiar"; }, 1500);
});

$("proteger").addEventListener("click", async () => {
  const r = await pedir({ tipo: "proteger", texto: $("entrada").value });
  $("salida").classList.remove("oculto");
  if (!r.ok) {
    $("salida").textContent = r.error;
    return;
  }
  $("salida").textContent = r.protegido + (r.resumen ? `\n\n(Tapados: ${r.resumen}. Ya está copiado.)` : "\n\n(Nada que tapar.)");
  await navigator.clipboard.writeText(r.protegido).catch(() => {});
});

$("nueva").addEventListener("click", async () => {
  const r = await pedir({ tipo: "nueva" });
  $("estado-texto").textContent = r.ok ? "Bóveda vaciada: los marcadores anteriores ya no se pueden restaurar." : r.error;
  pintar(null);
});

$("abrir-opciones").addEventListener("click", () => chrome.runtime.openOptionsPage());
$("abrir-prueba").addEventListener("click", () => chrome.tabs.create({ url: URL_PRUEBA }));

chrome.storage.onChanged.addListener((cambios, zona) => {
  if (zona === "session" && Object.keys(cambios).some((k) => k.startsWith("ultima_"))) mostrarDeLaPestana();
});
chrome.tabs.onActivated.addListener(mostrarDeLaPestana);

chrome.tabs.getCurrent((pestana) => {
  enPestana = Boolean(pestana);
  if (enPestana) $("leer").classList.add("oculto"); // en una pestaña, "esta página" sería el propio panel
  mostrarDeLaPestana();
});
comprobarServicio();
setInterval(comprobarServicio, 15000);
