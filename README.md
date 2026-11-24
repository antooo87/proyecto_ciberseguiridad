# Proyecto de Ciberseguridad · Guardián IA

**Alumno:** Antonio De Mateo Bodegas · **Asignatura:** Proyectos de Ciberseguridad - Ciberejercicios · **Versión del software:** 0.5.0

Guardián IA es un programa que se instala en el ordenador y se pone **entre la persona y la IA**. Tapa los datos personales antes de que salgan, frena los documentos que esconden órdenes para la IA (prompt injection), avisa de las respuestas peligrosas y revisa la IA instalada en el PC. Además ayuda a preguntar mejor a la IA y dice si un SMS o un correo es una estafa. Lo que ve tus datos sin tapar funciona en local, con Ollama.

Se usa con un doble clic (una web local en su propia ventana), dentro de ChatGPT, Claude, Gemini y otros seis chatbots (extensión del navegador), desde la terminal y delante de agentes con herramientas (modo proxy).

## Qué hay en este repositorio

| Carpeta | Contenido |
| --- | --- |
| [`guardian_ia/`](guardian_ia/) | **El software**: código (`guardian/`), extensión del navegador (`extension/`), pruebas automáticas (`tests/`), ejemplos y casos reales, evaluación y documentación técnica (`docs/`). Instrucciones completas en [`guardian_ia/README.md`](guardian_ia/README.md) y novedades de cada versión en [`guardian_ia/CHANGELOG.md`](guardian_ia/CHANGELOG.md) |
| [`memoria/`](memoria/) | **La memoria**: planteamiento inicial, memoria de la entrega intermedia (Word y PDF) y capturas (las de la entrega final, en [`memoria/capturas/entrega_final/`](memoria/capturas/entrega_final/)) |
| [`.github/workflows/`](.github/workflows/) | Integración continua: en cada cambio, las pruebas en Windows y Linux, la extensión en un Chromium de verdad y el instalador en un Windows limpio |

## Instalación (Windows)

Requisitos: Python 3.11 o superior. Para usar la IA local, además, [Ollama](https://ollama.com) con un modelo (`qwen3.5:9b`; en un PC sin tarjeta gráfica potente, `qwen3.5:4b` o `qwen3.5:2b`). Sin Ollama funciona todo con reglas.

```powershell
cd guardian_ia
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

Después, doble clic en **«Guardián IA»** en el escritorio. A mano (o en Linux y macOS):

```powershell
cd guardian_ia
python -m venv .venv
.venv\Scripts\Activate.ps1          # en Linux/macOS: source .venv/bin/activate
pip install -e ".[web,dev]"
python -m guardian doctor
```

## Probarlo en un minuto

```powershell
python -m guardian demo                                    # los cuatro módulos, sin necesidad de Ollama
python -m guardian app                                     # la web en su ventana + el servicio de la extensión
python -m guardian estafa --carpeta ejemplos\casos_reales\3_bandeja_de_entrada   # 10 estafas y 3 correos normales
python -m guardian escanear ejemplos\casos_reales\1_carpeta_rrhh                 # documentos con datos y con trampas
python -m guardian mejorar "hazme un correo para mi jefe"  # qué le falta a tu pregunta y dos versiones mejores
python -m pytest                                           # 320 pruebas automáticas
```

## Resultados (resumen)

| Medida | Solo reglas | Reglas + Qwen3.5 9B (local) |
| --- | --- | --- |
| Escudo, prueba ciega: datos que se escapan | 37,8 % | **0 %** |
| Aduana, prueba ciega: ataques detectados (falsas alarmas) | 30 % (0 %) | **100 % (0 %)** |
| Agente atacado: veces que los datos llegan al atacante (sin Guardián, 10 de 10) | **0 de 10** | **0 de 10** |

Método, conjuntos públicos (CoNLL-2002 y BIPIA), el ataque completo al agente y qué medidas no son a ciegas: [`guardian_ia/docs/evaluacion.md`](guardian_ia/docs/evaluacion.md).

## Capturas

| ¿Es una estafa? Una bandeja de 13 correos | Revisar una carpeta antes de dársela a una IA |
| --- | --- |
| ![Bandeja de correos](memoria/capturas/entrega_final/fig05_web_bandeja.png) | ![Carpeta de RRHH](memoria/capturas/entrega_final/fig02_web_carpeta_rrhh.png) |
| **La extensión tapa los datos al pegar** | **«✨ Mejorar» dentro del chat** |
| ![Extensión](memoria/capturas/entrega_final/fig09_ext_pegado.png) | ![Mejorar](memoria/capturas/entrega_final/fig10_ext_mejorar.png) |

## Uso de IA en el desarrollo

El proyecto se ha desarrollado con apoyo de IA (Claude, de Anthropic, en conversación y como agente de programación). Qué se ha hecho con IA, con qué grado de automatización y cómo se ha validado está en [`guardian_ia/docs/uso_de_ia.md`](guardian_ia/docs/uso_de_ia.md).

## Seguridad del repositorio

No contiene credenciales, claves de API ni archivos `.env`. Las claves, DNI, IBAN y nombres que aparecen en las pruebas, la evaluación y los ejemplos (también en `ejemplos/casos_reales/`) son **inventados** y no funcionan en ningún servicio. La clave del servicio de la extensión se crea al azar en cada PC y se guarda fuera del repositorio.

Licencia MIT (ver [`guardian_ia/LICENSE`](guardian_ia/LICENSE)).
