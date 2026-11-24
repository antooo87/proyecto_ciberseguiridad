from pathlib import Path

from guardian.__main__ import main
from guardian.escaner import DATOS, ILEGIBLE, LIMPIO, TRAMPA, anonimizar, escanear

EJEMPLOS = Path(__file__).parent.parent / "ejemplos"


def test_escanear_ejemplos_da_un_veredicto_por_documento():
    informe = escanear(str(EJEMPLOS))
    veredictos = {a.ruta: a.veredicto for a in informe.archivos}
    assert veredictos["cv_con_trampa.docx"] == TRAMPA
    assert veredictos["articulo_con_trampa.pdf"] == TRAMPA
    assert veredictos["mensaje_con_datos.txt"] == DATOS
    assert veredictos["informe_limpio.docx"] == LIMPIO
    assert informe.archivos[0].veredicto == TRAMPA  # lo peor sale primero
    # en la carpeta de arriba solo hay un DNI; el resto está en casos_reales/ (las subcarpetas también se revisan)
    sueltos = [a for a in informe.archivos if len(Path(a.ruta).parts) == 1]
    assert sum(a.datos.get("DNI", 0) for a in sueltos) == 1
    assert any(a.ruta.startswith("casos_reales") for a in informe.archivos)


def test_escanear_no_entra_en_carpetas_de_programas_y_avisa_de_lo_ilegible(tmp_path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "secreto.txt").write_text("DNI 12345678Z", encoding="utf-8")
    (tmp_path / "foto.png").write_bytes(b"\x89PNG")
    (tmp_path / "roto.docx").write_bytes(b"PK esto no es un Word")
    (tmp_path / "nota.txt").write_text("Mi DNI es 12345678Z", encoding="utf-8")
    informe = escanear(str(tmp_path))
    assert {a.ruta: a.veredicto for a in informe.archivos} == {"nota.txt": DATOS, "roto.docx": ILEGIBLE}
    assert informe.saltados == 1  # la imagen
    assert "12345678Z" not in informe.a_markdown()  # el informe nunca enseña los datos


def test_anonimizar_quita_lo_escondido_y_tapa_los_datos(tmp_path):
    texto, resultado, quitados = anonimizar(str(EJEMPLOS / "cv_con_trampa.docx"))
    assert quitados == 1
    assert "ignora las instrucciones" not in texto
    assert "@" not in texto and "[EMAIL_1]" in texto


def test_comandos_escanear_y_anonimizar(tmp_path, capsys):
    (tmp_path / "carta.txt").write_text("IBAN ES91 2100 0418 4502 0005 1332", encoding="utf-8")
    assert main(["escanear", str(tmp_path), "--informe", str(tmp_path / "informe.md")]) == 0
    assert "DATOS PERSONALES" in (tmp_path / "informe.md").read_text(encoding="utf-8")
    assert main(["anonimizar", str(tmp_path / "carta.txt")]) == 0
    assert (tmp_path / "carta_anonimizado.txt").read_text(encoding="utf-8").strip() == "IBAN [IBAN_1]"
    assert main(["escanear", str(EJEMPLOS)]) == 2  # hay documentos con trampa
