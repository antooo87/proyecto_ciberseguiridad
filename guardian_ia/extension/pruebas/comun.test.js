// Pruebas rápidas del primer filtro del navegador (comun.js). No necesita instalar nada:
//   node extension/pruebas/comun.test.js
"use strict";
const assert = require("assert");

global.window = {};
require("../comun.js");
const G = window.GuardianComun;

const CASOS = [
  ["Mi DNI es 12345678Z", ["DNI"]],
  ["Mi DNI es 12345678A", []], // la letra no cuadra: no es un DNI
  ["Mi NIE es X1234567L", ["NIE"]],
  ["mi cuenta ES91 2100 0418 4502 0005 1332 y mi correo", ["IBAN"]],
  ["en minúsculas: es91 2100 0418 4502 0005 1332", ["IBAN"]],
  ["ES00 1234 5678 9012 3456 7890", []], // no pasa el control del IBAN
  ["tarjeta 4111 1111 1111 1111", ["TARJETA"]],
  ["tarjeta 4111 1111 1111 1112", []], // no pasa el algoritmo de Luhn
  ["escríbeme a ana.lopez@example.com", ["EMAIL"]],
  ["llámame al 612 345 678", ["TELEFONO"]],
  ["mi contraseña: Verano2026!", ["CONTRASENA"]],
  ["la clave de la API es " + "sk-" + "proj-" + "a1B2c3D4e5F6g7H8i9J0k1L2", ["CLAVE_API"]],
  ["la empresa tiene CIF B-12345674", ["CIF"]],
  ["la empresa tiene CIF B-12345675", []], // control incorrecto
  ["el ayuntamiento tiene CIF P1234567D", ["CIF"]], // las entidades públicas llevan letra de control
  ["mi número de la Seguridad Social es 28 12345678 40", ["NSS"]],
  ["el pedido 281234567840 ya ha salido", []], // 12 cifras sin decir qué son
  ["mi pasaporte es PAA123456", ["PASAPORTE"]],
  ["fecha de nacimiento: 12/03/1990", ["FECHA_NACIMIENTO"]],
  ["nací el 3 de mayo de 1999", ["FECHA_NACIMIENTO"]],
  ["la reunión es el 12/03/2026", []],
  ["Hola, ¿qué tiempo hace hoy en Madrid?", []],
  ["Factura 2026-118 por 450,00 € a 30 días", []],
];

let fallos = 0;
for (const [texto, esperado] of CASOS) {
  const obtenido = G.sospechas(texto).sort();
  try {
    assert.deepStrictEqual(obtenido, [...esperado].sort());
    console.log(`OK    ${texto}`);
  } catch (e) {
    fallos++;
    console.log(`FALLO ${texto}\n      esperaba ${JSON.stringify(esperado)} y salió ${JSON.stringify(obtenido)}`);
  }
}
assert.ok(G.MARCADOR.test("[DNI_1]") && !G.MARCADOR.test("[nota]"), "MARCADOR");
assert.strictEqual(G.normalizar("  hola \n  mundo "), "hola mundo");
console.log(fallos ? `${fallos} FALLOS` : `TODO OK (${CASOS.length} casos)`);
process.exit(fallos ? 1 : 0);
