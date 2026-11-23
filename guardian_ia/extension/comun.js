// Comprobación rápida en el navegador, SIN el servicio del PC.
// Sirve para dos cosas: decidir al momento si un mensaje merece revisarse antes de enviarlo
// y, si el Guardián de tu PC está apagado, no dejar pasar a ciegas un texto con datos.
// Las reglas completas (y la IA local) están en el servicio: esto es solo un primer filtro.
(() => {
  "use strict";
  const LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE";

  function dniValido(numero, letra) {
    return LETRAS_DNI[parseInt(numero, 10) % 23] === letra.toUpperCase();
  }

  function ibanValido(iban) {
    const limpio = iban.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    if (limpio.length < 15 || limpio.length > 34) return false;
    const reordenado = limpio.slice(4) + limpio.slice(0, 4);
    let resto = 0;
    for (const c of reordenado) {
      const valor = parseInt(c, 36);
      if (Number.isNaN(valor)) return false;
      for (const d of String(valor)) resto = (resto * 10 + Number(d)) % 97;
    }
    return resto === 1;
  }

  // Como en el Guardián de Python: si "ES91 ... 1332 y" no valida, se prueba quitando bloques del final
  function ibanRecortado(trozo) {
    let partes = trozo.split(/([ -])/);
    while (partes.length) {
      if (ibanValido(partes.join(""))) return true;
      if (partes.length <= 2) return false;
      partes = partes.slice(0, -2);
    }
    return false;
  }

  function luhnValido(numero) {
    const digitos = numero.replace(/\D/g, "");
    if (digitos.length < 13 || digitos.length > 19 || /^(\d)\1+$/.test(digitos)) return false;
    let total = 0;
    [...digitos].reverse().forEach((c, i) => {
      let d = Number(c);
      if (i % 2 === 1) { d *= 2; if (d > 9) d -= 9; }
      total += d;
    });
    return total % 10 === 0;
  }

  const REGLAS = [
    ["DNI", /\b(\d{8})[ -]?([A-Za-z])\b/g, (m) => dniValido(m[1], m[2])],
    ["NIE", /\b([XYZxyz])[ -]?(\d{7})[ -]?([A-Za-z])\b/g,
      (m) => dniValido("XYZ".indexOf(m[1].toUpperCase()) + m[2], m[3])],
    ["IBAN", /\b[A-Za-z]{2}\d{2}(?:[ -]?[A-Za-z0-9]{4}){3,7}(?:[ -]?[A-Za-z0-9]{1,3})?\b/g, (m) => ibanRecortado(m[0])],
    ["TARJETA", /(?<!\d)(?:\d{4}[ -]?){3}\d{1,7}(?!\d)/g, (m) => luhnValido(m[0])],
    ["EMAIL", /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, () => true],
    ["TELEFONO", /(?<![\w+.-])(?:(?:\+|00)34[ .-]?)?[6789](?:[ .-]?\d){8}(?![.-]?\d)/g, () => true],
    ["CONTRASENA", /\b(?:contraseña|contrasena|password|passwd|pwd|clave|pin)\s*(?::|=|\bes\b|\bis\b)\s*\S{3,}/gi,
      () => true],
    ["CLAVE_API", /\b(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35}|xox[abprs]-[A-Za-z0-9-]{10,})/g,
      () => true],
  ];

  // Tipos de dato que parecen estar en el texto (sin decir cuáles)
  function sospechas(texto) {
    const tipos = new Set();
    for (const [tipo, patron, valido] of REGLAS) {
      patron.lastIndex = 0;
      for (const m of texto.matchAll(patron)) {
        if (valido(m)) { tipos.add(tipo); break; }
      }
    }
    return [...tipos];
  }

  const normalizar = (t) => (t || "").replace(/\s+/g, " ").trim();
  const MARCADOR = /\[[A-Z_]+_\d+\]/;

  window.GuardianComun = { sospechas, normalizar, MARCADOR, dniValido, ibanValido, luhnValido };
})();
