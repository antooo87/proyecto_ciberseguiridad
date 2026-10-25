# Planificación e hitos

El planteamiento (primera entrega, 1 de octubre de 2026) repartía el trabajo en 12 semanas. Este documento compara aquel plan con lo hecho hasta ahora, explica qué ha cambiado y por qué, y deja los hitos que quedan.

## Hitos cumplidos

| Hito | Fecha | Versión | Qué se entregó |
| --- | --- | --- | --- |
| H0 · Planteamiento | 1-oct-2026 | – | Idea, objetivos, herramientas parecidas, papel de la IA, riesgos, tecnologías y planificación (memoria de 4 páginas) |
| H1 · Entorno con IA local | 22-oct-2026 | 0.1.0 | Ollama con Qwen3.5 en el portátil (con GPU) y primer programa en Python que habla con el modelo |
| H2 · Segunda entrega | 24-oct-2026 | 0.2.0 | Escudo de datos y aduana de documentos, con web, registro sin datos personales y prueba ciega |
| H3 · Versión completa | 24-oct-2026 | 0.3.0 | Los cuatro módulos, modo proxy con control de acciones, evaluación con conjuntos públicos y ataque real a un agente, demostración, pruebas automáticas y documentación |

## El plan de 12 semanas frente a lo hecho

| Semanas | Plan del planteamiento | Estado |
| --- | --- | --- |
| 1-2 | Estudiar las herramientas parecidas y los riesgos, preparar el entorno y diseñar la arquitectura | Hecho: [`estado_del_arte.md`](estado_del_arte.md), [`amenazas.md`](amenazas.md), [`arquitectura.md`](arquitectura.md) |
| 3-4 | Escudo de datos | Hecho y medido: reglas con validación y IA local para nombres, direcciones y contraseñas |
| 5-6 | Verificador de respuestas | Hecho (primera versión completa) |
| 7-8 | Aduana de documentos | Hecho: texto, Word, PDF, HTML oculto, ASCII smuggling y juez con IA |
| 9 | Unir los módulos, extensión del navegador y panel | Unidos en el programa de terminal, la web y el modo proxy. **Falta la extensión del navegador** |
| 10 | Pruebas y medición de resultados | Adelantado: prueba ciega, CoNLL-2002, BIPIA y ataque a un agente con herramientas ([`evaluacion.md`](evaluacion.md)) |
| 11 | Documentación y publicación en GitHub | Documentación hecha. Falta publicar el repositorio |
| 12 | Memoria final y presentación | Pendiente |
| Extra | Revisión del software de IA del PC (si el proyecto duraba cuatro meses) | Hecho: módulo 4, revisor del PC |

## Cambios respecto al planteamiento

| En el planteamiento | Ahora | Por qué |
| --- | --- | --- |
| FastAPI para el intermediario y el panel | Servidor HTTP de la biblioteca estándar para el proxy y Streamlit para la web | Para una sola persona en su PC es suficiente y hay menos dependencias. Las protecciones importantes (escuchar solo en 127.0.0.1, comprobar Host y Origin, clave, tamaño máximo) están hechas a mano y tienen pruebas |
| Microsoft Presidio y expresiones regulares | Reglas propias con validación (letra del DNI y del NIE, IBAN, Luhn...) e IA local para lo que no tiene formato | Presidio necesita modelos de spaCy y los formatos españoles hay que añadirlos de todas formas. Con reglas propias cada detección se puede explicar, y la IA local cubre los nombres y direcciones (medido en [`evaluacion.md`](evaluacion.md)) |
| SQLite para el historial | Registro en archivos JSON Lines, sin datos personales | Solo hace falta añadir líneas y leerlas. Un archivo de texto se revisa a mano y no guarda nada sensible |
| API de Claude para el verificador (unos céntimos por consulta) | Todo con IA local. Las piezas que ven datos sin tapar se niegan a usar una IA remota | Coste 0 € y ningún dato sale del PC |
| Extensión del navegador | Aplazada. El modo proxy protege a los programas que dejan cambiar la dirección de la IA | Los agentes y programas de escritorio son los que pueden hacer acciones peligrosas, así que el proxy iba primero. La extensión es el siguiente hito |
| (no estaba) | Modo proxy con control de acciones y del flujo de datos | Los agentes con herramientas convierten el prompt injection en acciones reales (mandar correos, ejecutar comandos). Era el riesgo más importante que el plan no cubría |

## Hitos que quedan (propuesta)

| Hito | Cuándo | Qué |
| --- | --- | --- |
| H4 · Publicación | Noviembre de 2026 | Repositorio público en GitHub con licencia MIT, integración continua funcionando y primera versión publicada |
| H5 · Extensión del navegador | Noviembre de 2026 | Avisar y tapar datos dentro de la web de los chatbots (ChatGPT, Gemini, Claude...) usando el Guardián local |
| H6 · Evaluación final | Diciembre de 2026 | Repetir las medidas con el modelo 9B en la GPU del portátil, más trampas y herramientas en el ataque al agente y una prueba con usuarios |
| H7 · Memoria y presentación | Según el calendario de la asignatura | Memoria final y demostración en clase (`python -m guardian demo --pausa`) |

## Riesgos de la planificación

| Riesgo | Plan B |
| --- | --- |
| El modelo 9B va lento en el portátil | Qwen3.5 4B o 2B (los dos medidos) y, siempre, las reglas sin IA |
| No da tiempo a la extensión del navegador | El proxy, la web y el programa de terminal ya cubren el uso principal |
| Aparecen técnicas de ataque nuevas | Cada técnica nueva entra como regla con su caso de prueba, como el ASCII smuggling en la versión 0.3.0 |
