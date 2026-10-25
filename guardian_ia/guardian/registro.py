"""Registro de auditoría: qué ha hecho el Guardián, SIN guardar los datos.

Cada línea del archivo es un JSON (formato JSONL) con la hora, cuántos
datos de cada tipo se taparon, el riesgo de los documentos, etc.
Nunca se escribe el dato real: un registro con DNIs dentro sería
otra fuga de datos.
"""

import json
import os
from datetime import datetime

from . import config


class Registro:
    def __init__(self, carpeta: str | None = None, activo: bool = True):
        self.carpeta = carpeta or config.CARPETA_REGISTRO
        self.activo = activo

    def apuntar(self, evento: str, **detalles) -> None:
        if not self.activo:
            return
        os.makedirs(self.carpeta, exist_ok=True)
        ahora = datetime.now()
        linea = {"fecha": ahora.isoformat(timespec="seconds"), "evento": evento, **detalles}
        ruta = os.path.join(self.carpeta, f"guardian_{ahora:%Y-%m-%d}.jsonl")
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
