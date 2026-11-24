# Herramientas parecidas e investigación

Qué existe ya, qué hace cada cosa y qué aporta el Guardián. Las herramientas se agrupan por el problema que resuelven, que coincide con los módulos del proyecto.

## 1. Proteger los datos que se mandan a la IA (módulo 1)

| Herramienta | Qué hace | IA | Dónde | Diferencia con el Guardián |
| --- | --- | --- | --- | --- |
| [Microsoft Presidio](https://github.com/microsoft/presidio) | Librería de detección y anonimización de datos personales: reglas, validaciones y reconocimiento de entidades (spaCy, transformers) | Modelos NER | Local | Es una pieza para programadores, no un programa para usar la IA. Los formatos españoles (DNI, NIE) hay que añadirlos |
| [LLM Guard](https://github.com/protectai/llm-guard) (Protect AI) | "Escáneres" de entrada y salida: anonimizar con bóveda y desanonimizar, prompt injection con un clasificador DeBERTa, secretos... | Clasificadores | Local | Era la más parecida, pero el repositorio está archivado y sin mantenimiento en 2026 |
| DLP corporativos (Microsoft Purview, Netskope, Nightfall...) | Impiden pegar datos en ChatGPT y similares en la empresa | Sí | Nube, de pago | Pensados para empresas, con licencia y consola; el usuario normal no los tiene |
| [LiteLLM Proxy](https://github.com/BerriAI/litellm) | Proxy compatible con OpenAI hacia más de 100 proveedores, con "guardrails" enchufables (Presidio, Lakera...) | Según el plugin | Local o servidor | Es la misma idea que el modo proxy del Guardián, pero para equipos técnicos: hay que montar y configurar cada servicio por separado |

## 2. Prompt injection en documentos (módulo 3)

| Herramienta | Qué hace | IA | Dónde | Diferencia |
| --- | --- | --- | --- | --- |
| [Llama Prompt Guard 2](https://www.llama.com/docs/model-cards-and-prompt-formats/prompt-guard/) (Meta, 86M y 22M) | Clasificador pequeño de jailbreaks y prompt injection | Sí (BERT) | Local | Solo da una probabilidad: no explica por qué ni mira el formato del documento (texto blanco, oculto...) |
| [Lakera Guard](https://www.lakera.ai) | API de detección de prompt injection y fugas | Sí | Nube, de pago | Hay que mandarle el texto a un tercero: justo lo que el Guardián evita |
| Azure AI Content Safety, [Prompt Shields](https://learn.microsoft.com/azure/ai-services/content-safety/concepts/jailbreak-detection) | Detecta ataques en el mensaje del usuario y en documentos | Sí | Nube de Microsoft | Igual: el documento sale del PC |
| [NVIDIA NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) | Marco para programar "raíles" de entrada, salida y diálogo | Sí | Local o servidor | Muy potente pero para desarrolladores de chatbots; hay que escribir las reglas en su lenguaje (Colang) |
| [IBM Granite Guardian](https://www.ibm.com/granite/docs/models/guardian) | Modelos que detectan riesgos: daño, jailbreak, respuestas no apoyadas en el contexto, llamadas a funciones inventadas | Sí (LLM) | Local | Es un modelo, no un programa: se podría usar como juez dentro del Guardián |
| [oletools](https://github.com/decalage2/oletools), [pdfid](https://blog.didierstevens.com/programs/pdf-tools/) | Análisis clásico de Office y PDF maliciosos: macros, objetos, JavaScript | No | Local | Buscan malware, no órdenes para una IA. La aduana reutiliza su idea (pdfid) y añade el texto escondido |

## 3. Revisar lo que responde la IA (módulo 2)

| Herramienta | Qué hace | Diferencia |
| --- | --- | --- |
| [Guardrails AI](https://github.com/guardrails-ai/guardrails) | Validadores de la salida (formato, toxicidad, datos...) | Para programadores que montan su propia app |
| RAGAS, TruLens y similares | Métricas de "fidelidad" (si la respuesta sale del contexto) para evaluar sistemas RAG | Se usan para medir en laboratorio, no para avisar al usuario en cada respuesta. El juez de respaldo del Guardián usa la misma idea |
| Navegadores y antivirus (Safe Browsing, SmartScreen) | Avisan al abrir una web peligrosa conocida | Actúan cuando ya has hecho clic; el verificador avisa antes, al leer la respuesta, y detecta imitaciones nuevas por parecido |

## 4. Revisar la IA instalada en el PC (módulo 4)

| Herramienta | Qué hace | Diferencia |
| --- | --- | --- |
| [ModelScan](https://github.com/protectai/modelscan) (Protect AI), [picklescan](https://github.com/mmaitre314/picklescan), [fickling](https://github.com/trailofbits/fickling) | Analizan archivos de modelos (pickle, H5...) buscando código | Solo miran modelos sueltos que les pasas; no las plantillas GGUF ni los modelos de Ollama ni el resto del PC |
| [mcp-scan](https://invariantlabs.ai/blog/introducing-mcp-scan) (Invariant Labs) | Revisa los servidores MCP configurados buscando "tool poisoning" | Se centra en las descripciones de las herramientas MCP; no mira extensiones, modelos ni la red |
| Antivirus | Detecta malware conocido | No entiende permisos de conectores, plantillas de chat ni exposición de Ollama |

## 5. Para personas: extensiones de privacidad y mejoradores de preguntas (revisado el 24-nov-2026)

Las suites de seguridad para IA son para grandes empresas: Lakera (Check Point), Prompt Security (SentinelOne), Pangea (CrowdStrike), Protect AI (Palo Alto Networks)... Según [Forrester](https://www.forrester.com/blogs/securing-ais-ma-feeding-frenzy-is-on), ocho fabricantes gastaron más de 2.000 millones de dólares en 18 meses comprando estas startups. Para una persona o una pyme lo que hay son extensiones pequeñas:

| Extensión | Qué hace | En local | Webs | Usuarios (tienda, nov-2026) |
| --- | --- | --- | --- | --- |
| [ChatWall](https://chromewebstore.google.com/detail/chatwall-anonymise-mask-p/fgkiepldibfgepiohbjcelgklobakped) | Tapa nombres, correos, teléfonos y tarjetas | Eso dice | ChatGPT, Gemini y otras | 81 |
| [ChatGPT Privacy Shield](https://chromewebstore.google.com/detail/dphnbciedkeahabnlioegndnnkkejigb) | Tapa datos personales y secretos | Sí | Solo ChatGPT | 18 |
| [Rescriber](https://chromewebstore.google.com/detail/oglddlncokahjddccgjnnpdlgdbijcbl) | Tapa datos con un modelo pequeño en el navegador (investigación de Northeastern) | Sí | Solo ChatGPT | 17 |
| [Offsend](https://addons.mozilla.org/firefox/addon/offsend/) | Tapa claves, contraseñas y datos personales | Sí | 7 chatbots | 2 |
| [Casper](https://arxiv.org/html/2408.07004v1) (artículo, 2024) | Reglas, un modelo de nombres y Llama 3 en el navegador | Sí | Solo ChatGPT, en inglés | Prototipo |

Ninguna reconoce un DNI, un NIE o un IBAN con su comprobación, ninguna mira los documentos ni las respuestas y casi todas son solo para ChatGPT.

Para **mejorar la pregunta** hay extensiones como [Prompt Enhancer](https://chromewebstore.google.com/detail/prompt-enhancer/fbdfiklggfifedgcmlonhkcjfhodbloo) (reescribe con rol, tarea, contexto y formato; tu pregunta va a su servidor o a tu clave de Anthropic), [PromptEnhance](https://chromewebstore.google.com/detail/promptenhance/ajfnkdejpiigjhedggbinfpnnaboilho) o [Frompt](https://chromewebstore.google.com/detail/frompt-ai-prompt-enhancer/adlindblhlkehpgkobgcbcbheodooifc) (un botón encima del cuadro, como el del Guardián). Ninguna tapa tus datos antes de reescribir, todas mandan la pregunta a un servidor y ninguna te enseña dos versiones para elegir ni te dice qué le falta. Ese es el hueco de «✨ Mejorar mi pregunta».

## 6. Evaluación y ataque (para medir)

| Herramienta o conjunto | Uso en el proyecto |
| --- | --- |
| [BIPIA](https://arxiv.org/abs/2312.14197) (Microsoft, Yi et al.) | Prompt injection indirecta en correos, tablas, webs y código. Se usa su tarea de correos para medir la aduana |
| [AgentDojo](https://arxiv.org/abs/2406.13352) (ETH Zúrich, Debenedetti et al.) | Ataques a agentes con herramientas. Referencia para el modo proxy (trabajo futuro: medirlo con AgentDojo) |
| CoNLL-2002 (Tjong Kim Sang) | Noticias en español con las personas etiquetadas. Se usa para medir el detector de nombres |
| [garak](https://github.com/NVIDIA/garak) (NVIDIA), [PyRIT](https://github.com/Azure/PyRIT) (Microsoft) | Escáneres que atacan a un modelo para ver si cae. Útiles para el trabajo futuro |

## 7. Investigación en la que se apoya el diseño

- **Prompt injection indirecta.** Greshake et al. (2023), [*Not what you've signed up for*](https://arxiv.org/abs/2302.12173), mostraron que una web o un correo puede dar órdenes a una IA integrada en una aplicación. Es el origen del módulo 3.
- **Separar datos de órdenes.** Hines et al. (2024), [*Spotlighting*](https://arxiv.org/abs/2403.14720), marcan el documento para que el modelo sepa que es solo información. El Guardián lo aplica con las etiquetas `<documento>`, las marcas aleatorias de los jueces y, en el modo proxy, con `--marcar-datos` sobre los resultados de herramientas (las dos variantes del artículo: delimitar y marcar cada palabra). En el ataque al agente (`evaluacion.md`), con el 2B evitó todos los intentos de robo, pero el 9B lo siguió intentando las 10 veces: ayuda, pero no basta sola.
- **Defensa por diseño.** Debenedetti et al. (2025), [*Defeating Prompt Injections by Design* (CaMeL)](https://arxiv.org/abs/2503.18813), y el patrón "dual LLM" de Simon Willison: lo que viene de una fuente no fiable no puede disparar acciones. Es la base del "contexto contaminado" del modo proxy y, en versión sencilla, del control de destinos: CaMeL apunta de dónde viene cada dato y decide a dónde puede ir.
- **La "tríada letal".** [Simon Willison (2025)](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/): un agente con datos privados, contenido no fiable y forma de comunicarse hacia fuera puede ser usado para robar datos. El Guardián rompe los tres lados: el escudo quita los datos, la aduana limpia el contenido y el verificador corta la salida (enlaces, imágenes, acciones).
- **Ataques reales que se han tenido en cuenta:**
  - EchoLeak (CVE-2025-32711): un correo hacía que Microsoft 365 Copilot sacara datos sin que el usuario hiciera nada.
  - [ASCII smuggling contra Microsoft 365 Copilot](https://www.theregister.com/2024/08/28/microsoft_copilot_copirate) (Johann Rehberger, 2024): órdenes y datos escritos con "etiquetas" Unicode, letras que no se ven en pantalla pero la IA sí lee. La aduana las traduce y el verificador avisa si aparecen en una respuesta. Es el ejemplo `resena_con_texto_invisible.txt`.
  - [Artículos científicos con órdenes escondidas](https://www.schneier.com/blog/archives/2025/07/hiding-prompt-injections-in-academic-papers.html) en blanco para que la IA revisora diera buena nota (2025). Es el ejemplo `articulo_con_trampa.pdf`.
  - El paquete `postmark-mcp` (2025), primer servidor MCP malicioso conocido: mandaba copia oculta de todos los correos al atacante. Está en la lista negra del revisor.
  - Plantillas de chat envenenadas en archivos GGUF ([Pillar Security, 2025](https://www.pillar.security/blog/llm-backdoors-at-the-inference-level-the-threat-of-poisoned-templates)) y modelos con pickle roto para esquivar los escáneres (nullifAI, ReversingLabs, 2025).
  - [El resumen de Gemini en Gmail engañado con texto escondido](https://0din.ai/blog/phishing-for-gemini) (2025): letra de tamaño 0 y blanca con un falso aviso de seguridad que la IA repetía al resumir el correo. Es el correo `13_boletin_con_aviso_escondido.eml` de los casos reales, y el lector de correos lo separa.
  - Fallos de Ollama: DNS rebinding ([CVE-2024-28224](https://www.nccgroup.com/research/technical-advisory-ollama-dns-rebinding-attack-cve-2024-28224/)) y Probllama (CVE-2024-37032).

## 8. Qué aporta el Guardián

Ninguna de las herramientas anteriores junta las cuatro cosas en un programa que pueda usar una persona normal en su PC:

1. **Todo local y gratis.** Lo que ve datos sin tapar no sale del ordenador, y eso lo obliga el código.
2. **Pensado para España.** DNI, NIE, IBAN, matrículas y teléfonos españoles con su validación, y reglas en español.
3. **Explica cada aviso** en lenguaje sencillo, en vez de dar solo una probabilidad.
4. **Mira el formato de los documentos**, no solo el texto: lo que tú no ves no se lo pasa a la IA.
5. **Cubre el antes, el durante y el después**: el PC (revisor), el documento (aduana), el mensaje (escudo) y la respuesta y las acciones (verificador y proxy).
6. **Medido con conjuntos públicos** y con un método honesto (desarrollo, prueba ciega y conjuntos de otros investigadores).
7. **Para quien no sabe de informática**: se abre con un doble clic, ayuda a preguntar mejor sin regalar datos y enseña a ver las estafas que llegan por SMS, WhatsApp o correo.
