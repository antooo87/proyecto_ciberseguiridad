"""Módulo 1: escudo de datos sensibles."""

from .detectores import DetectorRegex, Hallazgo
from .escudo import Boveda, Escudo, ResultadoEscudo

__all__ = ["Boveda", "DetectorRegex", "Escudo", "Hallazgo", "ResultadoEscudo"]
