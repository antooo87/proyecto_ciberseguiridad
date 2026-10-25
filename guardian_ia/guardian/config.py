"""Ajustes del Guardián. Se pueden cambiar con variables de entorno."""

import os

# Modelo de Ollama que responde al usuario
MODELO = os.environ.get("GUARDIAN_MODELO", "qwen3.5:9b")

# Modelo que usa el detector con IA (nombres, direcciones) y el juez. Siempre local. Puede ser más pequeño.
MODELO_DETECTOR = os.environ.get("GUARDIAN_MODELO_DETECTOR", MODELO)

# Dirección de Ollama en tu PC
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not OLLAMA_HOST.startswith("http"):
    OLLAMA_HOST = "http://" + OLLAMA_HOST
if OLLAMA_HOST.count(":") == 1:  # "http://127.0.0.1" sin puerto
    OLLAMA_HOST += ":11434"
OLLAMA_HOST = OLLAMA_HOST.replace("//0.0.0.0", "//127.0.0.1")  # 0.0.0.0 vale para escuchar, no para conectar

# IA que responde al usuario: ollama (en tu PC), ollama-cloud u openai (cualquier API compatible).
# Si no es local, solo recibe el texto con los datos ya tapados.
PROVEEDOR = os.environ.get("GUARDIAN_PROVEEDOR", "ollama")
MODELO_NUBE = os.environ.get("GUARDIAN_MODELO_NUBE", "gpt-oss:120b")
URL_OPENAI = os.environ.get("GUARDIAN_URL", "http://127.0.0.1:1234/v1")  # LM Studio, por defecto

# Carpeta del registro de auditoría
CARPETA_REGISTRO = os.environ.get("GUARDIAN_REGISTRO", "registro")
