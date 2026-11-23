"use strict";

const CAMPOS = ["alPegar", "antesDeEnviar", "revisarTodo", "bloquearSinServicio"];
const POR_DEFECTO = { puerto: 8788, clave: "", alPegar: true, antesDeEnviar: true, revisarTodo: false,
  bloquearSinServicio: true };
const $ = (id) => document.getElementById(id);

async function cargar() {
  const o = { ...POR_DEFECTO, ...(await chrome.storage.local.get(Object.keys(POR_DEFECTO))) };
  $("clave").value = o.clave;
  $("puerto").value = o.puerto;
  for (const campo of CAMPOS) $(campo).checked = Boolean(o[campo]);
}

async function guardar() {
  const datos = { clave: $("clave").value.trim(), puerto: Number($("puerto").value) || 8788 };
  for (const campo of CAMPOS) datos[campo] = $(campo).checked;
  await chrome.storage.local.set(datos);
}

$("guardar").addEventListener("click", async () => {
  await guardar();
  $("resultado").textContent = "Probando…";
  chrome.runtime.sendMessage({ tipo: "salud" }, (r) => {
    $("resultado").textContent = r && r.ok
      ? `✓ Conectado al Guardián ${r.version} de tu PC`
      : `✗ ${(r && r.error) || "sin respuesta"}`;
  });
});
for (const campo of CAMPOS) $(campo).addEventListener("change", guardar);

cargar();
