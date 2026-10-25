import importlib

import pytest

from guardian import terminal


@pytest.fixture(autouse=True)
def _dejar_como_estaba():
    yield
    importlib.reload(terminal)  # después de cada prueba, con la salida y las variables de verdad


def _recargar(monkeypatch, tty: bool, no_color: bool):
    monkeypatch.setattr("sys.stdout.isatty", lambda: tty)
    if no_color:
        monkeypatch.setenv("NO_COLOR", "1")
    else:
        monkeypatch.delenv("NO_COLOR", raising=False)
    return importlib.reload(terminal)


def test_colores_en_una_terminal(monkeypatch):
    t = _recargar(monkeypatch, tty=True, no_color=False)
    assert t.CON_COLOR and t.ROJO.startswith("\033[")


def test_sin_colores_si_la_salida_va_a_un_archivo(monkeypatch):
    t = _recargar(monkeypatch, tty=False, no_color=False)
    assert not t.CON_COLOR and t.ROJO == t.FIN == "" and t.COLOR_NIVEL["ALTO"] == ""


def test_sin_colores_con_no_color(monkeypatch):
    t = _recargar(monkeypatch, tty=True, no_color=True)
    assert not t.CON_COLOR and t.VERDE == ""
