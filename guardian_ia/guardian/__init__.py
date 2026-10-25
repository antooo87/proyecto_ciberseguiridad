"""Guardián IA: un programa local que se pone entre el usuario y la IA.

Módulos:
  1. escudo      -> tapa los datos sensibles antes de que lleguen a la IA y los restaura después
  2. verificador -> revisa las respuestas: comandos peligrosos, enlaces falsos o inventados,
                    robo de datos por enlaces, frases que el documento no respalda
  3. aduana      -> revisa documentos en busca de prompt injection
  4. revisor     -> revisa la IA instalada en el PC: extensiones, conectores MCP, modelos, Ollama
"""

__version__ = "0.3.0"
