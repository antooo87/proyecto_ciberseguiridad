# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versiones con [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido
- **«✨ Mejorar mi pregunta»** (`guardian/mejorador.py`): te dice qué le falta a lo que le vas a preguntar a una IA (qué quieres que haga, de qué se trata, para qué, cómo quieres la respuesta), le pone nota de 0 a 100 y te propone dos versiones para elegir: **Directa** (al grano, para que la IA no se vaya por las ramas) y **Completa** (con formato, nivel y que no se invente nada). Distingue si preguntas algo, si quieres que te escriba algo o si te ha pasado algo (entonces pide lo urgente primero y lo que NO debes hacer). Trabaja siempre con tus datos ya tapados y deja huecos «escribe aquí...» en vez de inventarse lo que falta. Sin IA funciona con reglas; con `--ia`, la reescribe la IA local y se comprueba lo que devuelve (si cambia tus datos o se alarga demasiado, se queda la versión de reglas). Nunca usa una IA remota. Está en la terminal (`python -m guardian mejorar "..."`), en el servicio (`POST /v1/guardian/mejorar`), en la web y en la extensión: botón «✨ Mejorar» encima del cuadro del chat o `Alt+M`, con las propuestas dentro de un shadow root cerrado que la web no puede leer y el hueco del tema ya seleccionado al elegir una. También en el panel lateral y en la actividad («N preguntas mejoradas»).
- **Web con portada y menú**: la web pasa de pestañas a páginas con una portada («¿Qué quieres hacer?», lo que ha hecho esta semana y si el servicio de la extensión está encendido) y un menú lateral agrupado: antes de preguntar, lo que le das o te da la IA y tu PC. Los ajustes de la IA van plegados.
- **Nombres que entiende cualquiera** para los tipos de dato (`guardian/tipos.py`): «1 DNI y 2 teléfonos» en vez de «1 DNI, 2 TELEFONO» en los avisos, el informe y la extensión.

## [0.4.0] - 2026-11-23

Entrega final: el Guardián sale de la terminal. Funciona dentro de las webs de los chatbots, se instala con un comando y cuenta lo que ha hecho.

### Añadido
- **Extensión del navegador** (`extension/`, Chrome, Edge y Brave, Manifest V3) y **servicio local** (`python -m guardian servicio`): en ChatGPT, Claude, Gemini, Copilot, DeepSeek, Mistral, Perplexity, Qwen y Grok tapa tus datos al pegar y antes de enviar, pasa la aduana a los textos largos que pegas y revisa la respuesta de la IA. En el panel lateral se ve la respuesta con tus datos reales; la web del chatbot nunca ve ni tus datos ni la clave del servicio (solo la guarda el trabajador de fondo de la extensión). Si el servicio está apagado y el texto parece llevar datos, no lo pega ni lo envía. Página de prueba sin Internet con cuatro ejemplos. El servicio solo escucha en 127.0.0.1, comprueba Host y Origin (solo extensiones) y exige una clave al azar guardada en `~/.guardian/servicio.json`.
- **Escudo**: CIF de empresas (con su carácter de control), número de la Seguridad Social (con su control), pasaporte y fecha de nacimiento; estos tres últimos solo junto a palabras que los anuncian, para no confundirlos con otros números. Medido sin falsas alarmas nuevas.
- **Aduana y escáner para PowerPoint y Excel** (`.pptx`, `.pptm`, `.xlsx`, `.xlsm`): texto blanco sobre fondo claro (mirando el fondo de la diapositiva, del diseño y del patrón), letra de 2 puntos o menos, formas fuera de la diapositiva, diapositivas, formas, hojas, filas y columnas ocultas, hojas "muy ocultas", celdas con formato `;;;`, notas del orador, comentarios, texto alternativo, metadatos, macros, enlaces DDE y fórmulas que ejecutan programas (`cmd|`, `WEBSERVICE`...). Ejemplos: `presentacion_con_trampa.pptx` y `presupuesto_con_trampa.xlsx`.
- **Eco de la trampa** en el verificador (`guardian/verificador/eco.py`): avisa cuando la IA te empuja a verificar tu cuenta, mandar datos, pagar, instalar algo, llamar o entrar en una web y ese empujón sale de lo que ha leído (documento, web, correo pegado, resultado de una herramienta) y no de lo que pediste. Con un destino sacado de lo leído es PELIGRO. Lo usan el chat, el proxy, el servicio y la extensión. Medido sobre las 227 respuestas guardadas del ataque al agente (`evaluacion/medir_eco.py`): 8 de 8 y 9 de 9 avisos donde la IA repetía la trampa, 0 de 40 sin trampa.
- **Panel de actividad**: `python -m guardian informe [--dias N] [--json]`, la pestaña "📈 Actividad" de la web y «Esta semana» en el panel de la extensión. Datos tapados por tipo, documentos con trampas, respuestas con avisos o peligros (y de qué tipo), acciones de agentes bloqueadas y lo último importante, leído del registro, que nunca guarda los datos.
- **Instalador para Windows** (`instalar.ps1`): busca Python, crea el entorno virtual (en `%LOCALAPPDATA%\GuardianIA\entorno` si la ruta del proyecto es larga y Windows no tiene activadas las rutas largas), instala todo, comprueba Ollama y el modelo, pasa el médico y crea el lanzador `guardian.cmd` para usarlo sin activar nada. Probado en la integración continua con Windows PowerShell 5.1.
- **`python -m guardian web`**: abre la web desde cualquier carpeta, siempre solo en 127.0.0.1 y sin estadísticas de uso.
- **`evaluacion/repetir_medidas.py`**: repite todas las medidas en otro PC (pruebas, escudo y aduana con reglas y con IA, ataque al agente en cinco configuraciones y eco de la trampa) y deja un resumen con el PC, la gráfica y el tiempo de cada paso, sin tocar los resultados guardados. `guardian evaluar --salida` y `medir_eco.py CARPETA --salida` para eso.
- **Revisar carpetas antes de dárselas a una IA** (`python -m guardian escanear CARPETA`): cada documento (texto, HTML, Word, PDF) pasa por el escudo y la aduana y sale con un veredicto: TRAMPA, DATOS PERSONALES, NO SE PUEDE LEER o LIMPIO. No entra en `.git`, `.venv` ni carpetas ocultas, y el informe (`--informe`, `--json`) cuenta los datos por tipo sin enseñarlos nunca.
- **Anonimizar documentos** (`python -m guardian anonimizar ARCHIVO`): copia con solo lo que se ve (sin letra blanca ni invisibles) y los datos tapados, lista para compartir con cualquier IA.
- **`python -m guardian doctor`**: comprueba Python, que el entorno virtual está activado, las librerías (también si están instaladas a medias, como Streamlit sin `streamlit.proto`), si la ruta es tan larga que Windows corta archivos al instalar, y Ollama con el modelo. Para cada fallo dice el comando que lo arregla. Funciona aunque falten librerías.
- Web: pestaña "Revisar una carpeta" (una carpeta del PC o varios archivos subidos, con informe descargable) y anonimizar con descarga.

### Arreglado
- Al desinfectar un documento, la aduana ya no convierte `º` y `ª` en `o` y `a` (`n.º 233` se queda igual).
- El escudo tapa también los IBAN escritos en minúsculas (`es91 2100 ...`). En la prueba ciega solo con reglas, la fuga baja del 37,8 % al 35,1 % (IBAN: de 1 de 2 a 2 de 2). Ojo: este fallo se vio en la lista de fallos de la prueba ciega, así que esa mejora ya no cuenta como medida a ciegas.
- Un correo con un DNI dentro (`12345678z@gmail.com`) se tapa entero como `[EMAIL_1]`; antes se tapaba solo el DNI y quedaba `[DNI_1]@gmail.com`.
- Los lectores de Word usan `defusedxml` (nueva dependencia) para leer el XML sin DTD ni entidades, además de la comprobación rápida de DOCTYPE que ya había.
- La integración continua (`.github/workflows/tests.yml`) pasa a la raíz del repositorio, que es donde GitHub la busca. Ahora tiene tres trabajos: pruebas en Windows y Linux (Python 3.11 y 3.13), la extensión en un Chromium de verdad (Playwright) y el instalador de Windows.

### Cambiado
- El proxy apunta en el registro el tipo de cada aviso de la respuesta (para el panel de actividad).
- El médico recomienda `instalar.ps1` cuando falta el entorno o la ruta es demasiado larga.
- Si Ollama no responde, el aviso sale en español y dice cómo abrirlo y qué sigue funcionando sin él.
- La web avisa al anonimizar sin la detección con IA (sin ella no se tapan nombres ni direcciones).
- La prueba de la extensión usa su propia carpeta de registro y no se mezcla con tu actividad real.

## [0.3.0] - 2026-10-24

Los cuatro módulos funcionan. Primera versión pensada para publicarse como software libre.

### Añadido
- **Módulo 2, verificador de respuestas** (`guardian/verificador/`): comandos peligrosos tipo ClickFix (`curl | sh`, `irm | iex`, `powershell -enc`...), datos metidos en enlaces o imágenes para sacarlos fuera, imágenes externas (se bloquean), dominios que imitan a marcas (bbva-seguridad, paypa1...), acortadores, enlaces y DOI que no existen (opcional), peticiones de contraseñas, datos sensibles que la IA no recibió y comprobación con IA local de si cada frase sale del documento adjunto (respaldo).
- **Código canario**: un código secreto en las instrucciones de la IA. Si aparece en una respuesta, la IA ha contado sus instrucciones internas (OWASP LLM07).
- **Módulo 4, revisor de la IA del PC** (`guardian/revisor/`): extensiones del navegador (Chrome, Edge, Brave, Firefox) con lista negra y permisos peligrosos, conectores MCP de Claude Desktop, Cursor, VS Code, Windsurf, Claude Code, Gemini CLI, LM Studio, Cline y Roo Code (secretos en claro, versiones sin fijar, acceso a todo el disco, servidores remotos, aprobación automática), modelos descargados (pickle con código, capas Lambda de Keras, plantillas GGUF envenenadas, modelos de Ollama con instrucciones ocultas), exposición de Ollama en la red y claves en variables y archivos `.env`. Nota de salud de 0 a 100 e informe en Markdown. `revisar --demo` crea un PC de prueba lleno de problemas.
- **Aduana para Word y PDF** (`guardian/aduana/lectores.py`): encuentra texto que una persona no ve pero la IA sí lee (letra blanca, letra diminuta, texto oculto, fuera de la página, modo invisible), además de metadatos, texto alternativo de imágenes, macros, plantillas remotas y enlaces tipo Follina, y JavaScript en PDF. La IA solo recibe el texto visible. Sin dependencias para Word; PDF con pdfminer.six.
- **Modo proxy** (`python -m guardian proxy`): el Guardián delante de cualquier programa que hable con la IA en formato OpenAI (`/v1/chat/completions`). Tapa los datos de todos los mensajes, revisa los resultados de herramientas con la aduana y **controla las acciones** de los agentes: bloquea llamadas con comandos peligrosos, con datos metidos en enlaces o pedidas justo después de leer contenido sospechoso. **Control del flujo de datos**: ninguna acción puede mandar algo a una dirección sacada de lo que ha leído el agente, ni tus datos a un destino que no aparece en tus mensajes. Solo escucha en 127.0.0.1, comprueba Host y Origin y admite clave. En su pantalla enseña una línea por petición con lo que ha hecho (datos tapados por tipo, resultados revisados, acciones bloqueadas), sin enseñar ningún dato ni destino.
- `--leer-sospechosos` en el proxy: un resultado de herramienta con riesgo ALTO no se bloquea entero; la IA lo lee desinfectado para poder contestar, pero no puede hacer ninguna acción en esa conversación. Con el juez 9B, bloquear la web entera dejaba a Lucía sin las ofertas.
- **Nota al final de la respuesta** cuando la IA ha leído algo sospechoso: si el proxy lo tapó, te lo dice; si la IA lo leyó, te avisa de que no hagas lo que te pida sin comprobarlo. En el experimento, aunque no podía actuar, la IA le repetía a Lucía que tenía que "verificar su cuenta".
- **Confirmación humana** en el proxy (`--confirmar [herramienta ...]`): en vez de bloquear una acción dudosa (a un destino que no has escrito tú), te la enseña con los datos reales y espera un sí; con nombres de herramientas, pregunta siempre por esas. Lo peligroso se sigue bloqueando sin preguntar y, si nadie puede contestar, la respuesta es no.
- **Seguir tras un bloqueo**: si el proxy bloquea todas las acciones de una respuesta, se lo cuenta a la IA y le pide que conteste sin ellas (una vez y sin volver a ofrecerle esas herramientas). Antes, con el 9B, el agente atacado se paraba en el bloqueo y Lucía no recibía las ofertas ni una vez de diez. `--parar-tras-bloqueo` vuelve al comportamiento anterior.
- **Spotlighting** en el proxy (`--marcar-datos delimitar|marcas`): los resultados de herramientas llegan a la IA con un aviso de que son datos y no órdenes, entre etiquetas con un código al azar o con una marca entre cada palabra (técnica de Microsoft, Hines et al., 2024). Medido con el ataque al agente.
- **Proveedores de IA**: Ollama local, Ollama Cloud (`OLLAMA_API_KEY`) y cualquier API compatible con OpenAI (LM Studio, llama.cpp, vLLM, OpenAI...). Las piezas que ven datos sin tapar (detector, jueces) se niegan a usar una IA remota.
- **Demostración** (`python -m guardian demo`): los cuatro módulos y el control de acciones en un minuto, con ejemplos preparados y una IA simulada, así que funciona en cualquier PC sin Ollama (`--ia` usa la IA local y `--pausa` va paso a paso).
- **Evaluación con conjuntos públicos** (`evaluacion/publicos.py`): CoNLL-2002 español (nombres de personas) y BIPIA de Microsoft (prompt injection en correos).
- **Experimento de diseño del prompt** (`evaluacion/experimento_prompts.py`): cinco formas de pedirle los datos al modelo, medidas con Qwen3.5 2B y 9B.
- La aduana traduce los mensajes escritos con **etiquetas Unicode** invisibles (técnica "ASCII smuggling", usada contra Microsoft 365 Copilot en 2024) y el verificador avisa si una respuesta los trae. Las banderas de Escocia o Gales, que usan esas etiquetas de forma normal, no cuentan. Ejemplo: `resena_con_texto_invisible.txt`.
- Nueva regla de la aduana `ordenes_sobre_la_respuesta`, escrita mirando solo los ataques de entrenamiento de BIPIA.
- Ejemplos: `cv_con_trampa.docx`, `articulo_con_trampa.pdf`, `informe_limpio.docx/.pdf` y `agente_demo.py` (agente con herramientas atacado por una web).
- Web: pestañas para verificar respuestas, revisar el PC y ver resultados; subida de Word y PDF.
- Empaquetado: `pyproject.toml` (comando `guardian`), licencia MIT, `CONTRIBUTING.md`, `SECURITY.md` (avisos privados de vulnerabilidades), integración continua en GitHub Actions (Windows y Linux, Python 3.11 y 3.13) y `ruff`.
- Documentación en `docs/`: arquitectura, análisis de riesgos, estado del arte, evaluación, uso de IA en el desarrollo, casos de prueba y planificación con hitos.

### Cambiado
- Detector IA del escudo: el modelo devuelve **una lista por tipo de dato** en vez de una lista de objetos `{tipo, texto}`. En el experimento, F1 de 0,61 a 0,94 con Qwen3.5 2B y de 0,71 a 0,95 con 9B, y además más rápido.
- Al restaurar los datos, los marcadores que la IA mete dentro de enlaces o imágenes ya no se restauran (defensa contra el robo de datos por enlace).
- Los caracteres invisibles del código fuente se escriben con su código (`​`) para que el propio código no esconda nada.
- Sin colores cuando la salida va a un archivo o existe `NO_COLOR` (https://no-color.org): los registros del proxy y de las pruebas ya no se llenan de códigos de color.

## [0.2.0] - 2026-10-24

Segunda entrega (plan B).

### Añadido
- Módulo 1, escudo de datos: 11 tipos con reglas validadas (letra del DNI y NIE, Luhn, IBAN ISO 13616...) y detector con IA local para nombres, direcciones y contraseñas. Marcadores reversibles `[DNI_1]` con bóveda en memoria.
- Módulo 3, aduana de documentos: frases de ataque en español e inglés, caracteres invisibles, HTML y CSS ocultos, órdenes en base64 y juez con IA local.
- Núcleo con registro de auditoría sin datos personales, programa de terminal, web con Streamlit y evaluación con conjunto de desarrollo y prueba ciega.

## [0.1.0] - 2026-10-22

- Primer contacto con Ollama desde Python (`hola_ollama.py`).
