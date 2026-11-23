// Prueba automática de la extensión, de punta a punta, en un Chromium de verdad:
//   arranca el servicio del Guardián con una clave de prueba, carga la extensión y hace lo que haría una persona
//   (pegar datos, enviar, pegar un documento con trampa, pedir un "arreglo"...) en la página de prueba.
//
// Uso (desde la carpeta guardian_ia, con el entorno de Python activado):
//   npm install --no-save playwright && npx playwright install chromium
//   node extension/pruebas/e2e.js            (CAPTURAS=carpeta para guardar capturas de pantalla)
"use strict";
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

const EXT = path.resolve(__dirname, "..");
const RAIZ = path.resolve(EXT, "..");
const CLAVE = crypto.randomBytes(18).toString("base64url");
const PUERTO = Number(process.env.PUERTO || 8799);
const CAPTURAS = process.env.CAPTURAS || "";
const TEMPORAL = fs.mkdtempSync(path.join(os.tmpdir(), "guardian-e2e-"));
if (CAPTURAS) fs.mkdirSync(CAPTURAS, { recursive: true });
const captura = (pagina, nombre, extra = {}) =>
  CAPTURAS ? pagina.screenshot({ path: path.join(CAPTURAS, nombre), ...extra }) : Promise.resolve();

function arrancarServicio() {
  const python = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  const hijo = spawn(python, ["-m", "guardian", "servicio", "--puerto", String(PUERTO), "--clave", CLAVE,
    "--ocultar-clave"], { cwd: RAIZ, env: { ...process.env, HOME: TEMPORAL, USERPROFILE: TEMPORAL,
      GUARDIAN_REGISTRO: path.join(TEMPORAL, "registro") }, // no mezclar la prueba con tu actividad real
    stdio: ["ignore", "pipe", "pipe"] });
  hijo.stderr.on("data", (d) => process.stderr.write(`[servicio] ${d}`));
  return hijo;
}

async function esperarServicio() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PUERTO}/salud`, { headers: { Authorization: `Bearer ${CLAVE}` } });
      if (r.ok) return;
    } catch (e) { /* aún arrancando */ }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("El servicio del Guardián no ha arrancado");
}

let servicio = null;
const fallos = [];

// Lo mismo que pasa al pulsar Ctrl+V: un evento "paste" con el texto del portapapeles
function pegar(pagina, texto) {
  return pagina.evaluate((t) => {
    const dt = new DataTransfer();
    dt.setData("text/plain", t);
    document.getElementById("compositor").dispatchEvent(
      new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
  }, texto);
}
function comprobar(cond, texto) {
  console.log(`${cond ? "OK  " : "FALLO"} ${texto}`);
  if (!cond) fallos.push(texto);
}

(async () => {
  servicio = arrancarServicio();
  await esperarServicio();
  const perfil = fs.mkdtempSync(path.join(TEMPORAL, "perfil-"));
  const contexto = await chromium.launchPersistentContext(perfil, {
    channel: "chromium",
    headless: true,
    viewport: { width: 1100, height: 900 },
    deviceScaleFactor: CAPTURAS ? 2 : 1, // capturas nítidas para la memoria
    args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`],
  });
  let [sw] = contexto.serviceWorkers();
  if (!sw) sw = await contexto.waitForEvent("serviceworker");
  const id = sw.url().split("/")[2];
  console.log("extensión", id);

  // Se abre sola la página de opciones al instalar
  await new Promise((r) => setTimeout(r, 1000));
  const paginas = contexto.pages().map((p) => p.url());
  comprobar(paginas.some((u) => u.endsWith("/opciones.html")), "al instalar se abren las opciones");

  // Opciones: pegar la clave y probar
  const opc = contexto.pages().find((p) => p.url().endsWith("/opciones.html")) || (await contexto.newPage());
  if (!opc.url().endsWith("/opciones.html")) await opc.goto(`chrome-extension://${id}/opciones.html`);
  opc.on("pageerror", (e) => console.log("[opciones error]", e.message));
  await opc.fill("#clave", CLAVE);
  await opc.fill("#puerto", String(PUERTO));
  await opc.click("#guardar");
  await opc.waitForFunction(() => document.getElementById("resultado").textContent.includes("Conectado"), null,
    { timeout: 5000 }).catch(() => {});
  const resultado = await opc.textContent("#resultado");
  comprobar(resultado.includes("Conectado"), `opciones → ${resultado}`);
  await captura(opc, "ext_opciones.png", { fullPage: true });

  // Página de prueba
  const page = await contexto.newPage();
  page.on("pageerror", (e) => console.log("[prueba error]", e.message));
  await page.goto(`chrome-extension://${id}/prueba.html`);
  await page.waitForTimeout(500);

  const datos = await page.textContent("#ejemplo-datos");
  await page.focus("#compositor");
  await pegar(page, datos);
  await page.waitForFunction(() => document.getElementById("compositor").innerText.includes("["), null,
    { timeout: 5000 }).catch(() => {});
  const pegado = await page.innerText("#compositor");
  console.log("pegado:", pegado);
  comprobar(pegado.includes("[DNI_1]") && pegado.includes("[IBAN_1]") && pegado.includes("[TARJETA_1]"),
    "al pegar se tapan DNI, IBAN y tarjeta");
  comprobar(!pegado.includes("12345678Z") && !pegado.includes("lucia.moreno@gmail.com"),
    "los datos reales no llegan al cuadro del chat");
  await captura(page, "ext_pegado.png");

  // Enviar con Enter: ya no lleva datos, se envía a la primera
  await page.press("#compositor", "Enter");
  await page.waitForTimeout(800);
  const burbujas = await page.$$eval(".burbuja.tu div:not(.quien)", (ns) => ns.map((n) => n.textContent));
  comprobar(burbujas.length === 1 && burbujas[0].includes("[DNI_1]"), "el mensaje enviado lleva solo marcadores");

  // La respuesta de la IA llega al panel con los datos reales (sesión de la extensión)
  const tabId = await page.evaluate(() => new Promise((r) => chrome.tabs.getCurrent((t) => r(t.id))));
  let ultima = null;
  for (let i = 0; i < 20 && !(ultima && ultima.texto); i++) {
    await page.waitForTimeout(500);
    ultima = await sw.evaluate(async (k) => (await chrome.storage.session.get(k))[k], `ultima_${tabId}`);
  }
  console.log("ultima:", JSON.stringify(ultima));
  comprobar(ultima && ultima.texto.includes("12345678Z"), "el panel recibe la respuesta con el DNI real");
  const respuestaPagina = await page.$$eval(".burbuja.ia div:not(.quien)", (ns) => ns.map((n) => n.textContent).join("\n"));
  comprobar(!respuestaPagina.includes("12345678Z"), "la página del chat sigue sin ver el DNI real");

  // Mensaje escrito a mano con datos: se revisa antes de enviar
  await page.focus("#compositor");
  await page.keyboard.type("Mi teléfono es 612 345 678, llámame");
  await page.press("#compositor", "Enter");
  await page.waitForTimeout(800);
  const escrito = await page.innerText("#compositor");
  console.log("escrito:", escrito);
  comprobar(escrito.includes("[TELEFONO_1]"), "antes de enviar se tapa el teléfono escrito a mano");
  const enviadas = await page.$$eval(".burbuja.tu", (ns) => ns.length);
  comprobar(enviadas === 1, "no se envía hasta que lo revisas");
  await page.press("#compositor", "Enter");
  await page.waitForTimeout(500);
  comprobar((await page.$$eval(".burbuja.tu", (ns) => ns.length)) === 2, "al volver a pulsar Enter se envía");

  // Documento con trampa: la aduana avisa y quita el comentario escondido
  await page.waitForTimeout(1500);
  const trampa = await page.textContent("#ejemplo-trampa");
  await page.focus("#compositor");
  await pegar(page, trampa);
  await page.waitForTimeout(1000);
  const pegadoTrampa = await page.innerText("#compositor");
  console.log("trampa pegada:", pegadoTrampa);
  comprobar(!pegadoTrampa.includes("evil.example"), "la orden escondida de la factura no se pega");
  await captura(page, "ext_trampa.png");
  await page.evaluate(() => { document.getElementById("compositor").textContent = ""; });

  // Pedir un "arreglo": la respuesta peligrosa se marca
  await page.focus("#compositor");
  await page.keyboard.type("Me sale un error en Windows, ¿me das un comando para arreglarlo?");
  await page.press("#compositor", "Enter");
  let peligro = null;
  for (let i = 0; i < 20; i++) {
    await page.waitForTimeout(500);
    peligro = await sw.evaluate(async (k) => (await chrome.storage.session.get(k))[k], `ultima_${tabId}`);
    if (peligro && peligro.nivel === "PELIGRO") break;
  }
  console.log("peligro:", JSON.stringify(peligro));
  comprobar(peligro && peligro.nivel === "PELIGRO", "la respuesta con irm | iex se marca como PELIGRO");
  await page.waitForTimeout(300);
  await captura(page, "ext_peligro.png");

  // Un correo de phishing pegado: la IA de mentira se lo cree y lo repite. El Guardián avisa del "eco" de la trampa
  await page.evaluate(() => { document.getElementById("compositor").textContent = ""; });
  await page.focus("#compositor");
  await pegar(page, await page.textContent("#ejemplo-banco"));
  await page.waitForTimeout(800);
  await page.press("#compositor", "Enter");
  let eco = null;
  for (let i = 0; i < 20; i++) {
    await page.waitForTimeout(500);
    eco = await sw.evaluate(async (k) => (await chrome.storage.session.get(k))[k], `ultima_${tabId}`);
    if (eco && (eco.texto || "").includes("Según el correo")) break;
  }
  comprobar(eco && eco.nivel === "PELIGRO" && eco.hallazgos.some((h) => h.explicacion.includes("sale de lo que ha leído")),
    "la IA repite lo que pedía el correo pegado: el Guardián avisa del eco de la trampa");
  await captura(page, "ext_eco.png");

  // «✨ Mejorar» (Alt+M): una pregunta vaga se convierte en una clara, con el hueco del tema listo para escribir
  await page.evaluate(() => { document.getElementById("compositor").textContent = ""; });
  await page.focus("#compositor");
  await page.keyboard.type("hola, ¿qué tal estás? ¿Me podrías ayudar con este tema?");
  await page.waitForTimeout(300);
  await captura(page, "ext_mejorar_boton.png");
  await page.keyboard.press("Alt+KeyM");
  await page.waitForTimeout(1500);
  await captura(page, "ext_mejorar.png");
  await page.keyboard.press("Enter"); // el foco está en «Usar esta» de la primera opción
  await page.waitForTimeout(500);
  await page.keyboard.type("la ley de protección de datos en mi empresa");
  await page.waitForTimeout(300);
  const mejorada = await page.innerText("#compositor");
  console.log("mejorada:", mejorada.replace(/\n/g, " | "));
  comprobar(mejorada.startsWith("Ayúdame con la ley de protección de datos en mi empresa.") &&
    mejorada.includes("Ve al grano") && !/hola/i.test(mejorada),
    "Alt+M cambia la pregunta vaga por una clara y deja el hueco del tema listo para escribir");
  await page.press("#compositor", "Enter");
  await page.waitForTimeout(1200);
  const ultimaTu = await page.$$eval(".burbuja.tu div:not(.quien)", (ns) => ns[ns.length - 1].textContent);
  comprobar(ultimaTu.includes("Ve al grano"), "la pregunta mejorada se envía a la primera");

  // El panel (abierto como pestaña) enseña la última respuesta
  const panel = await contexto.newPage();
  panel.on("pageerror", (e) => console.log("[panel error]", e.message));
  await panel.goto(`chrome-extension://${id}/panel.html`);
  await panel.waitForTimeout(1500);
  console.log("panel estado:", await panel.textContent("#estado-texto"));
  const textoPanel = await panel.textContent("#texto");
  console.log("panel texto:", textoPanel.slice(0, 200));
  comprobar(textoPanel.includes("Según el correo") || textoPanel.includes("Perfecto, ahora sé"),
    "el panel abierto en pestaña enseña la última respuesta");
  const semana = await panel.textContent("#actividad");
  console.log("esta semana:", semana);
  comprobar(/\d+ datos? personal(es)? tapados?/.test(semana) && /respuestas? con peligro/.test(semana),
    "el panel enseña lo que ha hecho el Guardián esta semana (sin datos)");
  // Lo que hace el botón «Leer la última respuesta» con la página de prueba
  const porTabs = await panel.evaluate((t) => new Promise((r) => chrome.tabs.sendMessage(t, { tipo: "ultima_respuesta" },
    (x) => r(chrome.runtime.lastError ? "error: " + chrome.runtime.lastError.message : x))), tabId);
  console.log("tabs.sendMessage a la prueba:", JSON.stringify(porTabs).slice(0, 120));
  const porRuntime = await panel.evaluate((t) => new Promise((r) => chrome.runtime.sendMessage({ tipo: "ultima_respuesta", tabId: t },
    (x) => r(chrome.runtime.lastError ? { error: chrome.runtime.lastError.message } : x))), tabId);
  comprobar(porRuntime && porRuntime.ok && porRuntime.texto.includes("Perfecto, ahora sé"),
    "la página de prueba contesta al panel");
  const otra = await panel.evaluate(() => new Promise((r) => chrome.runtime.sendMessage({ tipo: "ultima_respuesta", tabId: 1 },
    (x) => r(chrome.runtime.lastError ? { error: chrome.runtime.lastError.message } : x))));
  comprobar(!otra.ok, `si la pregunta es para otra pestaña no contesta (${otra.error})`);
  await panel.setViewportSize({ width: 420, height: 900 });
  await captura(panel, "ext_panel.png", { fullPage: true });

  // Si el Guardián del PC se apaga, un texto con datos no pasa (falla "cerrado")
  servicio.kill();
  await page.waitForTimeout(500);
  await page.bringToFront();
  await page.evaluate(() => { document.getElementById("compositor").textContent = ""; });
  await page.focus("#compositor");
  await pegar(page, datos);
  await page.waitForTimeout(1000);
  comprobar(!(await page.innerText("#compositor")).includes("12345678Z"),
    "con el servicio apagado, un texto con datos no se pega");
  await captura(page, "ext_sin_servicio.png");
  await pegar(page, "Hola, ¿qué tiempo hace hoy en Madrid?");
  await page.waitForTimeout(1000);
  comprobar((await page.innerText("#compositor")).includes("qué tiempo"),
    "con el servicio apagado, un texto sin datos sí se pega");

  console.log(fallos.length ? `\n${fallos.length} FALLOS` : "\nTODO OK");
  await contexto.close();
  terminar(fallos.length ? 1 : 0);
})().catch((e) => { console.error(e); terminar(2); });

function terminar(codigo) {
  if (servicio) servicio.kill();
  fs.rmSync(TEMPORAL, { recursive: true, force: true });
  process.exit(codigo);
}
