"""Módulo 2: verificador de las respuestas de la IA.

Revisa lo que contesta la IA antes de enseñártelo: comandos peligrosos,
intentos de sacar tus datos en enlaces o imágenes, webs falsas, enlaces y
artículos inventados, peticiones de contraseñas y frases que el documento no
respalda.
"""

from .respaldo import JuezRespaldo
from .salida import HallazgoVerificacion, neutralizar_imagenes
from .verificador import InformeVerificacion, Verificador

__all__ = ["HallazgoVerificacion", "InformeVerificacion", "JuezRespaldo", "Verificador", "neutralizar_imagenes"]
