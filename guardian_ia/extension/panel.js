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
  if (r.ok) mostrarActividad();
}

// Lo que ha hecho el Guardián esta semana (del registro de tu PC, que solo guarda cuántos y de qué tipo)
async function mostrarActividad() {
  const r = await pedir({ tipo: "actividad" });
  if (!r.ok) return;
  const suma = (o) => Object.values(o || {}).reduce((a, b) => a + b, 0);
  const cuantos = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;
  const frases = [];
  if (!r.sucesos) frases.push("Todavía no ha tenido que hacer nada.");
  else {
    frases.push(`${cuantos(r.datos_tapados, "dato personal tapado", "datos personales tapados")} antes de llegar a la IA`);
    if (r.documentos_con_trampa) {
      frases.push(cuantos(r.documentos_con_trampa, "texto o documento con trampas desinfectado",
        "textos o documentos con trampas desinfectados"));
    }
    if (r.respuestas.PELIGRO || r.respuestas.AVISO) {
      frases.push(`${cuantos(r.respuestas.PELIGRO || 0, "respuesta con peligro", "respuestas con peligro")} y ` +
        `${r.respuestas.AVISO || 0} con aviso`);
    }
    const acciones = suma(r.acciones_bloqueadas);
    if (acciones) frases.push(cuantos(acciones, "acción de un agente bloqueada", "acciones de agentes bloqueadas"));
    if (r.preguntas_mejoradas) {
      frases.push(`${cuantos(r.preguntas_mejoradas, "pregunta mejorada", "preguntas mejoradas")}` +
        (r.nota_media !== null && r.nota_media !== undefined ? ` (nota media antes de mejorarlas: ${r.nota_media}/100)` : ""));
    }
  }
  $("actividad").replaceChildren(...frases.map((f) => {
    const li = document.createElement("li");
    li.textContent = f;
    return li;
  }));
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
  $("origen").textContent = `${ultima.origen} · ${new Date(ultima.hora).toLocaleTimeString("es-ES")}`;
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

// «¿Es una estafa?» (clic derecho sobre un texto, o el botón de «a mano»)
function pintarEstafa(r) {
  if (!r) {
    $("estafa").classList.add("oculto");
    return;
  }
  $("estafa").classList.remove("oculto");
  const veredicto = $("estafa-veredicto");
  const lista = (id, cosas) => $(id).replaceChildren(...(cosas || []).map((c) => elemento("li", "", c)));
  if (r.error) {
    veredicto.className = "estado MEDIO";
    veredicto.textContent = r.error;
    $("estafa-auxilio").classList.add("oculto");
    lista("estafa-pistas", []);
    lista("estafa-pasos", []);
    return;
  }
  veredicto.className = `estado ${r.nivel}`;
  veredicto.textContent = `${r.veredicto}${r.tipo ? ` · ${r.tipo}` : ""}`;
  const auxilio = r.si_ya_lo_hiciste || [];
  $("estafa-auxilio").classList.toggle("oculto", !auxilio.length);
  $("estafa-auxilio").textContent = auxilio.length ? `🚑 Si ya lo has hecho, ahora mismo: ${auxilio.join(" ")}` : "";
  lista("estafa-pistas", (r.senales || []).map((p) => `${p.explicacion} («${String(p.fragmento).slice(0, 90)}»)`));
  if (!(r.senales || []).length) lista("estafa-pistas", ["Ninguna de las pistas típicas."]);
  lista("estafa-pasos", r.que_hacer);
}

async function mostrarDeLaPestana() {
  if (enPestana) {
    // Abierto en su propia pestaña: se enseña la respuesta más reciente de cualquier pestaña
    const todo = await chrome.storage.session.get(null);
    const ultimas = Object.entries(todo).filter(([k]) => k.startsWith("ultima_")).map(([, v]) => v);
    ultimas.sort((a, b) => (b.hora || 0) - (a.hora || 0));
    pintar(ultimas[0]);
    const estafas = Object.entries(todo).filter(([k]) => k.startsWith("estafa_")).map(([, v]) => v);
    estafas.sort((a, b) => (b.hora || 0) - (a.hora || 0));
    pintarEstafa(estafas[0]);
    return;
  }
  const pestana = await pestanaActiva();
  if (!pestana) return;
  const claves = [`ultima_${pestana.id}`, `estafa_${pestana.id}`];
  const guardado = await chrome.storage.session.get(claves);
  pintar(guardado[claves[0]]);
  pintarEstafa(guardado[claves[1]]);
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
  $("mejoras").classList.add("oculto");
  if (!r.ok) {
    $("salida").textContent = r.error;
    return;
  }
  $("salida").textContent = r.protegido + (r.resumen ? `\n\n(Tapados: ${r.resumen}. Ya está copiado.)` : "\n\n(Nada que tapar.)");
  await navigator.clipboard.writeText(r.protegido).catch(() => {});
});

function elemento(etiqueta, clase, texto) {
  const n = document.createElement(etiqueta);
  if (clase) n.className = clase;
  if (texto !== undefined) n.textContent = texto;
  return n;
}

$("mejorar").addEventListener("click", async () => {
  const caja = $("mejoras");
  caja.classList.remove("oculto");
  $("salida").classList.add("oculto");
  caja.replaceChildren(elemento("p", "pequeno", "Mirando tu pregunta en el Guardián de tu PC…"));
  const r = await pedir({ tipo: "mejorar", texto: $("entrada").value });
  if (!r.ok) {
    caja.replaceChildren(elemento("div", "caja", r.error));
    return;
  }
  const cabecera = elemento("div", "mejora-cabecera");
  cabecera.append(elemento("span", `nota ${r.nota >= 80 ? "alta" : r.nota >= 50 ? "media" : "baja"}`, `Nota ${r.nota}/100`),
    elemento("span", "pequeno", r.con_ia ? "reescrita por la IA de tu PC" : "hecha con reglas en tu PC"));
  const partes = [cabecera];
  if (r.consejos.length) {
    const lista = elemento("ul", "pequeno lista");
    lista.append(...r.consejos.map((c) => elemento("li", "", c)));
    partes.push(lista);
  }
  r.versiones.forEach((v, i) => {
    const bloque = elemento("div", "version");
    const copiar = elemento("button", "", "Copiar");
    copiar.addEventListener("click", async () => {
      await navigator.clipboard.writeText(v.texto).catch(() => {});
      copiar.textContent = "Copiado ✓";
      setTimeout(() => { copiar.textContent = "Copiar"; }, 1500);
    });
    bloque.append(elemento("h3", "", `Opción ${i + 1} · ${v.titulo}`), elemento("div", "pequeno", v.por_que),
      elemento("div", "caja", v.texto), copiar);
    partes.push(bloque);
  });
  caja.replaceChildren(...partes);
});

$("analizar-estafa").addEventListener("click", async () => {
  $("salida").classList.add("oculto");
  $("mejoras").classList.add("oculto");
  const pestana = enPestana ? null : await pestanaActiva();
  const r = await pedir({ tipo: "estafa", texto: $("entrada").value, tabId: pestana ? pestana.id : -1 });
  pintarEstafa(r.ok ? r : { error: r.error });
  $("estafa").scrollIntoView({ behavior: "smooth", block: "start" });
});

$("nueva").addEventListener("click", async () => {
  const r = await pedir({ tipo: "nueva" });
  $("estado-texto").textContent = r.ok ? "Bóveda vaciada: los marcadores anteriores ya no se pueden restaurar." : r.error;
  pintar(null);
});

$("abrir-opciones").addEventListener("click", () => chrome.runtime.openOptionsPage());
$("abrir-prueba").addEventListener("click", () => chrome.tabs.create({ url: URL_PRUEBA }));

chrome.storage.onChanged.addListener((cambios, zona) => {
  if (zona === "session" && Object.keys(cambios).some((k) => k.startsWith("ultima_") || k.startsWith("estafa_"))) {
    mostrarDeLaPestana();
  }
});
chrome.tabs.onActivated.addListener(mostrarDeLaPestana);

chrome.tabs.getCurrent((pestana) => {
  enPestana = Boolean(pestana);
  if (enPestana) $("leer").classList.add("oculto"); // en una pestaña, "esta página" sería el propio panel
  mostrarDeLaPestana();
});
comprobarServicio();
setInterval(comprobarServicio, 15000);
