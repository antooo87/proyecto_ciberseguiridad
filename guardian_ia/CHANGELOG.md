# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versiones con [SemVer](https://semver.org/lang/es/).

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
