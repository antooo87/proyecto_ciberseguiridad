# Estrategia de uso de IA en el desarrollo

El proyecto usa IA de dos formas distintas, y conviene no mezclarlas:

1. **IA dentro del producto**: los modelos que usa el Guardián para trabajar (detector, jueces e IA que responde). Está explicado en `arquitectura.md` y sus riesgos en `amenazas.md`.
2. **IA para desarrollar el producto**: asistentes que han ayudado a pensar, programar, probar y documentar. Es lo que explica este documento.

## Qué asistentes se han usado y para qué

| Asistente | Para qué |
| --- | --- |
| Claude (Anthropic), en conversación | Buscar y comparar ideas de proyecto, preparar el planteamiento, aprender los conceptos (prompt injection, seudonimización, pickle, MCP...) y resolver dudas de programación paso a paso |
| Claude Code (agente de programación) | Escribir y probar versiones completas del código, montar la evaluación, ejecutar los experimentos con el modelo local y redactar la documentación técnica |
| Qwen3.5 en Ollama (local) | Además de ser parte del producto, se ha usado para medir: los experimentos de diseño del prompt y las evaluaciones se hacen con el modelo de verdad |

## Cómo se ha trabajado

- **Las decisiones son del autor.** El alcance, los cuatro módulos, qué entra y qué no (por ejemplo, dejar fuera el malware "hecho con IA") y las prioridades de cada entrega se deciden en persona. La IA propone opciones y explica pros y contras.
- **Aprender, no solo copiar.** El código que escribe el asistente se revisa y se ejecuta en el PC del autor, y las partes clave se rehacen a mano siguiendo una guía de pasos, preguntando cada duda (qué es un entorno virtual, qué hace cada línea, por qué una expresión regular...).
- **Nada se da por bueno sin medirlo.** Todo el código generado pasa por:
  - pruebas automáticas (`tests/`, más de cien casos) que se ejecutan en cada cambio en Windows y Linux;
  - el analizador `ruff`;
  - una evaluación con un conjunto que no se usó para ajustar nada (prueba ciega) y con conjuntos públicos de otros investigadores (CoNLL-2002 y BIPIA).
- **Experimentos en vez de intuiciones.** Cuando había que elegir un diseño, se midió. Ejemplo: cómo pedirle los datos al modelo detector. Se probaron cinco formas con los mismos textos y se eligió la que mejor F1 daba con los dos modelos (ver `evaluacion.md`).
- **Atacar el propio programa.** Antes de dar por buena una defensa, se ataca con la IA de verdad y repitiendo el ataque varias veces, porque el modelo no contesta siempre igual. Al repetir el ataque al agente, la primera versión del proxy dejó que mandase mis datos al atacante 2 veces de 5: la trampa no tenía ninguna frase típica de ataque y el escudo devolvía los datos reales a la herramienta. De ahí salió el control del flujo de datos (ver `evaluacion.md`, sección 6).
- **Fuentes comprobadas.** Las IA pueden inventarse artículos, CVE o funciones que no existen. Las referencias de `estado_del_arte.md` y `amenazas.md` se han comprobado una a una, y las librerías se han probado ejecutándolas.

## Reglas de seguridad al usar IA para desarrollar

- **Ningún dato real.** Todos los DNI, IBAN, nombres y correos de las pruebas son inventados (los DNI e IBAN tienen la letra o el control correctos, pero no son de nadie). Las claves de la demo del revisor se construyen por trozos en el código para que no parezcan claves reales a los escáneres de secretos.
- **No ejecutar sin entender.** Los comandos que propone el asistente se leen antes de ejecutarlos, sobre todo los que instalan cosas o tocan la configuración del sistema.
- **Pocas dependencias y conocidas.** Cada librería nueva es una puerta de entrada (cadena de suministro): el Word se lee con la biblioteca estándar de Python y solo se añadió `pdfminer.six` porque leer el color y la posición de cada letra de un PDF a mano no es razonable.
- **El propio código del Guardián no esconde nada.** Por ejemplo, los caracteres invisibles se escriben con su código (`​`) y no pegados, para que el código fuente se pueda revisar a simple vista.

## Qué ha aportado la IA y qué riesgos ha tenido

| Aporta | Riesgo | Cómo se ha controlado |
| --- | --- | --- |
| Velocidad para escribir y probar código | Errores sutiles que "parecen" correctos | Pruebas automáticas y evaluación con datos no vistos |
| Explicaciones adaptadas al nivel del autor | Explicaciones seguras de sí mismas pero equivocadas | Comprobar en el PC, en la documentación oficial o con un experimento |
| Ideas de ataques y casos raros para probar | Inventar referencias o versiones | Verificar cada fuente antes de citarla |
| Revisión del diseño (riesgos, límites) | Ampliar el alcance sin control | Las prioridades las fija el autor en cada entrega |

## Declaración

En este proyecto he usado herramientas de IA (principalmente Claude, de Anthropic) como apoyo para aprender, programar, probar y redactar. Las decisiones, la revisión y la validación de los resultados son mías, y todo lo que se presenta como resultado se ha medido con las pruebas y conjuntos que se describen en `evaluacion.md`.
