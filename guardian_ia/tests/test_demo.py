"""La demostración (python -m guardian demo) funciona sin Ollama y enseña lo que promete."""

import json

from guardian import demo
from guardian.__main__ import main


def test_la_demo_recorre_los_cinco_pasos_sin_ollama(capsys):
    assert main(["demo"]) == 0
    salida = capsys.readouterr().out
    for paso in ("1/5  ESCUDO", "2/5  ADUANA", "3/5  VERIFICADOR", "4/5  REVISOR", "5/5  CONTROL DE ACCIONES"):
        assert paso in salida
    assert "[DNI_1]" in salida and "imagen bloqueada por el Guardián" in salida
    assert "He bloqueado la acción «enviar_correo»" in salida
    assert "Lucía recibe" in salida and "549 €" in salida  # y aun así Lucía recibe las ofertas
    assert "✓ Pasa" in salida and "ana.garcia@gmail.com" in salida
    assert "ha frenado el robo de datos" in salida


def test_en_la_demo_la_ia_no_ve_los_datos_pero_el_ataque_se_para():
    datos, ia = demo._agente(demo.PETICION, demo._obedecer_a_la_web)
    visto = json.dumps(ia.visto, ensure_ascii=False)
    assert "12345678Z" not in visto and "lucia.moreno@gmail.com" not in visto
    assert ia.pedido["para"].startswith("[EMAIL_")  # la IA pide con marcadores...
    bloqueada = datos["guardian"]["acciones_bloqueadas"][0]
    assert demo.ATACANTE in bloqueada["motivo"]  # ...y el Guardián mira el destino real
    assert not datos["choices"][0]["message"].get("tool_calls")
    assert datos["choices"][0]["message"]["content"].startswith(demo.CONTESTACION)  # la IA sigue sin la acción


def test_en_la_demo_si_tu_das_la_direccion_la_accion_pasa():
    peticion = f"Lee {demo.WEB} y manda las ofertas a ana.garcia@gmail.com."
    datos, _ = demo._agente(peticion, demo._hacer_lo_que_pides)
    llamada = datos["choices"][0]["message"]["tool_calls"][0]
    assert json.loads(llamada["function"]["arguments"])["para"] == "ana.garcia@gmail.com"
    assert datos["guardian"]["acciones_bloqueadas"] == []
