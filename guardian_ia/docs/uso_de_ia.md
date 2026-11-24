# Estrategia de uso de IA en el desarrollo

El proyecto usa IA de dos formas distintas, y conviene no mezclarlas:

1. **IA dentro del producto**: los modelos que usa el Guardián para trabajar (detector, jueces e IA que responde). Está explicado en `arquitectura.md` y sus riesgos en `amenazas.md`.
2. **IA para desarrollar el producto**: asistentes que han ayudado a pensar, programar, probar y documentar. Es lo que explica este documento.

## Qué asistentes se han usado y para qué

| Asistente | Para qué |
| --- | --- |
| Claude (Anthropic), en conversación | Buscar y comparar ideas de proyecto, preparar el planteamiento, aprender los conceptos (prompt injection, seudonimización, pickle, MCP...) y resolver dudas de programación paso a paso |
| Claude Code (agente de programación) | Escribir y probar versiones completas del código (el Guardián en Python, la extensión del navegador en JavaScript y el instalador de Windows en PowerShell), montar la evaluación y la integración continua, ejecutar los experimentos con el modelo local y redactar la documentación técnica |
| Qwen3.5 en Ollama (local) | Además de ser parte del producto, se ha usado para medir: los experimentos de diseño del prompt y las evaluaciones se hacen con el modelo de verdad |

## Cómo se ha trabajado

- **Las decisiones son del autor.** El alcance, los cuatro módulos, qué entra y qué no (por ejemplo, dejar fuera el malware "hecho con IA") y las prioridades de cada entrega se deciden en persona. La IA propone opciones y explica pros y contras.
- **Aprender, no solo copiar.** El código que escribe el asistente se revisa y se ejecuta en el PC del autor, y las partes clave se rehacen a mano siguiendo una guía de pasos, preguntando cada duda (qué es un entorno virtual, qué hace cada línea, por qué una expresión regular...).
- **Nada se da por bueno sin medirlo.** Todo el código generado pasa por:
  - pruebas automáticas (`tests/`, 320 casos) que se ejecutan en cada cambio en Windows y Linux;
  - una prueba de la extensión en un Chromium de verdad, que carga la extensión y hace lo que haría una persona en la página de prueba (pegar datos, enviar, pegar un documento con trampa);
  - el instalador de Windows, que se ejecuta dos veces en un Windows limpio de GitHub y comprueba que la web solo escucha en el propio PC;
  - el analizador `ruff`;
  - una evaluación con un conjunto que no se usó para ajustar nada (prueba ciega) y con conjuntos públicos de otros investigadores (CoNLL-2002 y BIPIA).
- **Experimentos en vez de intuiciones.** Cuando había que elegir un diseño, se midió. Ejemplo: cómo pedirle los datos al modelo detector. Se probaron cinco formas con los mismos textos y se eligió la que mejor F1 daba con los dos modelos (ver `evaluacion.md`).
- **Atacar el propio programa.** Antes de dar por buena una defensa, se ataca con la IA de verdad y repitiendo el ataque varias veces, porque el modelo no contesta siempre igual. Al repetir el ataque al agente, la primera versión del proxy dejó que mandase mis datos al atacante 2 veces de 5: la trampa no tenía ninguna frase típica de ataque y el escudo devolvía los datos reales a la herramienta. De ahí salió el control del flujo de datos (ver `evaluacion.md`, sección 6).
- **Decir qué medida no es ciega.** El eco de la trampa (0.4.0) se diseñó mirando las respuestas del ataque al agente y se midió con esas mismas respuestas, así que su resultado no vale como prueba ciega. Lo mismo pasa con el arreglo de los IBAN en minúsculas, que salió de la propia prueba ciega. En `evaluacion.md` se dice así y las tablas dejan los números originales.
- **Casos densos, no frases de una línea.** Para la 0.5.0 se pidió al asistente una empresa inventada con los documentos que tendría de verdad (nóminas, contratos, currículums, correos...), creada por un programa (`ejemplos/casos_reales/generar.py`) que apunta cada dato que mete. Así las pruebas no comprueban "que encuentra algo" sino que encuentra **exactamente** esos datos. Al probarlos salieron fallos que con los ejemplos cortos no se veían: el número de la Seguridad Social en una columna de Excel (la palabra que lo anuncia está en la cabecera, no al lado), la contraseña dentro de una cadena de conexión, los correos `.eml` leídos sin descodificar (un IBAN partido en dos líneas) y seis de las diez preguntas de prueba mal entendidas por «Mejorar mi pregunta». Como los casos se escribieron a la vez que se arreglaban las reglas, **no son una medida a ciegas**, y así se dice en su `LEEME.md` y en `evaluacion.md`.
- **Probarlo en mi PC, no solo en la nube.** El instalador de Windows salió de un fallo real: en mi portátil Streamlit se instalaba a medias porque la carpeta del proyecto tiene una ruta muy larga y Windows corta los archivos a 260 caracteres. En Linux no pasaba. Ahora el instalador lo evita, `guardian doctor` lo detecta y la integración continua lo prueba en un Windows limpio.
- **Lo que funciona en Linux puede fallar en Windows.** La prueba que compara los casos reales guardados con los que crea el generador falló solo en Windows: Python cambia los saltos de línea al escribir texto y el zip guarda en qué sistema se creó. Se arregló escribiendo los archivos byte a byte y comparando lo que hay dentro de cada zip, y ahora se comprueba en los dos sistemas en cada cambio.
- **La IA también se equivoca al revisar.** Revisando la web, el asistente afirmó que se podía abrir desde otros equipos de la wifi y que mandaba estadísticas de uso. Al comprobarlo no era verdad: `.streamlit/config.toml` ya lo impedía desde la versión 0.3.0. Se corrigió la afirmación y, para no depender de la carpeta desde la que se arranca, `guardian web` pasa esas opciones él mismo y tiene una prueba.
- **Fuentes comprobadas.** Las IA pueden inventarse artículos, CVE o funciones que no existen. Las referencias de `estado_del_arte.md` y `amenazas.md` se han comprobado una a una, y las librerías se han probado ejecutándolas.

## Reglas de seguridad al usar IA para desarrollar

- **Ningún dato real.** Todos los DNI, IBAN, nombres y correos de las pruebas son inventados (los DNI e IBAN tienen la letra o el control correctos, pero no son de nadie). Las claves de la demo del revisor se construyen por trozos en el código para que no parezcan claves reales a los escáneres de secretos.
- **No ejecutar sin entender.** Los comandos que propone el asistente se leen antes de ejecutarlos, sobre todo los que instalan cosas o tocan la configuración del sistema.
- **Pocas dependencias y conocidas.** Cada librería nueva es una puerta de entrada (cadena de suministro). El Word, el PowerPoint y el Excel son archivos zip con XML dentro y se leen con la biblioteca estándar de Python, más `defusedxml` para que un documento preparado no pueda colgar el programa con una «bomba XML». Solo se añadió `pdfminer.six` porque leer el color y la posición de cada letra de un PDF a mano no es razonable. La extensión del navegador no usa ninguna librería de fuera, solo se activa en las webs de los chatbots y no pide permiso para ver tus pestañas ni tu historial.
- **El propio código del Guardián no esconde nada.** Por ejemplo, los caracteres invisibles se escriben con su código (`​`) y no pegados, para que el código fuente se pueda revisar a simple vista.

## Qué ha aportado la IA y qué riesgos ha tenido

| Aporta | Riesgo | Cómo se ha controlado |
| --- | --- | --- |
| Velocidad para escribir y probar código | Errores sutiles que "parecen" correctos | Pruebas automáticas y evaluación con datos no vistos |
| Explicaciones adaptadas al nivel del autor | Explicaciones seguras de sí mismas pero equivocadas | Comprobar en el PC, en la documentación oficial o con un experimento |
| Ideas de ataques y casos raros para probar | Inventar referencias o versiones | Verificar cada fuente antes de citarla |
| Revisión del diseño (riesgos, límites) | Ampliar el alcance sin control | Las prioridades las fija el autor en cada entrega |
| Programar en lenguajes que conozco menos (JavaScript de la extensión, PowerShell del instalador) | No poder revisar bien lo que no se entiende | Pruebas en un navegador de verdad y en un Windows limpio, y pedir la explicación de cada parte antes de presentarla |
| Generar casos de prueba densos (empresa inventada, correos, documentos con trampas) | Que los casos se ajusten a lo que el programa ya sabe hacer | El generador apunta cada dato, el resultado se comprueba con valores exactos y se dice claramente que no es una medida a ciegas |
| Revisar su propio trabajo | Ver fallos que no existen, o no ver los que sí | Comprobarlo en el código y con una prueba antes de cambiar nada |

## Declaración

En este proyecto he usado herramientas de IA (principalmente Claude, de Anthropic) como apoyo para aprender, programar, probar y redactar. Las decisiones, la revisión y la validación de los resultados son mías, y todo lo que se presenta como resultado se ha medido con las pruebas y conjuntos que se describen en `evaluacion.md`.
