"""La web (Streamlit) se carga entera sin errores. Se salta si Streamlit no está instalado."""

from pathlib import Path

import pytest

prueba_streamlit = pytest.importorskip("streamlit.testing.v1")
WEB = Path(__file__).resolve().parent.parent / "app_web.py"


def abrir(pagina=None):
    """Abre la web en una página (la de inicio si no se dice cuál)."""
    web = prueba_streamlit.AppTest.from_file(str(WEB), default_timeout=60)
    if pagina:
        web.session_state["ir_a"] = pagina
    return web.run()


def test_la_portada_se_carga_sin_errores():
    web = abrir()
    assert not web.exception
    assert web.title[0].value == "🛡️ Guardián IA"
    assert {m.label for m in web.metric} >= {"Datos tapados (7 días)", "Preguntas mejoradas"}


@pytest.mark.parametrize("pagina, titulo", [
    ("escudo", "vería la IA"), ("mejorar", "Mejorar mi pregunta"), ("chat", "sin darle tus datos"),
    ("verificar", "fiar de esta respuesta"), ("aduana", "esconde órdenes"), ("carpeta", "darle estos documentos"),
    ("revisar", "médico"), ("actividad", "ha hecho el Guardián"), ("resultados", "evaluación"),
    ("estafa", "¿Es una estafa?"), ("aprende", "¿Lo detectas?"),
])
def test_cada_pagina_se_carga_sin_errores(pagina, titulo):
    web = abrir(pagina)
    assert not web.exception
    assert any(titulo in s.value for s in web.subheader)


def test_mejorar_mi_pregunta_en_la_web():
    web = abrir("mejorar")
    next(b for b in web.button if b.label == "Mejorar").click().run()
    assert not web.exception
    assert web.metric[0].label == "Nota de tu pregunta" and web.metric[0].value == "30/100"
    versiones = [c.value for c in web.code]
    assert len(versiones) == 2 and versiones[0].startswith("Ayúdame con «escribe aquí de qué se trata».")


def test_la_pestana_de_actividad_resume_el_registro(tmp_path, monkeypatch):
    from guardian import config
    from tests.test_actividad import SUCESOS, escribir
    escribir(tmp_path, SUCESOS)
    monkeypatch.setattr(config, "CARPETA_REGISTRO", str(tmp_path))
    web = abrir("actividad")
    next(r for r in web.radio if r.label == "Periodo").set_value("Todo").run()
    assert not web.exception
    metricas = {m.label: m.value for m in web.metric}
    assert metricas["Datos tapados"] == "10" and metricas["Documentos con trampas"] == "2"
    assert metricas["Acciones de agentes bloqueadas"] == "2"


def test_guardian_web_solo_escucha_en_este_pc(monkeypatch):
    import subprocess

    from guardian.__main__ import main
    llamadas = []
    monkeypatch.setattr(subprocess, "call", lambda orden, cwd: llamadas.append((orden, cwd)) or 0)
    assert main(["web", "--puerto", "8599", "--sin-navegador"]) == 0
    orden, carpeta = llamadas[0]
    assert orden[orden.index("--server.address") + 1] == "127.0.0.1"
    assert orden[orden.index("--browser.gatherUsageStats") + 1] == "false"
    assert orden[orden.index("--server.port") + 1] == "8599" and Path(carpeta) == WEB.parent


def test_la_configuracion_de_la_web_no_sale_del_pc():
    import tomllib
    ajustes = tomllib.loads((WEB.parent / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert ajustes["server"]["address"] == "127.0.0.1" and ajustes["browser"]["gatherUsageStats"] is False


def test_es_una_estafa_en_la_web():
    web = abrir("estafa")
    next(b for b in web.button if b.label == "Analizar").click().run()
    assert not web.exception
    assert any("Casi seguro que es una estafa" in e.value and "paquetería" in e.value for e in web.error)


def test_el_juego_cuenta_los_aciertos():
    web = abrir("aprende")
    juego = web.session_state["juego"]
    from guardian.escuela import MENSAJES
    es_estafa = MENSAJES[juego["orden"][0]].es_estafa
    next(b for b in web.button if b.label == ("🚨 Es una estafa" if es_estafa else "✅ Es de fiar")).click().run()
    next(b for b in web.button if b.label == "Siguiente ➡️").click().run()
    assert not web.exception
    assert web.session_state["juego"]["n"] == 1 and web.session_state["juego"]["aciertos"] == 1


def test_guardian_app_arranca_la_web_y_el_servicio(monkeypatch, capsys):
    import subprocess

    import guardian.__main__ as programa
    arrancadas = []

    class WebFalsa:
        def __init__(self, orden, cwd):
            arrancadas.append((orden, cwd))

        def wait(self):
            return 0

        def terminate(self):
            pass

    monkeypatch.setattr(subprocess, "Popen", WebFalsa)
    monkeypatch.setattr(programa, "_esperar_web", lambda url: True)
    assert programa.main(["app", "--sin-ventana", "--puerto", "8598", "--puerto-servicio", "0"]) == 0
    orden, carpeta = arrancadas[0]
    assert orden[orden.index("--server.address") + 1] == "127.0.0.1" and "8598" in orden
    assert Path(carpeta) == WEB.parent
    salida = capsys.readouterr().out
    assert "Servicio para la extensión del navegador encendido" in salida and "Web abierta" in salida
