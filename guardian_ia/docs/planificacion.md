# Planificación e hitos

El planteamiento (primera entrega, 1 de octubre de 2026) repartía el trabajo en 12 semanas, y la memoria intermedia dejó los hitos H4 a H8. Este documento compara aquel plan con lo hecho, explica qué ha cambiado y por qué, y deja lo que queda.

## Hitos cumplidos

| Hito | Fecha | Versión | Qué se entregó |
| --- | --- | --- | --- |
| H0 · Planteamiento | 1-oct-2026 | – | Idea, objetivos, herramientas parecidas, papel de la IA, riesgos, tecnologías y planificación (memoria de 4 páginas) |
| H1 · Entorno con IA local | 22-oct-2026 | 0.1.0 | Ollama con Qwen3.5 en el portátil (con GPU) y primer programa en Python que habla con el modelo |
| H2 · Segunda entrega | 24-oct-2026 | 0.2.0 | Escudo de datos y aduana de documentos, con web, registro sin datos personales y prueba ciega |
| H3 · Versión completa | 24-oct-2026 | 0.3.0 | Los cuatro módulos, modo proxy con control de acciones, evaluación con conjuntos públicos y ataque real a un agente, demostración, pruebas automáticas y documentación |
| H4 · Validación y arreglos | 26-oct a 23-nov-2026 | 0.4.0 | Arreglos de la revisión (IBAN en minúsculas, correo con un DNI dentro, `defusedxml`), integración continua en GitHub (pruebas en Windows y Linux, la extensión en un Chromium de verdad y el instalador de Windows), `guardian doctor` e instalador `instalar.ps1`. **Falta repetir las medidas con el 9B en la GPU del portátil**: `evaluacion/repetir_medidas.py --ia --agente` lo deja en un comando |
| H5 · Extensión del navegador | 23-nov-2026 | 0.4.0 | Extensión para ChatGPT, Claude, Gemini, Copilot, DeepSeek, Mistral, Perplexity, Qwen y Grok que habla con el servicio local del Guardián (`guardian servicio`): tapa al pegar y antes de enviar, aduana para lo pegado, revisión de la respuesta y panel con tus datos reales |

Además, en la 0.4.0 entraron cosas que no estaban en el plan y que salieron de usar el programa y de los puntos débiles de la evaluación:

- **Eco de la trampa** en el verificador: el punto débil más claro del ataque al agente (la IA, sin poder actuar, le repetía a Lucía que verificara su cuenta).
- **PowerPoint y Excel** en la aduana y el escáner, porque son documentos que se suben mucho a los chatbots.
- **Panel de actividad** (`guardian informe`, pestaña de la web y panel de la extensión), sin guardar ningún dato.
- **Revisar carpetas y anonimizar documentos** (`guardian escanear`, `guardian anonimizar`).
- Cuatro tipos de dato nuevos en el escudo: CIF, número de la Seguridad Social, pasaporte y fecha de nacimiento.

## El plan de 12 semanas frente a lo hecho

| Semanas | Plan del planteamiento | Estado |
| --- | --- | --- |
| 1-2 | Estudiar las herramientas parecidas y los riesgos, preparar el entorno y diseñar la arquitectura | Hecho: [`estado_del_arte.md`](estado_del_arte.md), [`amenazas.md`](amenazas.md), [`arquitectura.md`](arquitectura.md) |
| 3-4 | Escudo de datos | Hecho y medido: reglas con validación (15 tipos) e IA local para nombres, direcciones y contraseñas |
| 5-6 | Verificador de respuestas | Hecho, con el eco de la trampa en la 0.4.0. Falta contrastar afirmaciones con fuentes (H6) |
| 7-8 | Aduana de documentos | Hecho: texto, Word, PowerPoint, Excel, PDF, HTML oculto, ASCII smuggling y juez con IA |
| 9 | Unir los módulos, extensión del navegador y panel | Hecho: programa de terminal, web, modo proxy, extensión del navegador y panel de actividad |
| 10 | Pruebas y medición de resultados | Hecho en CPU: prueba ciega, CoNLL-2002, BIPIA, ataque a un agente y eco de la trampa ([`evaluacion.md`](evaluacion.md)). Falta repetirlo en la GPU |
| 11 | Documentación y publicación en GitHub | Hecho: repositorio público con integración continua |
| 12 | Memoria final y presentación | En curso (entrega final el 29 de noviembre) |
| Extra | Revisión del software de IA del PC (si el proyecto duraba cuatro meses) | Hecho: módulo 4, revisor del PC |

## Cambios respecto al planteamiento

| En el planteamiento | Ahora | Por qué |
| --- | --- | --- |
| FastAPI para el intermediario y el panel | Servidor HTTP de la biblioteca estándar para el proxy y el servicio, y Streamlit para la web | Para una sola persona en su PC es suficiente y hay menos dependencias. Las protecciones importantes (escuchar solo en 127.0.0.1, comprobar Host y Origin, clave, tamaño máximo) están hechas a mano y tienen pruebas |
| Microsoft Presidio y expresiones regulares | Reglas propias con validación (letra del DNI y del NIE, IBAN, Luhn, CIF, Seguridad Social...) e IA local para lo que no tiene formato | Presidio necesita modelos de spaCy y los formatos españoles hay que añadirlos de todas formas. Con reglas propias cada detección se puede explicar, y la IA local cubre los nombres y direcciones (medido en [`evaluacion.md`](evaluacion.md)) |
| SQLite para el historial | Registro en archivos JSON Lines, sin datos personales, con un resumen para el panel de actividad | Solo hace falta añadir líneas y leerlas. Un archivo de texto se revisa a mano y no guarda nada sensible |
| API de Claude para el verificador (unos céntimos por consulta) | Todo con IA local. Las piezas que ven datos sin tapar se niegan a usar una IA remota | Coste 0 € y ningún dato sale del PC |
| Extensión del navegador en la semana 9 | Hecha en la 0.4.0, después del proxy | Los agentes y programas de escritorio son los que pueden hacer acciones peligrosas, así que el proxy iba primero. La extensión no tapa nada por sí misma: se lo pide al servicio del PC, así las reglas, la bóveda y la IA local son las mismas en todas partes |
| (no estaba) | Modo proxy con control de acciones y del flujo de datos | Los agentes con herramientas convierten el prompt injection en acciones reales (mandar correos, ejecutar comandos). Era el riesgo más importante que el plan no cubría |
| (no estaba) | Instalador de Windows y `guardian doctor` | Al probarlo en mi portátil, Streamlit se instalaba a medias por la ruta larga de la carpeta (Windows corta a 260 caracteres). El instalador lo evita y el médico lo detecta |

## Hitos que quedan

| Hito | Cuándo | Qué |
| --- | --- | --- |
| H4 (lo que falta) | Antes del 29-nov | Repetir las medidas con el 9B (y el 4B) en la GPU del portátil: `python evaluacion\repetir_medidas.py --ia --agente --modelo qwen3.5:9b` |
| H6 · Verificador con fuentes | Después de la entrega, si da tiempo | Contrastar las afirmaciones de la respuesta con fuentes (por ejemplo, una enciclopedia) sin mandar fuera datos sin tapar |
| H7 · Evaluación final | Antes del 29-nov (parte) | Más trampas, herramientas y modelos en el ataque al agente (el script ya acepta otros modelos) y una prueba con usuarios sin conocimientos de ciberseguridad |
| H8 · Memoria final y presentación | 29-nov-2026 | Memoria final y demostración en clase (`.\guardian demo --pausa`, la web y la extensión con su página de prueba) |

## Riesgos de la planificación

| Riesgo | Plan B |
| --- | --- |
| El modelo 9B va lento en el portátil | Qwen3.5 4B o 2B (los dos medidos) y, siempre, las reglas sin IA |
| Una web de chatbot cambia y la extensión deja de encontrar sus respuestas | Al pegar y al enviar trabaja con el cuadro de texto que tiene el foco, sin depender del diseño de cada web; para leer las respuestas hay una lista de selectores en un solo sitio (`SELECTORES_RESPUESTA` en `extension/contenido.js`) y, si falla, el clic derecho «Guardián: ver con mis datos» funciona en cualquier web. La página de prueba permite comprobarla sin depender de ninguna web. Con el servicio apagado, lo que parece llevar datos no se pega ni se envía |
| Aparecen técnicas de ataque nuevas | Cada técnica nueva entra como regla con su caso de prueba, como el ASCII smuggling en la versión 0.3.0 o el texto escondido en PowerPoint y Excel en la 0.4.0 |
