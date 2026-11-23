import builtins

from guardian import doctor
from guardian.__main__ import main


def test_doctor_sin_ollama_funciona(capsys):
    assert main(["doctor", "--sin-ollama"]) in (0, 1)
    salida = capsys.readouterr().out
    assert "Python" in salida and "Librería ollama" in salida


def test_doctor_detecta_libreria_instalada_a_medias(monkeypatch):
    importar = builtins.__import__

    def falso(nombre, *args, **kwargs):
        if nombre == "streamlit.proto.RootContainer_pb2":
            raise ModuleNotFoundError("No module named 'streamlit.proto'", name="streamlit.proto")
        return importar(nombre, *args, **kwargs)

    monkeypatch.setattr(doctor.importlib, "import_module", lambda m: falso(m))
    streamlit = next(c for c in doctor._librerias() if c.nombre == "Librería streamlit")
    assert streamlit.estado == doctor.AVISO and "a medias" in streamlit.detalle
    assert "--force-reinstall" in streamlit.arreglo


def test_doctor_falta_libreria_imprescindible(monkeypatch):
    def falso(nombre):
        if nombre == "httpx":
            raise ModuleNotFoundError("No module named 'httpx'", name="httpx")
        return None

    monkeypatch.setattr(doctor.importlib, "import_module", falso)
    httpx = next(c for c in doctor._librerias() if c.nombre == "Librería httpx")
    assert httpx.estado == doctor.FALLO and "requirements.txt" in httpx.arreglo
