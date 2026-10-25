"""Módulo 4: revisor de la IA instalada en el PC (el "médico" de la IA).

Revisa, sin cambiar nada: extensiones de IA del navegador, conectores MCP de
las apps de IA, modelos descargados con código escondido o plantillas
envenenadas, si Ollama está abierto a la red y si hay claves de IA a la vista.
"""

from .comun import HallazgoRevisor, Ubicaciones
from .demo import crear_pc_de_prueba
from .revisor import InformeRevisor, Revisor

__all__ = ["HallazgoRevisor", "InformeRevisor", "Revisor", "Ubicaciones", "crear_pc_de_prueba"]
