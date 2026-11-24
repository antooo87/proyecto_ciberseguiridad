# Extensión del navegador del Guardián IA

Lleva el escudo y la aduana del Guardián a las webs de los chatbots (ChatGPT, Claude, Gemini, Copilot, DeepSeek,
Mistral, Perplexity, Qwen y Grok) sin cambiar nada de cómo usas la web:

1. **Al pegar** un texto en el chat, se pega ya con los datos tapados (`[DNI_1]`, `[IBAN_1]`...). Si el texto es
   largo, la aduana mira además si esconde órdenes para la IA y quita lo que no se ve.
2. **Antes de enviar** (Enter o el botón), si lo que has escrito parece llevar datos, se tapan y te deja revisarlo.
   Se envía al volver a pulsar.
3. **Cuando la IA contesta**, la respuesta se revisa en tu PC (comandos peligrosos, enlaces falsos...) y en el panel
   lateral de la extensión la ves con tus datos reales. La web del chatbot nunca ve esos datos.
4. **«✨ Mejorar»** (botón encima del cuadro del chat, o `Alt+M`): te dice qué le falta a tu pregunta y te propone dos
   versiones más claras, Directa y Completa. Al elegir una, sustituye lo que habías escrito y deja seleccionado el
   hueco «escribe aquí...» para que escribas encima. Tus datos se tapan antes de nada.
5. **«Guardián: ¿es una estafa?»**: selecciona cualquier texto en cualquier web (un correo en Gmail, un WhatsApp
   Web, un SMS copiado...) y, con el clic derecho, el panel lateral te dice si tiene las pistas de una estafa, cuál
   parece y qué hacer.

La extensión no tapa nada por sí misma: se lo pide al Guardián de tu PC (`python -m guardian servicio`), que es donde
están las reglas, la bóveda y la IA local. Así tus datos no salen del ordenador.

## Instalarla (2 minutos)

1. Arranca el servicio en tu PC, dentro de la carpeta `guardian_ia` y con el entorno activado:
   `python -m guardian servicio` (añade `--ia` si quieres que tape también nombres y direcciones con la IA local).
   Copia la clave que sale en la ventana.
2. En Chrome o Edge abre `chrome://extensions` (en Edge, `edge://extensions`).
3. Activa el **Modo de desarrollador** (arriba a la derecha).
4. Pulsa **Cargar descomprimida** y elige esta carpeta (`guardian_ia/extension`).
5. Se abren las opciones: pega la clave y pulsa **Guardar y probar**. Debe salir «Conectado».

Para probarla sin cuenta ni Internet: icono de la extensión → **Página de prueba**. Es un chat de mentira con cuatro
textos de ejemplo: datos personales, una factura con trampa, una petición de «arreglo» que la IA contesta con un
comando peligroso y un correo falso del «banco» cuya orden la IA repite (el Guardián avisa del eco de la trampa).

Con el instalador de Windows (`instalar.ps1`) el servicio se arranca con `.\guardian servicio`, sin activar nada.
En el panel lateral, «Esta semana» resume lo que ha hecho el Guardián (sin enseñar ningún dato).

## Por qué es segura

- Solo habla con `127.0.0.1` (tu PC). El servicio no acepta peticiones de páginas web (mira el `Origin`), comprueba
  el `Host` (contra el *DNS rebinding*) y pide una clave en cada petición.
- La clave solo la tiene el trabajador de fondo de la extensión. Las webs de los chatbots nunca la ven.
- Tus datos reales solo se enseñan en el panel lateral, que es de la extensión: la web del chatbot no lo puede leer.
  Los avisos y las propuestas de «✨ Mejorar» van dentro de un *shadow root* cerrado y se escriben siempre como texto.
- Si el servicio está apagado y el texto parece llevar datos, no se pega ni se envía (se puede cambiar en opciones).
  Para decidirlo sin el servicio hay un primer filtro en el navegador (`comun.js`) que comprueba la letra del DNI,
  el control del IBAN y el algoritmo de Luhn de las tarjetas.
- Permisos mínimos: `storage`, `sidePanel`, `contextMenus` y `activeTab`. No pide leer tu historial.

## Limitaciones (para ser honestos)

- Solo protege **texto**. Si subes un PDF o una imagen al chatbot, usa antes `python -m guardian anonimizar`.
- Las webs de los chatbots cambian a menudo. Si una cambia su HTML, puede dejar de encontrarse la respuesta de la IA;
  entonces selecciona el texto y usa el clic derecho → «Guardián: ver con mis datos».
- Sin `--ia` solo se tapan los datos con forma fija (DNI, IBAN, tarjeta, correo, teléfono, claves...). Los nombres y
  direcciones necesitan la IA local.
- Probada en Chromium (Chrome y Edge usan el mismo motor). En Firefox no está probada.

## Pruebas

- `node extension/pruebas/comun.test.js`: el primer filtro del navegador. No necesita instalar nada.
- `node extension/pruebas/e2e.js`: abre un Chromium de verdad con la extensión y el servicio y hace lo que haría una
  persona. Antes: `npm install --no-save playwright` y `npx playwright install chromium`.
  Con `CAPTURAS=carpeta` guarda capturas de pantalla.

Las dos se ejecutan en GitHub en cada cambio.
