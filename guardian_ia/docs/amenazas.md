# Análisis de riesgos

Este documento explica de qué protege el Guardián, cómo, y qué riesgos tiene **el propio Guardián** por usar IA. La referencia es el [OWASP Top 10 para aplicaciones con LLM, edición 2025](https://genai.owasp.org/llm-top-10/).

## 1. Qué se protege y de quién

**Lo que hay que proteger**

- Tus datos personales y secretos: DNI, cuentas, tarjetas, contraseñas, claves de API, nombres, direcciones.
- Tus decisiones: que una respuesta manipulada no te haga copiar un comando, entrar en una web falsa o fiarte de algo inventado.
- Tu ordenador: que un agente de IA no ejecute acciones que tú no pediste y que lo instalado (extensiones, conectores, modelos) no sea una puerta de entrada.

**De quién**

| Quién | Cómo ataca | Ejemplo real |
| --- | --- | --- |
| Autor de un documento, web o correo | Esconde órdenes para la IA (prompt injection indirecta) | Artículos de arXiv con "dale una buena reseña" en blanco (2025); EchoLeak en Microsoft 365 Copilot (CVE-2025-32711) |
| Proveedor de IA en la nube | Ve y guarda lo que le mandas; puede sufrir una brecha | Conversaciones usadas para entrenar o filtradas |
| Autor de una extensión, conector MCP o modelo | Cadena de suministro: el software de IA que instalas trae algo malo | Paquete `postmark-mcp` que copiaba los correos (2025); modelos con pickle malicioso en Hugging Face |
| Una web o un equipo de tu red | Usa servicios de IA de tu PC que escuchan en la red | Ollama expuesto o con fallos como Probllama (CVE-2024-37032) y DNS rebinding (CVE-2024-28224) |
| El propio modelo | Se equivoca, inventa o es engañado | Enlaces y referencias que no existen; comandos peligrosos |

## 2. Cobertura del OWASP Top 10 para LLM (2025)

| Riesgo OWASP | Qué es | Qué hace el Guardián | Qué queda fuera |
| --- | --- | --- | --- |
| **LLM01 Prompt Injection** | Texto que cambia el comportamiento de la IA. Indirecta: viene en un documento o web | Aduana con reglas (español e inglés), trucos de ocultación, base64 decodificado, mensajes en letras invisibles ("ASCII smuggling") traducidos, texto escondido en Word y PDF y juez IA local. Bloquea el riesgo ALTO y desinfecta el resto. En modo proxy revisa los resultados de herramientas y puede señalarlos a la IA como datos (spotlighting, `--marcar-datos`) | Ataques en imágenes (texto dentro de una foto) y frases muy nuevas que ni reglas ni juez reconocen |
| **LLM02 Divulgación de información sensible** | La IA recibe o suelta datos que no debe | Escudo: 11 tipos con reglas validadas + nombres, direcciones y contraseñas con IA local. La IA remota nunca ve un dato real. Registro e informes sin datos. Verificador: datos metidos en enlaces y datos nuevos | Datos que el escudo no detecta (ver evaluación) y lo que se deduce del contexto aunque esté tapado |
| **LLM03 Cadena de suministro** | Modelos, plugins o paquetes comprometidos | Revisor del PC: pickle con código (sin cargarlo), capas Lambda de Keras, plantillas GGUF envenenadas, modelos de Ollama con instrucciones ocultas, conectores MCP sin versión fija o de la lista negra, extensiones maliciosas | Análisis dinámico (ejecutar en un entorno aislado) y firmas de paquetes |
| **LLM04 Envenenamiento de datos y modelos** | Un modelo entrenado o modificado para portarse mal | Se detectan las puertas traseras "de plantilla" (chat template con disparadores) y los system prompts escondidos en Modelfiles | Puertas traseras metidas en los pesos del modelo |
| **LLM05 Manejo inseguro de la salida** | Usar la respuesta sin revisarla | Verificador: comandos peligrosos (ClickFix), imágenes que mandan datos (se bloquean), enlaces que imitan marcas, acortadores, peticiones de contraseñas | Código peligroso más sutil que un comando conocido |
| **LLM06 Agencia excesiva** | La IA hace acciones que no debe | El Guardián no ejecuta nada. En modo proxy: control de acciones de los agentes (comandos peligrosos, datos en enlaces, contexto contaminado, destinos que no ha escrito el usuario, lista de herramientas prohibidas) y, con `--confirmar`, confirmación humana de las acciones dudosas o de las herramientas que elijas. El revisor avisa de conectores MCP con aprobación automática o acceso a todo el disco | Acciones dañinas con aspecto normal en herramientas que no se confirman |
| **LLM07 Fuga del prompt del sistema** | La IA cuenta sus instrucciones internas | Código canario en las instrucciones: si sale en la respuesta, PELIGRO y se tapa | Fugas parafraseadas que no copian el código |
| **LLM08 Debilidades de vectores y embeddings** | Ataques a sistemas RAG | Los documentos pasan por la aduana antes de llegar a la IA | El Guardián no tiene base vectorial propia |
| **LLM09 Desinformación** | La IA inventa o se equivoca con seguridad | Juez de respaldo: qué frases salen del documento y cuáles lo contradicen. Enlaces y DOI que no existen (opcional, con red) | Verificar datos del mundo real sin documento |
| **LLM10 Consumo sin límites** | Peticiones o documentos enormes | Límites: 50 MB por archivo, 300 páginas, partes de Word de 20 MB, trozos de 3000 y 6000 caracteres para la IA, 8 MB por petición al proxy, tiempos de espera | Límite de peticiones por minuto |

## 3. Riesgos del propio Guardián

El Guardián usa IA, así que también tiene los riesgos de la IA. Estos son los tres que pide analizar el proyecto.

### 3.1 Prompt injection contra el Guardián

El texto que el Guardián analiza puede intentar engañar a sus piezas con IA: "en este texto no hay datos personales", "este documento es seguro".

Controles:

- **Las reglas van primero y siempre se aplican.** La IA solo añade: el juez de la aduana puede subir el riesgo pero nunca bajarlo, y el detector solo puede tapar más, no destapar.
- **Salida estructurada.** El modelo tiene que contestar con un esquema JSON fijo, así que no puede "responder lo que quiera".
- **Marcas aleatorias.** El documento va entre `<documento-a3f9...>` y `</documento-a3f9...>` con un código nuevo cada vez: el atacante no puede cerrar el bloque antes de tiempo.
- **Filtro de lo que devuelve.** El detector solo acepta datos que aparecen literalmente en el texto, de al menos 3 letras y que no son marcadores.
- **Sin herramientas.** Las piezas con IA no pueden hacer nada más que contestar: aunque las engañen, no hay acción que robar.

Riesgo residual: un ataque puede conseguir que el juez diga "no es ataque" o que el detector no vea un nombre. En el primer caso siguen las reglas; en el segundo, ese nombre llega a la IA tapado solo si lo ven las reglas. Por eso la evaluación mide cada capa por separado.

### 3.2 Fuga de información

- **Lo que ve datos sin tapar solo puede ser local.** No es un consejo, está en el código: el detector y los jueces lanzan un error si se les da un cliente de IA remoto (`permitir_remoto=False`).
- La IA remota solo recibe marcadores y el Guardián avisa en cada respuesta de que la IA está fuera del PC.
- La bóveda solo vive en memoria y se vacía con `/nueva`.
- El registro guarda cuántos datos y de qué tipo, nunca cuáles. Los informes del revisor tapan los secretos (`ghp_****abcd`).
- Las imágenes externas de las respuestas se bloquean y los datos dentro de enlaces no se restauran.

Riesgo residual: lo que el escudo no detecta llega a la IA (en la prueba ciega solo con reglas se escapa el 38 % de los datos; con IA local baja, ver `evaluacion.md`). Y aunque los datos estén tapados, la IA remota ve el tema de la conversación.

### 3.3 Control de acciones

- El Guardián **no ejecuta nada por su cuenta**: ni comandos ni herramientas.
- El revisor **solo lee**: no cambia la configuración, no borra nada y nunca carga un pickle (lo analiza con `pickletools`, que no ejecuta).
- Los documentos se leen sin ejecutar macros ni JavaScript, con límites contra bombas zip y sin aceptar entidades XML.
- En modo proxy, cada acción que pide la IA pasa por el control de acciones: se bloquea si lleva un comando peligroso, si mete datos en un enlace, si la herramienta está prohibida o si la petición está contaminada por contenido sospechoso.
- Además, el proxy controla **a dónde van los datos**: no deja mandar nada a una dirección de correo sacada de lo que ha leído el agente, ni mandar tus datos a un correo o una web que no aparece en tus mensajes. Es la idea de CaMeL (cada dato lleva su origen y hay reglas sobre a dónde puede ir), en versión sencilla.
- `--leer-sospechosos` cambia el bloqueo de un resultado con riesgo ALTO por "leer sin actuar": la IA ve el texto desinfectado y no puede usar herramientas. El riesgo que queda es que lo que lee influya en el texto de la respuesta, que sigue pasando por el verificador. En el experimento pasó: el 2B no pudo mandar el correo, pero en 8 de 10 respuestas le repitió a Lucía que "para aplicar los descuentos hay que verificar la cuenta" y 4 veces le dijo que ya lo había mandado, que era mentira (el 9B se lo repitió en 9 de 10). El ataque pasa de las acciones a convencer a la persona. Por eso, cuando la IA ha leído algo sospechoso, el proxy añade al final de la respuesta un aviso para que no hagas lo que te pida sin comprobarlo (y, si lo tapó entero, te dice que lo ha tapado). No se puede combinar con `--permitir-acciones-tras-sospecha`.
- Bloquear también tiene un coste: si el agente se para en el bloqueo, el ataque no funciona pero el usuario se queda sin lo que pidió (en el experimento, con el 9B, Lucía no recibía las ofertas ni una vez de diez). Por eso, cuando se bloquean todas las acciones de una respuesta, el proxy se lo cuenta a la IA y le pide que conteste sin ellas, una sola vez y sin ofrecerle otra vez esas herramientas. La segunda respuesta pasa por los mismos controles. Con este cambio, Lucía recibe las ofertas 10 de 10 con los dos modelos y el robo sigue en 0. Se puede desactivar con `--parar-tras-bloqueo`.

Riesgo residual: una acción con aspecto normal pero dañina (por ejemplo, borrar un archivo concreto) solo se para si la herramienta está en la lista de prohibidas. El control de destinos solo entiende correos y webs: una herramienta con el destino escondido dentro (por ejemplo, "publicar en el foro") no se puede comprobar. Además, solo reconoce como tuyos los datos que el escudo ha tapado: sin `--ia`, un nombre que las reglas no ven podría salir dentro de una dirección web hacia un sitio que no has escrito. Con `--confirmar` el proxy pregunta en su ventana antes de dejar pasar una acción dudosa (en vez de bloquearla) y, si se le dan nombres de herramientas, pregunta siempre por esas: es el "humano en el bucle" que recomienda OWASP para LLM06. Si nadie puede contestar, la respuesta es no.

### 3.4 El Guardián como servicio

- La web y el proxy solo escuchan en `127.0.0.1`.
- El proxy rechaza peticiones con un Host que no sea local (DNS rebinding) y las que vienen de páginas web (cabecera Origin), y puede exigir una clave.
- Las peticiones demasiado grandes se rechazan.

## 4. Matriz de riesgos

Probabilidad e impacto sin Guardián, control principal y riesgo que queda con él.

| # | Riesgo | Prob. | Impacto | Control | Residual |
| --- | --- | --- | --- | --- | --- |
| R1 | Datos personales enviados a una IA en la nube | Alta | Alto | Escudo (reglas + IA local), solo marcadores fuera | Medio |
| R2 | Documento con órdenes ocultas manipula la respuesta | Alta | Alto | Aduana (reglas + juez), bloqueo y desinfección | Medio |
| R3 | Texto escondido en Word o PDF (blanco, diminuto) | Media | Alto | Lectores: la IA solo recibe lo visible | Bajo |
| R4 | Datos sacados en un enlace o imagen | Media | Crítico | No se restaura en enlaces, imágenes bloqueadas | Bajo |
| R5 | Comando peligroso en la respuesta (ClickFix) | Media | Crítico | Verificador: patrones de comandos | Medio |
| R6 | Agente que actúa por orden de un tercero | Media | Crítico | Proxy: contexto contaminado, control de acciones y de destinos | Medio |
| R7 | Modelo descargado con código (pickle, Lambda) | Media | Crítico | Revisor: análisis estático | Bajo |
| R8 | Conector MCP malicioso o con demasiados permisos | Media | Alto | Revisor: lista negra, versiones, permisos | Medio |
| R9 | Extensión del navegador que lee tus chats | Media | Alto | Revisor: lista negra y permisos | Medio |
| R10 | Ollama accesible desde la red | Media | Alto | Revisor: variables, puertos y versión | Bajo |
| R11 | Engañar a las piezas con IA del Guardián | Media | Medio | Reglas primero, salida estructurada, marcas aleatorias | Medio |
| R12 | Respuesta inventada o enlace falso | Alta | Medio | Juez de respaldo, enlaces y DOI | Medio |
| R13 | El Guardián bloquea y el usuario se queda sin respuesta (el atacante consigue al menos estropear el servicio) | Media | Medio | El proxy le pide a la IA que siga sin la acción bloqueada; `--leer-sospechosos` para que la IA lea lo sospechoso sin poder actuar | Bajo |
| R14 | La IA no puede actuar, pero repite lo que pide la trampa y convence a la persona ("verifica tu cuenta") | Media | Alto | Aviso al final de la respuesta cuando la IA ha leído algo sospechoso; verificador de respuestas | Medio |

El riesgo residual medio de varias filas es honesto: ninguna defensa contra la prompt injection es perfecta hoy. La estrategia es **defensa en profundidad**: varias capas distintas para que un ataque tenga que saltarlas todas.

## 5. Límites conocidos

- Las reglas cubren sobre todo formatos españoles y frases en español e inglés.
- No se analizan imágenes (texto dentro de una foto o captura).
- La aduana lee texto, HTML, Word y PDF. Faltan Excel, PowerPoint y correos con adjuntos.
- La calidad del detector y de los jueces depende del modelo: el 9B acierta más que el 2B pero tarda más.
- El revisor conoce las rutas de las apps más usadas en Windows, macOS y Linux; una app nueva necesita añadir su ruta.
