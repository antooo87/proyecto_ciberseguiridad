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

- La web, el proxy y el servicio de la extensión solo escuchan en `127.0.0.1`. `guardian web` lo fuerza aunque Streamlit se arranque desde otra carpeta, y no manda estadísticas de uso.
- El proxy y el servicio rechazan peticiones con un Host que no sea local (DNS rebinding) y las que vienen de páginas web (cabecera Origin). El proxy puede exigir una clave y el servicio la exige siempre (32 caracteres al azar, guardada solo para tu usuario en `~/.guardian/servicio.json`).
- Las peticiones demasiado grandes se rechazan.

### 3.5 La extensión del navegador

La extensión vive dentro de webs que no son nuestras, así que se diseñó suponiendo que la web del chatbot (o un script malicioso dentro de ella) puede intentar abusar de ella:

- **La web no ve nada que no deba.** Solo recibe el texto ya tapado. La respuesta con tus datos reales se enseña en el panel lateral, que es una página de la extensión y la web no puede leer. La clave del servicio solo la tiene el trabajador de fondo; a los scripts de las webs solo se les pasan los interruptores de las opciones.
- **Solo la extensión habla con el servicio.** El servicio rechaza cualquier petición con un Origin que no sea de una extensión y sin la clave, así que una web cualquiera no puede usar tu Guardián para restaurar marcadores. El resumen de actividad solo se da a las páginas de la propia extensión.
- **Nada de HTML de fuera.** Las respuestas se pintan con `textContent` (nunca `innerHTML`), así que una respuesta manipulada no puede meter código en el panel. Los avisos en la web van dentro de un shadow root cerrado.
- **Permisos justos.** Solo se ejecuta en las webs de los chatbots de la lista y solo puede conectar con `127.0.0.1`; no pide acceso a todas las webs ni el permiso «tabs» (para ver las direcciones de tus pestañas).
- **Fallo cerrado.** Si el servicio está apagado, un texto que parece llevar datos (según una copia de las reglas en la propia extensión) no se pega ni se envía.

Riesgo residual: la extensión depende de cómo está hecha cada web; si una web cambia su página, puede dejar de leer las respuestas (el clic derecho «Guardián: ver con mis datos» sirve en cualquier web). Una extensión maliciosa instalada en el mismo navegador podría leer lo que se ve en la página, igual que con cualquier otra web: para eso está el revisor del PC (R9).

### 3.6 «¿Es una estafa?», los correos y «Mejorar mi pregunta» (0.5.0)

Estas piezas las va a usar gente que no sabe de informática, así que el riesgo principal no es técnico: es que la persona se fíe demasiado del resultado.

- **Un «no veo pistas» no es un «es seguro».** Las reglas solo reconocen las pistas que conocen; una estafa escrita de otra forma puede pasar. Por eso el resultado bajo dice «No veo señales claras de estafa» y siempre añade que, si te pide datos, dinero o prisa, lo compruebes por otro camino. Lo mismo en el juego: tiene mensajes legítimos para no enseñar a desconfiar de todo ni a fiarse de todo.
- **Un correo preparado contra el Guardián.** Un `.eml` puede traer cabeceras rotas, codificaciones inventadas o HTML retorcido. El lector usa la biblioteca estándar de Python, nunca falla (se queda con lo que puede leer), no pinta el HTML ni carga imágenes remotas, no abre los adjuntos (solo mira su nombre) y en una bandeja se salta los archivos de más de 25 MB. No abre nada de Internet.
- **Texto escondido para la IA que te resume el correo** (el caso de Gemini en Gmail en 2025). Se separa lo que se ve de lo escondido (tamaño 0, blanco sin fondo, `display:none`, comentarios): «¿Es una estafa?» lo cuenta como pista y la aduana lo quita antes de que el correo llegue a un chatbot.
- **Que la mejora cambie lo que querías decir o meta datos.** La pregunta se tapa antes de nada; la IA (solo local) trabaja con marcadores y lo que devuelve se comprueba: si quita o cambia un marcador, mete un dato que no estaba o se alarga demasiado, se descarta y se queda la versión de reglas. Lo que no sabe, no lo inventa: deja un hueco «escribe aquí...». Y si la pregunta parece una orden escondida (alguien que te ha hecho copiar un texto), avisa.

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
| R14 | La IA no puede actuar, pero repite lo que pide la trampa y convence a la persona ("verifica tu cuenta") | Media | Alto | Verificador: eco de la trampa (PELIGRO si lleva un destino sacado de lo leído) y aviso al final de la respuesta cuando la IA ha leído algo sospechoso. Medido: 8/8 y 9/9 avisos, 0 de 40 falsas alarmas | Bajo |
| R15 | Pegar en un chatbot de la web datos personales o un documento con trampa | Alta | Alto | Extensión del navegador: tapa al pegar y antes de enviar, aduana para lo pegado, fallo cerrado sin servicio | Medio |
| R16 | Una web abusa de la extensión o del servicio local para leer tus datos | Baja | Alto | Clave solo en el trabajador de fondo, Origin solo de extensiones, panel que la web no puede leer, `textContent` | Bajo |
| R17 | Texto escondido en PowerPoint o Excel (blanco, diminuto, hojas ocultas, `;;;`) | Media | Alto | Lectores de PowerPoint y Excel: la IA solo recibe lo visible; fórmulas DDE y macros avisadas | Bajo |
| R18 | Picar en una estafa por SMS, WhatsApp o correo (enlace falso, adjunto disfrazado, fraude del CEO) | Alta | Alto | «¿Es una estafa?»: pistas explicadas, remitente real, enlaces engañosos, adjuntos peligrosos, primeros auxilios y el juego para aprender | Medio |
| R19 | Correo con texto escondido que manipula a la IA que lo resume | Media | Alto | Lector de correos: lo escondido se separa, se avisa y la aduana lo quita | Bajo |
| R20 | La persona se fía de un «no veo pistas» | Media | Alto | El resultado nunca dice «es seguro» y siempre recomienda comprobarlo por otro camino | Medio |

El riesgo residual medio de varias filas es honesto: ninguna defensa contra la prompt injection es perfecta hoy. La estrategia es **defensa en profundidad**: varias capas distintas para que un ataque tenga que saltarlas todas.

## 5. Límites conocidos

- Las reglas cubren sobre todo formatos españoles y frases en español e inglés.
- No se analizan imágenes (texto dentro de una foto o captura).
- La aduana lee texto, HTML, Word, PowerPoint, Excel, PDF y correos `.eml`. Faltan los formatos antiguos (`.doc`, `.xls`, `.ppt`), OpenDocument, los `.msg` de Outlook y lo que hay dentro de los adjuntos de un correo (solo se mira su nombre).
- «¿Es una estafa?» y «Mejorar mi pregunta» sin IA funcionan con reglas: una estafa escrita de una forma nueva puede no tener ninguna de las pistas que conocen.
- El eco de la trampa reconoce peticiones de verificar cuentas, mandar datos, pagar, instalar, llamar o entrar en webs, en español y en inglés; una trampa que pida otra cosa necesitaría una categoría nueva.
- La calidad del detector y de los jueces depende del modelo: el 9B acierta más que el 2B pero tarda más.
- El revisor conoce las rutas de las apps más usadas en Windows, macOS y Linux; una app nueva necesita añadir su ruta.
