"""Piezas comunes del revisor: dónde buscar en el PC y cómo se apunta cada hallazgo."""

import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

GRAVEDADES = ("CRITICA", "ALTA", "MEDIA", "BAJA", "INFO")
# Cuánto resta cada hallazgo a la nota de salud (sobre 100)
PESO_NOTA = {"CRITICA": 40, "ALTA": 15, "MEDIA": 5, "BAJA": 1, "INFO": 0}


@dataclass
class HallazgoRevisor:
    area: str  # extensiones, conectores, modelos, red, secretos
    gravedad: str
    titulo: str
    detalle: str
    recomendacion: str
    ruta: str = ""

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Ubicaciones:
    """Las carpetas donde los programas guardan sus cosas.

    En Windows:  home = C:\\Users\\tú, appdata = ...\\AppData\\Roaming, local = ...\\AppData\\Local
    En macOS:    appdata y local = ~/Library/Application Support
    En Linux:    appdata y local = ~/.config

    Con `simuladas(raiz)` se usa una carpeta cualquiera como si fuera un PC con
    Windows: así se puede probar el revisor con un "PC de prueba" sin tocar el real.
    """
    home: Path
    appdata: Path
    local: Path
    sistema: str  # windows, mac o linux
    simulado: bool = False

    @classmethod
    def del_sistema(cls) -> "Ubicaciones":
        home = Path.home()
        if os.name == "nt":
            appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
            local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
            return cls(home, appdata, local, "windows")
        if sys.platform == "darwin":
            soporte = home / "Library" / "Application Support"
            return cls(home, soporte, soporte, "mac")
        config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        return cls(home, config, config, "linux")

    @classmethod
    def simuladas(cls, raiz) -> "Ubicaciones":
        raiz = Path(raiz)
        return cls(raiz, raiz / "AppData" / "Roaming", raiz / "AppData" / "Local", "windows", True)


def leer_json(ruta) -> dict | list | None:
    """Lee un JSON aunque tenga comentarios o comas al final (como settings.json de VS Code)."""
    try:
        texto = Path(ruta).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    # Quita comentarios // y /* */ que no estén dentro de una cadena, y comas sobrantes
    sin_comentarios = re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*[\s\S]*?\*/',
                             lambda m: m.group(1) or "", texto)
    sin_comas = re.sub(r",(\s*[}\]])", r"\1", sin_comentarios)
    try:
        return json.loads(sin_comas)
    except json.JSONDecodeError:
        return None


def tapar_secreto(valor: str) -> str:
    """Enseña solo el principio y el final de un secreto: sk-p…9xQz."""
    valor = str(valor)
    if len(valor) <= 8:
        return "*" * len(valor)
    return f"{valor[:4]}…{valor[-4:]}"
