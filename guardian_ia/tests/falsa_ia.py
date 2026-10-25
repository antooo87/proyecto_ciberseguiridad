"""Una IA de mentira para los tests: no necesita Ollama y responde lo que le digamos."""

import json


class IAFalsa:
    modelo = "ia-falsa"

    def __init__(self, respuestas=None, error=None):
        self.respuestas = list(respuestas or [])
        self.error = error
        self.recibido = []  # todo lo que le llega, para comprobar que NO ve datos reales

    def chat(self, mensajes, formato=None, temperatura=None):
        self.recibido.append(mensajes)
        if self.error:
            raise self.error
        respuesta = self.respuestas.pop(0) if self.respuestas else "vale"
        return json.dumps(respuesta) if isinstance(respuesta, dict) else respuesta
