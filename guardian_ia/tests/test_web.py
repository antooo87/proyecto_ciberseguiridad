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
