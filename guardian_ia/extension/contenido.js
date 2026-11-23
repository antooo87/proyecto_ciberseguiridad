// Guardián IA · script de la página del chatbot (chatgpt.com, claude.ai, gemini...).
//
//  1. Al PEGAR un texto en el cuadro del chat, se lo pasa al Guardián de tu PC y pega la versión con los datos
//     tapados ([DNI_1]...). Si el texto es largo, la aduana mira además si esconde órdenes para la IA.
//  2. Antes de ENVIAR (Enter o botón), si el mensaje parece llevar datos, lo tapa y te deja revisarlo.
//  3. Cuando la IA contesta, manda la respuesta al panel de la extensión, que la enseña con tus datos reales.
//     Tus datos reales NUNCA se escriben en la página: la web del chatbot no los puede leer.
//  4. «✨ Mejorar» (o Alt+M): te dice qué le falta a tu pregunta y te propone dos versiones mejores. Las hace el
//     Guardián de tu PC, con tus datos ya tapados; la página no ve nada hasta que eliges una con «Usar esta».
(() => {
  "use strict";
  if (window.__guardianIA) return;
  window.__guardianIA = true;

  const G = window.GuardianComun;
  let opciones = { alPegar: true, antesDeEnviar: true, revisarTodo: false, bloquearSinServicio: true,
    mejorarPregunta: true };
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

  // ---------------------------------------------------------------- 4. mejorar mi pregunta
  // Un botón «✨ Mejorar» encima del cuadro del chat. Todo va dentro de un shadow root cerrado (como los avisos):
  // la web no puede leer las propuestas ni cambiarles el estilo. Solo la que elijas se escribe en el cuadro.
  let raizMejora = null;
  let anfitrionMejora = null;
  let campoMejora = null;
  let pidiendoMejora = false;
  const HUECO = /\(«(?:escribe|pega)[^»]*»\)|«(?:escribe|pega)[^»]*»/;
  const ESTILO_MEJORA = `
    :host{all:initial}
    *{box-sizing:border-box}
    .boton{position:fixed;font:600 12px/1 system-ui,-apple-system,"Segoe UI",sans-serif;background:#6e40c9;color:#fff;
      border:0;border-radius:999px;padding:7px 11px;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.25)}
    .boton:hover{background:#8250df}
    .caja{position:fixed;width:min(540px,calc(100vw - 32px));max-height:min(72vh,680px);overflow:auto;background:#fff;
      color:#1f2328;border:1px solid #d1d9e0;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.28);
      font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;padding:14px 16px}
    .cabecera{display:flex;align-items:center;gap:8px;margin-bottom:6px}
    .titulo{font-weight:700;font-size:15px}
    .nota{margin-left:auto;font-weight:700;font-size:12px;border-radius:999px;padding:3px 10px;color:#fff}
    .alta{background:#1a7f37}.media{background:#9a6700}.baja{background:#d1242f}
    .cerrar{background:none;border:0;font-size:20px;line-height:1;cursor:pointer;color:inherit;opacity:.7;padding:0 4px}
    .sub{font-weight:600;margin:8px 0 2px}
    ul{margin:2px 0 6px;padding-left:20px}li{margin:3px 0}
    .ojo{background:#fff8c5;color:#4d2d00;border-radius:8px;padding:8px 10px;margin:6px 0;list-style:none;margin-left:-20px}
    .opcion{border:1px solid #d1d9e0;border-radius:10px;padding:10px 12px;margin-top:10px}
    .opcion h3{margin:0 0 2px;font-size:14px}
    .por-que{font-size:12px;opacity:.75;margin-bottom:6px}
    .texto{white-space:pre-wrap;word-break:break-word;max-height:160px;overflow:auto;font-size:13px;
      background:rgba(127,127,127,.09);border-radius:8px;padding:8px 10px}
    .usar{margin-top:8px;background:#1f6feb;color:#fff;border:0;border-radius:6px;padding:7px 14px;
      font:600 13px system-ui,-apple-system,"Segoe UI",sans-serif;cursor:pointer}
    .usar:focus-visible,.boton:focus-visible,.cerrar:focus-visible{outline:2px solid #1f6feb;outline-offset:2px}
    .pie{margin-top:10px;font-size:12px;opacity:.75}
    .error{background:#ffebe9;color:#82071e;border-radius:8px;padding:8px 10px}
    @media (prefers-color-scheme:dark){
      .caja{background:#161b22;color:#e6edf3;border-color:#3d444d}.opcion{border-color:#3d444d}
      .ojo{background:#3b2e00;color:#f2cc60}.error{background:#3c0b0b;color:#ffa198}}`;

  function nodo(etiqueta, clase, texto) {
    const n = document.createElement(etiqueta);
    if (clase) n.className = clase;
    if (texto !== undefined) n.textContent = texto; // siempre texto, nunca HTML
    return n;
  }

  function montarMejora() {
    if (raizMejora) return;
    anfitrionMejora = document.createElement("div");
    anfitrionMejora.style.cssText = "position:fixed;z-index:2147483646;top:0;left:0;width:0;height:0;";
    document.documentElement.appendChild(anfitrionMejora);
    raizMejora = anfitrionMejora.attachShadow({ mode: "closed" });
    const boton = nodo("button", "boton", "✨ Mejorar");
    boton.title = "Mejorar mi pregunta (Alt+M): qué le falta y dos versiones más claras, hechas en tu PC";
    boton.hidden = true;
    boton.addEventListener("mousedown", (e) => e.preventDefault()); // que el cuadro del chat no pierda el foco
    boton.addEventListener("click", () => abrirMejora(campoMejora));
    const caja = nodo("div", "caja");
    caja.hidden = true;
    caja.setAttribute("role", "dialog");
    caja.setAttribute("aria-label", "Mejorar mi pregunta");
    caja.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarMejora(); });
    raizMejora.append(nodo("style", "", ESTILO_MEJORA), boton, caja);
  }

  const cajaAbierta = () => Boolean(raizMejora && !raizMejora.querySelector(".caja").hidden);

  function colocarBoton() {
    if (!opciones.mejorarPregunta || cajaAbierta()) {
      if (raizMejora) raizMejora.querySelector(".boton").hidden = true;
      return;
    }
    const el = campoMejora;
    const activo = el && el.isConnected && editable(document.activeElement) === el;
    const palabras = activo ? textoDe(el).trim().split(/\s+/).filter(Boolean).length : 0;
    if (!activo || palabras < 3) {
      if (raizMejora) raizMejora.querySelector(".boton").hidden = true;
      return;
    }
    montarMejora();
    const boton = raizMejora.querySelector(".boton");
    boton.hidden = false;
    const r = el.getBoundingClientRect();
    const ancho = boton.offsetWidth || 96;
    const arriba = r.top - 34;
    boton.style.top = `${arriba >= 4 ? arriba : Math.min(r.bottom + 6, window.innerHeight - 34)}px`;
    boton.style.left = `${Math.max(8, Math.min(r.right - ancho - 6, window.innerWidth - ancho - 8))}px`;
  }

  function vigilarCampo() {
    const el = editable(document.activeElement);
    if (el) campoMejora = el;
    colocarBoton();
  }
  document.addEventListener("focusin", vigilarCampo, true);
  document.addEventListener("input", () => requestAnimationFrame(vigilarCampo), true);
  document.addEventListener("focusout", () => setTimeout(colocarBoton, 120), true);
  window.addEventListener("resize", () => { colocarBoton(); if (cajaAbierta()) colocarCaja(); });
  window.addEventListener("scroll", colocarBoton, true);

  function colocarCaja() {
    const caja = raizMejora.querySelector(".caja");
    caja.hidden = false;
    raizMejora.querySelector(".boton").hidden = true;
    const r = (campoMejora && campoMejora.isConnected ? campoMejora : document.body).getBoundingClientRect();
    const ancho = caja.offsetWidth;
    const alto = caja.offsetHeight;
    const encima = r.top - alto - 10;
    const top = encima >= 8 ? encima : Math.min(r.bottom + 10, window.innerHeight - alto - 8);
    caja.style.top = `${Math.max(8, top)}px`;
    caja.style.left = `${Math.max(16, Math.min(r.right - ancho, window.innerWidth - ancho - 16))}px`;
  }

  function pintarCaja(r) {
    const caja = raizMejora.querySelector(".caja");
    caja.replaceChildren();
    const cabecera = nodo("div", "cabecera");
    cabecera.append(nodo("span", "titulo", "✨ Mejorar mi pregunta"));
    if (r.ok && typeof r.nota === "number") {
      const nota = nodo("span", `nota ${r.nota >= 80 ? "alta" : r.nota >= 50 ? "media" : "baja"}`, `Nota ${r.nota}/100`);
      nota.title = "Lo clara que es tu pregunta para una IA";
      cabecera.append(nota);
    }
    const cerrar = nodo("button", "cerrar", "×");
    cerrar.setAttribute("aria-label", "Cerrar");
    if (!(r.ok && typeof r.nota === "number")) cerrar.style.marginLeft = "auto";
    cerrar.addEventListener("click", cerrarMejora);
    cabecera.append(cerrar);
    caja.append(cabecera);
    if (r.cargando) {
      caja.append(nodo("div", "pie", "Mirando tu pregunta en el Guardián de tu PC…"));
      return;
    }
    if (!r.ok) {
      caja.append(nodo("div", "error", r.error || "El Guardián de tu PC no responde."));
      return;
    }
    const consejos = Array.isArray(r.consejos) ? r.consejos : [];
    if (consejos.length) {
      caja.append(nodo("div", "sub", "Qué le falta a tu pregunta"));
      const lista = nodo("ul");
      for (const c of consejos) lista.append(nodo("li", String(c).startsWith("Ojo:") ? "ojo" : "", String(c)));
      caja.append(lista);
    } else {
      caja.append(nodo("div", "pie", "Tu pregunta ya está muy bien. Aun así, aquí tienes dos versiones:"));
    }
    (Array.isArray(r.versiones) ? r.versiones : []).slice(0, 2).forEach((v, i) => {
      const opcion = nodo("div", "opcion");
      const usar = nodo("button", "usar", "Usar esta");
      usar.addEventListener("click", () => usarVersion(String(v.texto || "")));
      opcion.append(nodo("h3", "", `Opción ${i + 1} · ${v.titulo}`), nodo("div", "por-que", String(v.por_que || "")),
        nodo("div", "texto", String(v.texto || "")), usar);
      caja.append(opcion);
    });
    const tapados = Object.values(r.datos_tapados || {}).reduce((a, b) => a + b, 0);
    caja.append(nodo("div", "pie", `${r.con_ia ? "Reescritas por la IA de tu PC" : "Hechas con reglas en tu PC"}` +
      `${tapados ? ` · ${tapados === 1 ? "1 dato tapado" : `${tapados} datos tapados`} ([DNI_1]...)` : ""}` +
      " · Esc para cerrar · Alt+M para volver a abrirlo"));
  }

  async function abrirMejora(el) {
    if (!el || pidiendoMejora) return;
    const texto = textoDe(el);
    if (!texto.trim()) {
      avisar("Escribe primero tu pregunta y después pulsa «✨ Mejorar» (o Alt+M).", "info", 5);
      return;
    }
    montarMejora();
    campoMejora = el;
    pintarCaja({ cargando: true });
    colocarCaja();
    pidiendoMejora = true;
    const r = await pedir({ tipo: "mejorar", texto });
    pidiendoMejora = false;
    if (!cajaAbierta()) return; // la han cerrado mientras esperaba
    pintarCaja(r);
    colocarCaja();
    const primera = raizMejora.querySelector(".usar") || raizMejora.querySelector(".cerrar");
    if (primera) primera.focus(); // se puede elegir con el teclado: Enter, Tab, Esc
  }

  function cerrarMejora(devolverFoco = true) {
    if (!raizMejora) return;
    raizMejora.querySelector(".caja").hidden = true;
    if (devolverFoco === true && campoMejora && campoMejora.isConnected) campoMejora.focus();
    colocarBoton();
  }

  // Deja seleccionado el hueco «escribe aquí...»: lo que escribas lo sustituye
  function seleccionarHueco(el) {
    if (esCampo(el)) {
      const m = HUECO.exec(el.value);
      if (m) el.setSelectionRange(m.index, m.index + m[0].length);
      return Boolean(m);
    }
    const recorrido = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = recorrido.nextNode(); n; n = recorrido.nextNode()) {
      const m = HUECO.exec(n.data);
      if (!m) continue;
      const rango = document.createRange();
      rango.setStart(n, m.index);
      rango.setEnd(n, m.index + m[0].length);
      const seleccion = window.getSelection();
      seleccion.removeAllRanges();
      seleccion.addRange(rango);
      return true;
    }
    return false;
  }

  function usarVersion(texto) {
    const el = campoMejora;
    cerrarMejora();
    if (!el || !el.isConnected || !texto) return;
    reemplazarTodo(el, texto);
    marcarRevisado(el); // ya viene con los datos tapados por el Guardián
    if (seleccionarHueco(el)) avisar("Escribe lo que falta (ya está seleccionado) y envíala.", "info", 8);
    else avisar("Listo: repásala y envíala.", "ok", 4);
  }

  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && cajaAbierta()) {
      cerrarMejora();
      return;
    }
    if (!opciones.mejorarPregunta || !evento.altKey || evento.ctrlKey || evento.metaKey || evento.code !== "KeyM") return;
    const el = editable(evento.target);
    if (!el) return;
    evento.preventDefault();
    evento.stopImmediatePropagation();
    abrirMejora(el);
  }, true);

  // Un clic fuera la cierra (dentro del shadow root el clic llega con el anfitrión como destino)
  document.addEventListener("mousedown", (evento) => {
    if (cajaAbierta() && evento.target !== anfitrionMejora) cerrarMejora(false);
  }, true);

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
