"""Módulo 3: aduana de documentos contra prompt injection."""

from .aduana import Aduana, InformeAduana, leer_documento
from .lectores import ErrorLectura, Lectura, Peligro, TextoOculto, leer

__all__ = ["Aduana", "ErrorLectura", "InformeAduana", "Lectura", "Peligro", "TextoOculto", "leer", "leer_documento"]
