"""La batería de casos reales y difíciles (ejemplos/casos_reales): una empresa inventada con su carpeta de RRHH, un
contrato largo, una bandeja de correos, respuestas de IA y preguntas mal hechas.

El generador apunta cada dato que mete en cada archivo, así que aquí se comprueba que el Guardián encuentra
EXACTAMENTE esos datos (ni uno más ni uno menos) y el veredicto que toca. No es una medida a ciegas: los casos se
escribieron a la vez que las reglas. Sirve para que ninguna mejora futura rompa lo que ya funciona.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from guardian.escaner import anonimizar, escanear
from guardian.estafas import revisar_bandeja
from guardian.mejorador import Mejorador, analizar
from guardian.verificador import Verificador

CASOS = Path(__file__).resolve().parent.parent / "ejemplos" / "casos_reales"
_spec = importlib.util.spec_from_file_location("generar_casos", CASOS / "generar.py")
generar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generar)


@pytest.fixture(scope="module")
def casos(tmp_path_factory):
    destino = tmp_path_factory.mktemp("casos_reales")
    return destino, generar.crear_todo(destino)


def test_los_archivos_del_repositorio_son_los_que_crea_el_generador(casos):
    destino, _ = casos
    creados = sorted(p.relative_to(destino) for p in destino.rglob("*") if p.is_file())
    guardados = sorted(p.relative_to(CASOS) for p in CASOS.rglob("*") if p.is_file()
                       and p.name not in ("generar.py", "LEEME.md", ".gitattributes") and "__pycache__" not in p.parts)
    assert creados == guardados
    distintos = [str(r) for r in creados if (destino / r).read_bytes() != (CASOS / r).read_bytes()]
    assert distintos == [], f"Vuelve a ejecutar ejemplos/casos_reales/generar.py: han cambiado {distintos}"


def test_carpeta_de_rrhh_veredicto_y_datos_exactos_de_cada_archivo(casos):
    destino, esperado = casos
    informe = escanear(str(destino / "1_carpeta_rrhh"))
    vistos = {a.ruta: a for a in informe.archivos}
    assert set(vistos) == set(esperado["rrhh"])
    for archivo, quiero in esperado["rrhh"].items():
        resultado = vistos[archivo]
        assert resultado.veredicto == quiero["veredicto"], archivo
        assert dict(sorted(resultado.datos.items())) == quiero["datos"], archivo
    assert informe.saltados == 1  # el «DNI escaneado» es una imagen: el Guardián no lee imágenes y lo cuenta
    assert informe.cuenta() == {"TRAMPA": 6, "DATOS PERSONALES": 5, "NO SE PUEDE LEER": 0, "LIMPIO": 3}


def test_las_siete_formas_de_esconder_ordenes_se_detectan(casos):
    destino, _ = casos
    informe = {a.ruta: a for a in escanear(str(destino / "1_carpeta_rrhh")).archivos}
    assert informe["nominas_noviembre_2026.xlsx"].ocultos == 1  # hoja «muy oculta»
    assert informe["cv_candidato_ciberseguridad.docx"].ocultos == 2  # texto oculto de Word + letra blanca de 1 pt
    assert informe["encuesta_clima_laboral_2026.xlsx"].ocultos == 1  # celda con formato ;;;
    assert informe["formacion_phishing_2026.pptx"].riesgo == "ALTO"  # diapositiva oculta con la orden
    assert informe["portal_empleado_intranet.html"].riesgo == "ALTO"  # display:none, comentario e imagen espía
    assert informe["organigrama_2027.docx"].riesgo == "MEDIO"  # plantilla remota (trampa del formato)
    # y lo que se VE con letra blanca sobre fondo oscuro no es trampa
    assert informe["bienvenida_nuevos_empleados.pptx"].veredicto == "LIMPIO"
    assert informe["politica_teletrabajo_2026.pdf"].veredicto == "LIMPIO"


def test_contrato_largo_anonimizado_sin_dejar_ni_un_dato(casos):
    destino, esperado = casos
    contrato = esperado["contrato"]
    texto, resultado, quitados = anonimizar(str(destino / "2_contrato_largo" / contrato["archivo"]))
    quedan = [valor for valor in contrato["valores"] if valor in texto]
    assert quedan == []
    assert dict(sorted(resultado.resumen().items())) == contrato["datos"]
    marcadores = {m for m in __import__("re").findall(r"\[([A-Z_]+)_\d+\]", texto)}
    assert marcadores == set(contrato["distintos"])
    assert "[CIF_1]" in texto and "[IBAN_2]" in texto and "[MATRICULA_5]" in texto
    assert quitados == 0


def test_bandeja_de_entrada_todas_las_estafas_y_ningun_correo_normal(casos):
    destino, esperado = casos
    revisados = {r.archivo: r for r in revisar_bandeja(str(destino / "3_bandeja_de_entrada"))}
    assert set(revisados) == set(esperado["bandeja"])
    for archivo, quiero in esperado["bandeja"].items():
        nivel = revisados[archivo].informe.nivel
        assert (nivel == "ALTO") if quiero["estafa"] else (nivel == "BAJO"), (archivo, nivel)


@pytest.mark.parametrize("archivo, pista, tipo", [
    ("01_correos_paquete_retenido.eml", "enlace_enganoso", "paquetería"),
    ("02_santander_cuenta_bloqueada.eml", "remitente_falso", "banco"),
    ("04_director_general_transferencia.eml", "responder_a_otro", "CEO"),
    ("08_factura_pendiente_adjunta.eml", "adjunto_ejecutable", "archivo peligroso"),
    ("13_boletin_con_aviso_escondido.eml", "texto_oculto", "engañar a la IA"),
])
def test_pistas_que_solo_se_ven_en_el_correo_entero(casos, archivo, pista, tipo):
    destino, _ = casos
    revisado = next(r for r in revisar_bandeja(str(destino / "3_bandeja_de_entrada")) if r.archivo == archivo)
    assert pista in {s.tipo for s in revisado.informe.senales}
    assert tipo in revisado.informe.tipo


def test_respuestas_de_ia_cada_una_con_su_nivel(casos):
    destino, esperado = casos
    for archivo, nivel in esperado["respuestas"].items():
        texto = (destino / "4_respuestas_de_ia" / archivo).read_text("utf-8")
        assert Verificador().revisar(texto).nivel == nivel, archivo


def test_preguntas_vagas_tipo_nota_baja_y_datos_tapados(casos):
    _, esperado = casos
    mejorador = Mejorador()
    for caso in esperado["preguntas"]:
        mejora = mejorador.mejorar(caso["pregunta"])
        assert analizar(mejora.protegido).tipo == caso["tipo"], caso["pregunta"]
        assert mejora.nota <= 80, caso["pregunta"]  # todas están mal hechas a propósito
        assert len(mejora.versiones) == 2
    ultima = mejorador.mejorar(esperado["preguntas"][-1]["pregunta"])
    assert ultima.datos_tapados == {"DNI": 1, "IBAN": 1}
    assert ultima.versiones[0].texto.startswith("Tengo que mandar a la gestoría")
    assert "¿Cómo lo hago?" in ultima.versiones[0].texto


def test_esperado_json_coincide_con_lo_que_devuelve_el_generador(casos):
    _, esperado = casos
    assert json.loads((CASOS / "esperado.json").read_text("utf-8")) == esperado
