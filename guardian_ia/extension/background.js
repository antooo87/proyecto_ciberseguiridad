// Guardián IA · trabajador de fondo de la extensión.
// Es el único que habla con el servicio del PC (http://127.0.0.1:8788) y el único que guarda la clave.
// Las páginas (chatgpt.com...) nunca ven la clave ni tus datos restaurados: solo reciben el texto ya tapado.
"use strict";

const POR_DEFECTO = {
  puerto: 8788,
  clave: "",
  alPegar: true, // tapar los datos al pegar un texto
  antesDeEnviar: true, // revisar el mensaje antes de enviarlo
  revisarTodo: false, // revisar SIEMPRE en el servicio (con --ia pilla nombres; hay que pulsar Enter dos veces)
  bloquearSinServicio: true, // si el servicio está apagado y el texto parece llevar datos, no pegarlo ni enviarlo
  mejorarPregunta: true, // botón «✨ Mejorar» junto al cuadro del chat (y Alt+M)
};
const ESPERA_MS = 90000; // con --ia, el modelo local puede tardar

async function opciones() {
  return { ...POR_DEFECTO, ...(await chrome.storage.local.get(Object.keys(POR_DEFECTO))) };
}

async function llamar(ruta, cuerpo) {
  const o = await opciones();
  if (!o.clave) throw new Error("Falta la clave del servicio: ábrela en las opciones de la extensión.");
  let respuesta;
  try {
    respuesta = await fetch(`http://127.0.0.1:${Number(o.puerto) || 8788}${ruta}`, {
      method: cuerpo === undefined ? "GET" : "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${o.clave}` },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal: AbortSignal.timeout(ESPERA_MS),
      cache: "no-store",
    });
  } catch (e) {
    throw new Error("El Guardián de tu PC no responde. Arráncalo con: python -m guardian servicio");
  }
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) throw new Error(datos.error || `El servicio ha contestado ${respuesta.status}`);
  return datos;
}

// Cuántos datos se han tapado en cada pestaña: se ve en el icono
async function contar(tabId, datos) {
  const n = Object.values(datos || {}).reduce((a, b) => a + b, 0);
  if (!n || tabId === undefined) return;
  const clave = `cuenta_${tabId}`;
  const total = ((await chrome.storage.session.get(clave))[clave] || 0) + n;
  await chrome.storage.session.set({ [clave]: total });
  await chrome.action.setBadgeBackgroundColor({ tabId, color: "#1f6feb" });
  await chrome.action.setBadgeText({ tabId, text: total > 99 ? "99+" : String(total) });
}

// La última respuesta de la IA en cada pestaña, ya con tus datos: solo la lee el panel de la extensión
async function guardarRespuesta(tabId, origen, texto) {
  const r = await llamar("/v1/guardian/restaurar", { texto });
  const ultima = { origen, texto: r.texto, nivel: r.nivel, hallazgos: r.hallazgos, hora: Date.now() };
  await chrome.storage.session.set({ [`ultima_${tabId}`]: ultima });
  if (r.nivel === "PELIGRO") {
    await chrome.action.setBadgeBackgroundColor({ tabId, color: "#d1242f" });
    await chrome.action.setBadgeText({ tabId, text: "!" });
  }
  return ultima;
}

chrome.runtime.onInstalled.addListener(async (detalles) => {
  chrome.contextMenus.create({
    id: "ver-con-mis-datos",
    title: "Guardián: ver con mis datos",
    contexts: ["selection"],
  });
  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
  if (detalles.reason === "install") chrome.runtime.openOptionsPage();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});

// Clic derecho sobre un texto seleccionado (cualquier web): se ve con tus datos en el panel
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== "ver-con-mis-datos" || !tab) return;
  chrome.sidePanel.open({ tabId: tab.id }).catch(() => {}); // tiene que ir antes de cualquier espera
  guardarRespuesta(tab.id, "texto seleccionado", info.selectionText || "").catch(async (e) => {
    await chrome.storage.session.set({ [`ultima_${tab.id}`]: { error: String(e.message || e), hora: Date.now() } });
  });
});

chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.session.remove([`cuenta_${tabId}`, `ultima_${tabId}`]);
});

chrome.runtime.onMessage.addListener((mensaje, remitente, responder) => {
  if (remitente.id !== chrome.runtime.id || !mensaje || typeof mensaje.tipo !== "string") return false;
  const tabId = mensaje.tabId ?? remitente.tab?.id;
  const tareas = {
    // A las páginas solo se les dan los interruptores, nunca la clave
    opciones: async () => {
      const { clave, ...resto } = await opciones();
      return { opciones: resto, configurada: Boolean(clave) };
    },
    salud: () => llamar("/salud"),
    // Resumen de la semana (sin datos): solo para las páginas de la propia extensión, no para las webs
    actividad: async () => {
      if (!String(remitente.url || "").startsWith(chrome.runtime.getURL(""))) throw new Error("Solo para el panel");
      return llamar("/v1/guardian/actividad");
    },
    proteger: async () => {
      const r = await llamar("/v1/guardian/proteger", { texto: String(mensaje.texto || ""), pegado: mensaje.pegado === true });
      await contar(remitente.tab?.id, r.datos);
      return r;
    },
    respuesta: () => guardarRespuesta(tabId, mensaje.origen || "respuesta de la IA", String(mensaje.texto || "")),
    restaurar: () => llamar("/v1/guardian/restaurar", { texto: String(mensaje.texto || "") }),
    // Dos versiones mejores de tu pregunta, ya con tus datos tapados (con la misma bóveda que el resto del chat)
    mejorar: () => llamar("/v1/guardian/mejorar", { texto: String(mensaje.texto || "").slice(0, 20000) }),
    nueva: async () => {
      const r = await llamar("/v1/guardian/nueva", {});
      await chrome.storage.session.clear();
      return r;
    },
  };
  const tarea = tareas[mensaje.tipo];
  if (!tarea) return false; // otros mensajes (p. ej. "ultima_respuesta") son para la página, no para aquí
  tarea()
    .then((r) => responder({ ok: true, ...r }))
    .catch((e) => responder({ ok: false, error: String(e.message || e) }));
  return true; // la respuesta llega más tarde
});
