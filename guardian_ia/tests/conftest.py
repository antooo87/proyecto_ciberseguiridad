import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def registro_de_prueba(tmp_path_factory, monkeypatch):
    """Cada prueba apunta en un registro aparte. Si no, la página «Actividad» de tu PC enseñaría lo que hacen las
    pruebas (respuestas con PELIGRO, trampas, datos tapados) como si lo hubieras hecho tú."""
    from guardian import config
    carpeta = str(tmp_path_factory.mktemp("registro"))
    monkeypatch.setattr(config, "CARPETA_REGISTRO", carpeta)
    monkeypatch.setenv("GUARDIAN_REGISTRO", carpeta)  # por si una prueba arranca otro Python
