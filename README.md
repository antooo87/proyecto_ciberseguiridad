# Proyecto de Ciberseguridad · Guardián IA

**Alumno:** Antonio De Mateo Bodegas · **Asignatura:** Proyectos de Ciberseguridad · **Versión del software:** 0.3.0

Guardián IA es un programa que se instala en el ordenador y se pone **entre el usuario y la IA**. Tapa los datos personales antes de que salgan, frena los documentos que esconden órdenes para la IA (prompt injection), avisa de las respuestas peligrosas y revisa la IA instalada en el PC. Lo que ve tus datos sin tapar funciona en local, con Ollama.

## Qué hay en este repositorio

| Carpeta | Contenido |
| --- | --- |
| [`guardian_ia/`](guardian_ia/) | **El software**: código (`guardian/`), pruebas automáticas (`tests/`), ejemplos, evaluación y documentación técnica (`docs/`). Instrucciones completas en [`guardian_ia/README.md`](guardian_ia/README.md) |
| [`memoria/`](memoria/) | **La memoria**: planteamiento inicial, memoria de la entrega intermedia (Word y PDF) y capturas de las pruebas (`memoria/capturas/`) |

## Instalación y ejecución rápida (Windows)

Requisitos: Python 3.11 o superior. Para usar la IA local, además, [Ollama](https://ollama.com) con un modelo (`ollama pull qwen3.5:9b`, o `qwen3.5:2b` en un PC sin tarjeta gráfica potente).

```powershell
cd guardian_ia
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m guardian demo        # los cuatro módulos en un minuto, sin necesidad de Ollama
python -m pytest               # 146 pruebas automáticas
streamlit run app_web.py       # web de la demo en http://localhost:8501
python -m guardian chat --ia   # chat protegido con la IA local (necesita Ollama)
```

En Linux o macOS, el entorno se activa con `source .venv/bin/activate`.

## Capturas

| Escudo de datos | Aduana de documentos |
| --- | --- |
| ![Escudo](memoria/capturas/web_01_escudo.png) | ![Aduana](memoria/capturas/term_03_aduana.png) |
| **Control de acciones de un agente** | **Pruebas automáticas** |
| ![Agente](memoria/capturas/term_06_demo_agente.png) | ![Tests](memoria/capturas/term_01_tests.png) |

Todas las capturas, explicadas, están en la memoria ([PDF](memoria/2_Memoria_entrega_intermedia_Guardian_IA.pdf)).

## Seguridad del repositorio

No contiene credenciales, claves de API ni archivos `.env`. Las claves, DNI, IBAN y nombres que aparecen en `guardian_ia/tests/` y `guardian_ia/evaluacion/` son **inventados**, para probar el detector.

Licencia MIT (ver [`guardian_ia/LICENSE`](guardian_ia/LICENSE)).
