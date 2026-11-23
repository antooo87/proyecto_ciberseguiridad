"""Panel de actividad: resume el registro sin enseñar (ni guardar) ningún dato."""

import json
import threading
from datetime import date

from guardian.__main__ import main
from guardian.actividad import leer_registro
from guardian.nucleo import Guardian
from guardian.registro import Registro
from guardian.servicio import ServicioGuardian, ServidorServicio
from tests.falsa_ia import IAFalsa
from tests.test_servicio import CLAVE, pedir

SUCESOS = [
    {"fecha": "2026-11-20T10:00:00", "evento": "extension_proteger", "datos_tapados": {"DNI": 1, "IBAN": 1},
     "riesgo_documento": None},
    {"fecha": "2026-11-20T10:01:00", "evento": "extension_restaurar", "verificacion": "PELIGRO",
     "avisos_respuesta": {"descarga_y_ejecuta": 1, "imita_marca": 1}},
    {"fecha": "2026-11-22T09:00:00", "evento": "extension_proteger", "datos_tapados": {}, "riesgo_documento": "ALTO"},
    {"fecha": "2026-11-22T09:05:00", "evento": "documento_bloqueado", "puntuacion": 9, "reglas": ["ignora_instrucciones"]},
    {"fecha": "2026-11-23T12:00:00", "evento": "pregunta", "modelo": "qwen3.5:9b", "datos_tapados": {"DNI": 2},
     "riesgo_documento": None, "verificacion": "AVISO", "avisos_respuesta": {"eco_de_la_trampa": 1, "sin_respaldo": 3}},
    {"fecha": "2026-11-23T12:30:00", "evento": "proxy", "datos_tapados": {"EMAIL": 1}, "resultados_bloqueados": 1,
     "acciones_bloqueadas": ["enviar_correo", "enviar_correo"], "verificacion": "OK"},
    {"fecha": "2026-10-01T08:00:00", "evento": "extension_proteger", "datos_tapados": {"TARJETA": 5}},
]
HOY = date(2026, 11, 23)


def escribir(carpeta, sucesos, extra=""):
    por_dia = {}
    for s in sucesos:
        por_dia.setdefault(s["fecha"][:10], []).append(json.dumps(s, ensure_ascii=False))
    for dia, lineas in por_dia.items():
        (carpeta / f"guardian_{dia}.jsonl").write_text("\n".join(lineas) + "\n" + extra, encoding="utf-8")


def test_resume_lo_que_ha_hecho(tmp_path):
    escribir(tmp_path, SUCESOS)
    a = leer_registro(str(tmp_path), dias=30, hoy=HOY)
    assert a.sucesos == 6  # el de octubre se queda fuera
    assert dict(a.datos) == {"DNI": 3, "IBAN": 1, "EMAIL": 1} and a.mensajes_con_datos == 3
    assert a.documentos_con_trampa == 2 and a.documentos_bloqueados == 1
    assert dict(a.respuestas) == {"PELIGRO": 1, "AVISO": 1, "OK": 1}
    assert dict(a.avisos) == {"descarga_y_ejecuta": 1, "imita_marca": 1, "eco_de_la_trampa": 1}  # sin los INFO
    assert dict(a.acciones_bloqueadas) == {"enviar_correo": 2} and a.resultados_bloqueados == 1
    assert dict(a.donde) == {"Extensión": 3, "Chat": 2, "Agentes": 1}
    assert (a.desde, a.hasta) == (date(2026, 11, 20), HOY)
    assert a.ultimos[0]["donde"] == "Agentes" and "enviar_correo" in a.ultimos[0]["que"] and a.ultimos[0]["grave"]
    assert "bloqueado" in a.ultimos[2]["que"]  # el documento bloqueado
    assert a.por_dia["2026-11-20"] == {"datos": 2, "alertas": 1}


def test_filtra_por_dias(tmp_path):
    escribir(tmp_path, SUCESOS)
    assert leer_registro(str(tmp_path), dias=1, hoy=HOY).sucesos == 2
    assert leer_registro(str(tmp_path), dias=0, hoy=HOY).datos["TARJETA"] == 5  # 0 = todo


def test_un_registro_roto_o_editado_no_lo_rompe(tmp_path):
    raros = [{"fecha": "2026-11-23T10:00:00", "evento": "pregunta", "datos_tapados": {"DNI": "muchos", "IBAN": -3,
                                                                                       "EMAIL": True, "NIE": 1}},
             {"fecha": "2026-11-23T10:01:00", "evento": "de_otra_version", "datos_tapados": {"DNI": 9}},
             {"fecha": "2026-11-23T10:02:00", "evento": "proxy", "acciones_bloqueadas": "no es una lista"}]
    escribir(tmp_path, raros, extra="esto no es JSON\n[1, 2]\n{\"sin\": \"fecha\"}\n")
    a = leer_registro(str(tmp_path), dias=0, hoy=HOY)
    assert a.sucesos == 2 and dict(a.datos) == {"NIE": 1} and a.lineas_rotas == 3


def test_carpeta_vacia(tmp_path):
    a = leer_registro(str(tmp_path / "no_existe"), hoy=HOY)
    assert a.sucesos == 0 and a.a_dict()["datos_tapados"] == 0


def test_el_registro_nunca_guarda_el_dato(tmp_path):
    guardian = Guardian(ia=IAFalsa(["Hecho."]), registro=Registro(str(tmp_path)))
    guardian.preguntar("Mi DNI es 12345678Z y mi correo lucia.moreno@gmail.com")
    texto = "".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.jsonl"))
    assert "12345678Z" not in texto and "lucia.moreno" not in texto
    a = leer_registro(str(tmp_path))
    assert dict(a.datos) == {"DNI": 1, "EMAIL": 1}
    assert "12345678Z" not in json.dumps(a.a_dict(), ensure_ascii=False)


def test_informe_en_la_terminal(tmp_path, capsys):
    escribir(tmp_path, SUCESOS)
    assert main(["informe", "--carpeta", str(tmp_path), "--dias", "0"]) == 0
    salida = capsys.readouterr().out
    assert "Datos tapados antes de llegar a la IA: 10" in salida  # con los de octubre
    assert "comando que descarga un programa y lo ejecuta" in salida and "enviar_correo ×2" in salida
    assert main(["informe", "--carpeta", str(tmp_path), "--dias", "0", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["documentos_con_trampa"] == 2
    assert main(["informe", "--carpeta", str(tmp_path / "vacia")]) == 0
    assert "Todavía no hay nada" in capsys.readouterr().out


def test_el_servicio_da_la_actividad_a_la_extension(tmp_path):
    servicio = ServicioGuardian(registro=Registro(str(tmp_path)))
    srv = ServidorServicio(servicio, puerto=0, clave=CLAVE, silencioso=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        pedir(srv, "POST", "/v1/guardian/proteger", {"texto": "Mi DNI es 12345678Z"})
        codigo, r = pedir(srv, "GET", "/v1/guardian/actividad")
        assert codigo == 200 and r["datos_tapados"] == 1 and r["datos"] == {"DNI": 1}
        assert "12345678Z" not in json.dumps(r)
        assert pedir(srv, "GET", "/v1/guardian/actividad", clave=None)[0] == 401
    finally:
        srv.shutdown()
        srv.server_close()
