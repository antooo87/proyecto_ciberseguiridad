"""La web (Streamlit) se carga entera sin errores. Se salta si Streamlit no está instalado."""

from pathlib import Path

import pytest

prueba_streamlit = pytest.importorskip("streamlit.testing.v1")
WEB = Path(__file__).resolve().parent.parent / "app_web.py"


def test_la_web_se_carga_sin_errores():
    web = prueba_streamlit.AppTest.from_file(str(WEB), default_timeout=60)
    web.run()
    assert not web.exception
    titulos = [s.value for s in web.subheader]
    assert any("vería la IA" in t for t in titulos) and any("médico" in t for t in titulos)


def test_la_pestana_de_actividad_resume_el_registro(tmp_path, monkeypatch):
    from guardian import config
    from tests.test_actividad import SUCESOS, escribir
    escribir(tmp_path, SUCESOS)
    monkeypatch.setattr(config, "CARPETA_REGISTRO", str(tmp_path))
    web = prueba_streamlit.AppTest.from_file(str(WEB), default_timeout=60)
    web.run()
    next(r for r in web.radio if r.label == "Periodo").set_value("Todo").run()
    assert not web.exception
    metricas = {m.label: m.value for m in web.metric}
    assert metricas["Datos tapados"] == "10" and metricas["Documentos con trampas"] == "2"
    assert metricas["Acciones de agentes bloqueadas"] == "2"
