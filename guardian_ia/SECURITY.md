# Política de seguridad

El Guardián IA es una herramienta defensiva: si encuentras una forma de saltártelo, es justo lo que más ayuda a mejorarlo.

## Versiones con soporte

| Versión | Soporte |
| --- | --- |
| 0.3.x | Sí |
| Anteriores | No |

## Cómo avisar de una vulnerabilidad

No abras una issue pública. Usa **Report a vulnerability** en la pestaña *Security* del repositorio (avisos privados de GitHub) y cuenta:

- la versión y el sistema (Windows, Linux...),
- los pasos para reproducirlo, con un ejemplo inventado (nunca datos reales),
- qué consigue el ataque.

Intentaré contestar en una semana y, cuando esté arreglado, el aviso se publicará con tu nombre si quieres.

## Qué cuenta como vulnerabilidad

- Un dato que el escudo debería reconocer y llega a la IA sin tapar.
- Un documento o un resultado de herramienta que consigue que el proxy deje pasar una acción que debería bloquear (por ejemplo, mandar tus datos a un destino que no has escrito).
- Saltarse las protecciones del proxy: escuchar fuera de 127.0.0.1, cabeceras Host u Origin, clave.
- Que el registro guarde algún dato personal.
- Que el revisor del PC ejecute algo de lo que analiza (por ejemplo, cargar un pickle).

## Qué no cuenta

- Que la IA se equivoque en una respuesta: es un límite conocido (ver [`docs/amenazas.md`](docs/amenazas.md)).
- Ataques que necesitan tener ya acceso al PC.
- Frases de prompt injection nuevas que las reglas no conocen: son bienvenidas como caso de prueba en una issue normal o un pull request (ver [`CONTRIBUTING.md`](CONTRIBUTING.md)).

Los ataques de `ejemplos/` y `evaluacion/` son inofensivos: sirven para probar las defensas y no hacen nada fuera del programa.
