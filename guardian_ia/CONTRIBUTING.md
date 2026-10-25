# Cómo contribuir

Gracias por echar una mano. El proyecto es pequeño y quiere seguir siendo fácil de leer.

## Preparar el entorno

```powershell
python -m venv .venv
.venv\Scripts\activate          # en Linux: source .venv/bin/activate
pip install -e ".[web,dev]"
python -m pytest                # todas las pruebas, sin Ollama (usan una IA falsa)
ruff check .                    # estilo y errores típicos
```

## Reglas del proyecto

- **Cada cambio va con su prueba.** Una regla nueva del escudo o de la aduana lleva su caso en `tests/` y una fila en [`docs/casos_de_prueba.md`](docs/casos_de_prueba.md). Si es un ataque nuevo, mejor todavía con un ejemplo en `ejemplos/`.
- **La prueba ciega no se toca.** Las reglas se ajustan mirando el conjunto de desarrollo (`evaluacion/datos_*.jsonl`), nunca `evaluacion/ciega_*.jsonl`: si no, los resultados dejarían de ser honestos.
- **Solo datos inventados.** Nada de DNIs, correos o claves de verdad, ni en pruebas ni en ejemplos. Las claves de ejemplo se escriben por trozos (`"sk-" + "..."`) para que no parezcan secretos reales.
- **Nada sale del PC sin tapar.** Las piezas que ven datos sin tapar (detector, jueces) solo pueden usar una IA local.
- **Pocas dependencias.** Cada librería nueva es una puerta para un ataque a la cadena de suministro: explica en el pull request por qué hace falta.
- **Sencillo y en español.** Código, comentarios y mensajes en español, explicados para alguien que está aprendiendo.

## Avisar de un fallo

- Un fallo normal: una issue con los pasos para reproducirlo.
- Una forma de saltarse el Guardián: por privado, como explica [`SECURITY.md`](SECURITY.md).
