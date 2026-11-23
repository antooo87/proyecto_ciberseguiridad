// Guardián IA · script de la página del chatbot (chatgpt.com, claude.ai, gemini...).
//
//  1. Al PEGAR un texto en el cuadro del chat, se lo pasa al Guardián de tu PC y pega la versión con los datos
//     tapados ([DNI_1]...). Si el texto es largo, la aduana mira además si esconde órdenes para la IA.
//  2. Antes de ENVIAR (Enter o botón), si el mensaje parece llevar datos, lo tapa y te deja revisarlo.
//  3. Cuando la IA contesta, manda la respuesta al panel de la extensión, que la enseña con tus datos reales.
//     Tus datos reales NUNCA se escriben en la página: la web del chatbot no los puede leer.
(() => {
  "use strict";
  if (window.__guardianIA) return;
  window.__guardianIA = true;

  const G = window.GuardianComun;
  let opciones = { alPegar: true, antesDeEnviar: true, revisarTodo: false, bloquearSinServicio: true };
  let configurada = true;

  function pedir(mensaje) {
    return new Promise((resolver) => {
      try {
        chrome.runtime.sendMessage(mensaje, (r) => {
          if (chrome.runtime.lastError) resolver({ ok: false, error: chrome.runtime.lastError.message });
          else resolver(r || { ok: false, error: "sin respuesta" });
        });
      } catch (e) {
        resolver({ ok: false, error: String(e) }); // la extensión se ha actualizado: hay que recargar la página
      }
    });
  }

  async function cargarOpciones() {
    const r = await pedir({ tipo: "opciones" });
    if (r && r.ok) {
      opciones = { ...opciones, ...r.opciones };
      configurada = r.configurada;
    }
  }
  cargarOpciones();
  chrome.storage.onChanged.addListener((cambios, zona) => { if (zona === "local") cargarOpciones(); });

  // ---------------------------------------------------------------- aviso flotante
  // Va dentro de un "shadow root" cerrado: la página no le cambia el estilo y no puede leerlo fácilmente.
  let raizAviso = null;
  let temporizador = null;
  function avisar(texto, tipo = "info", segundos = 7) {
    if (!raizAviso) {
      const anfitrion = document.createElement("div");
      anfitrion.style.cssText = "position:fixed;z-index:2147483647;right:16px;bottom:16px;max-width:380px;";
      document.documentElement.appendChild(anfitrion);
      raizAviso = anfitrion.attachShadow({ mode: "closed" });
      const estilo = document.createElement("style");
      estilo.textContent = `
        .aviso{font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:#fff;border-radius:10px;
          padding:10px 14px;box-shadow:0 6px 24px rgba(0,0,0,.25);display:flex;gap:8px;align-items:flex-start}
        .info{background:#1f6feb}.ok{background:#1a7f37}.aviso-amarillo{background:#9a6700}.peligro{background:#d1242f}
        .cerrar{margin-left:auto;cursor:pointer;opacity:.8;background:none;border:0;color:#fff;font-size:16px}`;
      raizAviso.appendChild(estilo);
    }
    raizAviso.querySelectorAll(".aviso").forEach((n) => n.remove());
    const caja = document.createElement("div");
    caja.className = `aviso ${tipo === "aviso" ? "aviso-amarillo" : tipo}`;
    caja.setAttribute("role", "status");
    const icono = document.createElement("span");
    icono.textContent = "🛡️";
    const cuerpo = document.createElement("span");
    cuerpo.textContent = texto; // siempre texto, nunca HTML
    const cerrar = document.createElement("button");
    cerrar.className = "cerrar";
    cerrar.textContent = "×";
    cerrar.addEventListener("click", () => caja.remove());
    caja.append(icono, cuerpo, cerrar);
    raizAviso.appendChild(caja);
    clearTimeout(temporizador);
    temporizador = setTimeout(() => caja.remove(), segundos * 1000);
  }

  // ---------------------------------------------------------------- el cuadro de texto del chat
  function editable(nodo) {
    const el = nodo && nodo.nodeType === 1 ? nodo : nodo?.parentElement;
    if (!el) return null;
    const campo = el.closest("textarea, input[type=text], input[type=search], input:not([type])");
    if (campo) return campo;
    let actual = el;
    while (actual && actual !== document.documentElement) {
      if (actual.isContentEditable && (!actual.parentElement || !actual.parentElement.isContentEditable)) return actual;
      actual = actual.parentElement;
    }
    return null;
  }

  const esCampo = (el) => el.tagName === "TEXTAREA" || el.tagName === "INPUT";
  const textoDe = (el) => (esCampo(el) ? el.value : el.innerText);

  function insertar(el, texto) {
    el.focus();
    // execCommand es antiguo pero es lo que entienden los editores de los chatbots (y deja deshacer con Ctrl+Z)
    if (document.execCommand("insertText", false, texto)) return;
    if (esCampo(el)) {
      el.setRangeText(texto, el.selectionStart, el.selectionEnd, "end");
      el.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: texto }));
    }
  }

  function reemplazarTodo(el, texto) {
    el.focus();
    if (esCampo(el)) {
      el.select();
    } else {
      const rango = document.createRange();
      rango.selectNodeContents(el);
      const seleccion = window.getSelection();
      seleccion.removeAllRanges();
      seleccion.addRange(rango);
    }
    insertar(el, texto);
  }

  const revisados = new WeakMap(); // cuadro -> texto ya revisado (para no revisarlo dos veces)
  const marcarRevisado = (el) => revisados.set(el, G.normalizar(textoDe(el)));
  const yaRevisado = (el) => revisados.get(el) === G.normalizar(textoDe(el));

  function contarDatos(datos) {
    return Object.entries(datos || {}).map(([tipo, n]) => `${n} ${tipo}`).join(", ");
  }

  function avisarAduana(aduana) {
    if (!aduana) return false;
    const motivo = aduana.motivos && aduana.motivos[0] ? ` ${aduana.motivos[0]}` : "";
    avisar(`Ojo: lo que has pegado podría esconder órdenes para la IA (riesgo ${aduana.nivel}).${motivo} ` +
      "He quitado lo que no se ve; revísalo antes de enviarlo.", aduana.nivel === "ALTO" ? "peligro" : "aviso", 12);
    return true;
  }

  function sinServicio(texto, error, accion) {
    const tipos = G.sospechas(texto);
    if (!configurada) {
      avisar("Guardián sin configurar: abre las opciones de la extensión y pega la clave del servicio.", "aviso");
    }
    if (tipos.length && opciones.bloquearSinServicio) {
      avisar(`No he ${accion}: parece llevar ${tipos.join(", ")} y no se ha podido tapar. ${error}`, "peligro", 12);
      return false; // no dejar pasar
    }
    if (tipos.length) avisar(`Cuidado: parece llevar ${tipos.join(", ")} y no se ha podido tapar. ${error}`, "aviso", 10);
    return true;
  }

  // ---------------------------------------------------------------- 1. al pegar
  document.addEventListener("paste", async (evento) => {
    if (!opciones.alPegar) return;
    const el = editable(evento.target);
    const texto = evento.clipboardData && evento.clipboardData.getData("text/plain");
    if (!el || !texto || !texto.trim()) return; // imágenes, archivos...: el chatbot lo gestiona
    evento.preventDefault(); // hay que pararlo YA, antes de esperar al servicio
    evento.stopImmediatePropagation();
    const r = await pedir({ tipo: "proteger", texto, pegado: true }); // lo pegado se recuerda para ver ecos de trampas
    if (r.ok) {
      insertar(el, r.protegido);
      if (!avisarAduana(r.aduana)) {
        if (r.resumen) avisar(`He tapado ${r.resumen} antes de pegar. La IA solo verá marcadores como [DNI_1].`, "ok");
      }
      for (const aviso of r.avisos || []) avisar(aviso, "aviso");
      return;
    }
    if (sinServicio(texto, r.error, "pegado el texto")) insertar(el, texto);
  }, true);

  // ---------------------------------------------------------------- 2. antes de enviar
  async function revisarAntesDeEnviar(evento, el) {
    const texto = textoDe(el);
    if (!texto.trim() || yaRevisado(el)) return; // ya revisado: se envía
    if (!opciones.revisarTodo && G.sospechas(texto).length === 0) return; // nada raro a simple vista
    evento.preventDefault();
    evento.stopImmediatePropagation();
    const r = await pedir({ tipo: "proteger", texto });
    if (r.ok) {
      if (G.normalizar(r.protegido) !== G.normalizar(texto)) {
        reemplazarTodo(el, r.protegido);
        avisarAduana(r.aduana) ||
          avisar(`He tapado ${r.resumen || "datos"} en tu mensaje. Revísalo y vuelve a enviarlo.`, "ok", 9);
      } else {
        avisar("No hay datos que tapar. Vuelve a enviarlo.", "info", 5);
      }
      marcarRevisado(el);
      return;
    }
    if (sinServicio(texto, r.error, "enviado el mensaje")) {
      marcarRevisado(el);
      avisar("Vuelve a enviarlo si quieres mandarlo así.", "aviso", 8);
    }
  }

  document.addEventListener("keydown", (evento) => {
    if (!opciones.antesDeEnviar || evento.key !== "Enter" || evento.shiftKey || evento.isComposing) return;
    const el = editable(evento.target);
    if (el) revisarAntesDeEnviar(evento, el);
  }, true);

  const BOTON_ENVIAR = 'button[data-testid="send-button"], button[aria-label*="Send" i], ' +
    'button[aria-label*="Enviar" i], button[aria-label*="Submit" i], button[type="submit"]';
  document.addEventListener("click", (evento) => {
    if (!opciones.antesDeEnviar) return;
    const boton = evento.target instanceof Element && evento.target.closest(BOTON_ENVIAR);
    if (!boton) return;
    const formulario = boton.closest("form") || document;
    const el = editable(document.activeElement) ||
      [...formulario.querySelectorAll("textarea, [contenteditable=true], [contenteditable='']")].find(
        (c) => c.offsetParent !== null);
    if (el) revisarAntesDeEnviar(evento, el);
  }, true);

  // ---------------------------------------------------------------- 3. la respuesta de la IA
  const SELECTORES_RESPUESTA = [
    '[data-message-author-role="assistant"]', // ChatGPT
    '.font-claude-response', '[data-testid="assistant-message"]', '.font-claude-message', // Claude
    "model-response message-content", "message-content", ".model-response-text", // Gemini
    ".ds-markdown", // DeepSeek
    ".guardian-demo-respuesta", // página de prueba de la extensión
  ];

  function ultimaRespuesta() {
    for (const selector of SELECTORES_RESPUESTA) {
      const nodos = document.querySelectorAll(selector);
      if (nodos.length) return nodos[nodos.length - 1].innerText || "";
    }
    return "";
  }

  // Cuando la IA termina de escribir (el texto deja de cambiar) y trae marcadores, se manda al panel
  let ultimaVista = "";
  let ultimaEnviada = "";
  setInterval(async () => {
    const texto = ultimaRespuesta();
    if (!texto || texto !== ultimaVista) { ultimaVista = texto; return; } // aún está escribiendo
    if (texto === ultimaEnviada) return;
    ultimaEnviada = texto;
    // Se revisa en tu PC (comandos peligrosos, enlaces falsos...) y, si trae marcadores, se restaura para el panel
    const r = await pedir({ tipo: "respuesta", texto });
    if (!r.ok) return;
    if (r.nivel === "PELIGRO") {
      avisar("La respuesta de la IA trae algo peligroso (mira el panel del Guardián). No copies comandos ni " +
        "abras enlaces sin comprobarlos.", "peligro", 14);
    } else if (G.MARCADOR.test(texto)) {
      avisar("La respuesta usa tus datos tapados. Ábrela en el panel del Guardián (icono de la extensión) para " +
        "leerla con tus datos reales.", "info", 9);
    }
  }, 1500);

  // El panel pide la última respuesta. En las webs de chatbots llega solo a esta pestaña; en la página de prueba
  // (que es de la propia extensión) llega a todas sus páginas, así que cada una mira si la pregunta es para ella.
  let miPestana = null;
  if (chrome.tabs && chrome.tabs.getCurrent) chrome.tabs.getCurrent((t) => { miPestana = t ? t.id : null; });
  chrome.runtime.onMessage.addListener((mensaje, remitente, responder) => {
    if (remitente.id !== chrome.runtime.id || mensaje?.tipo !== "ultima_respuesta") return false;
    if (miPestana !== null && mensaje.tabId !== undefined && mensaje.tabId !== miPestana) return false;
    responder({ ok: true, texto: ultimaRespuesta() });
    return false;
  });
})();
