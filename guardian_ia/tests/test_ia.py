import json

import httpx
import pytest

from guardian.aduana.juez_ia import JuezIA
from guardian.escudo.detector_ia import DetectorIA
from guardian.ia import ClienteIA, ClienteOpenAI, ErrorIA, crear_cliente, es_direccion_local
from guardian.nucleo import Guardian
from guardian.registro import Registro
from tests.falsa_ia import IAFalsa


def test_direcciones_locales():
    assert es_direccion_local("http://127.0.0.1:11434") and es_direccion_local("localhost:1234")
    assert not es_direccion_local("https://ollama.com") and not es_direccion_local("http://192.168.1.10:11434")


def test_cliente_openai_manda_esquema_estricto_y_clave():
    recibido = {}

    def servidor(peticion: httpx.Request):
        recibido["cuerpo"] = json.loads(peticion.content)
        recibido["clave"] = peticion.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": true}'}}]})

    c = ClienteOpenAI("modelo-x", "https://api.ejemplo.com/v1", api_key="clave-falsa",
                      transporte=httpx.MockTransport(servidor))
    assert c.chat([{"role": "user", "content": "hola"}], formato={"type": "object", "properties": {
        "ok": {"type": "boolean"}}, "required": ["ok"]}, temperatura=0) == '{"ok": true}'
    esquema = recibido["cuerpo"]["response_format"]["json_schema"]["schema"]
    assert esquema["additionalProperties"] is False and recibido["clave"] == "Bearer clave-falsa"
    assert recibido["cuerpo"]["temperature"] == 0 and not c.es_local


def test_cliente_openai_error_se_convierte_en_errorIA():
    c = ClienteOpenAI("m", "http://127.0.0.1:1/v1", transporte=httpx.MockTransport(
        lambda p: httpx.Response(500, text="fallo")))
    with pytest.raises(ErrorIA):
        c.chat([{"role": "user", "content": "hola"}])


def test_ollama_en_la_nube_necesita_clave(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    with pytest.raises(ErrorIA):
        crear_cliente("ollama-cloud")
    monkeypatch.setenv("OLLAMA_API_KEY", "clave-falsa")
    nube = crear_cliente("ollama-cloud")
    assert nube.host == "https://ollama.com" and not nube.es_local


def test_lo_que_ve_datos_sin_tapar_no_puede_ser_remoto():
    remota = ClienteIA("m", host="https://ollama.com", api_key="x")
    with pytest.raises(ValueError):
        DetectorIA(remota)
    with pytest.raises(ValueError):
        JuezIA(remota)


def test_con_ia_remota_se_avisa(tmp_path):
    ia = IAFalsa(["ok"])
    ia.es_local, ia.host = False, "https://api.ejemplo.com"
    r = Guardian(ia, registro=Registro(str(tmp_path))).preguntar("mi DNI es 12345678Z")
    assert any("fuera de tu PC" in a for a in r.avisos)
    assert "12345678Z" not in str(ia.recibido)
