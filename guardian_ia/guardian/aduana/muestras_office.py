"""Fabrica presentaciones (.pptx) y hojas de cálculo (.xlsx) de prueba sin instalar nada.

Igual que muestras.py con Word y PDF: un archivo de Office es un zip con XML dentro. Los archivos que salen
se abren en PowerPoint, Excel y LibreOffice, y sirven para esconder texto (blanco, diminuto, fuera de la
diapositiva, en hojas ocultas...) y comprobar que la aduana lo encuentra.
"""

import io
import zipfile
from xml.sax.saxutils import escape, quoteattr

from .muestras import NS_REL, TIPO_REL, core_xml

XML = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
CT = "application/vnd.openxmlformats-officedocument."
EMU_CM = 360000  # PowerPoint mide en EMU: 1 cm = 360 000
ANCHO, ALTO = 12192000, 6858000  # diapositiva panorámica 16:9 (33,867 x 19,05 cm)
MAPA_COLORES = ("bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" accent1=\"accent1\" accent2=\"accent2\" "
                "accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" hlink=\"hlink\" "
                "folHlink=\"folHlink\"")
ARBOL_VACIO = ("<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>")


def _rels(*relaciones: tuple[str, str, str]) -> str:
    filas = "".join(f"<Relationship Id=\"{i}\" Type=\"{t if t.startswith('http') else TIPO_REL + t}\" "
                    f"Target={quoteattr(d)}/>" for i, t, d in relaciones)
    return f"{XML}<Relationships xmlns=\"{NS_REL}\">{filas}</Relationships>"


def _tipos(*partes: tuple[str, str]) -> str:
    filas = "".join(f"<Override PartName=\"{nombre}\" ContentType=\"{tipo}\"/>" for nombre, tipo in partes)
    return (f"{XML}<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
            "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
            "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
            "<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package."
            f"core-properties+xml\"/>{filas}</Types>")


def _zip(partes: dict[str, str]) -> bytes:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in partes.items():
            z.writestr(nombre, contenido)
    return salida.getvalue()


# ---------------------------------------------------------------- PowerPoint
TEMA = (f"{XML}<a:theme xmlns:a=\"{NS_A}\" name=\"Guardian\"><a:themeElements>"
        "<a:clrScheme name=\"Guardian\"><a:dk1><a:sysClr val=\"windowText\" lastClr=\"000000\"/></a:dk1>"
        "<a:lt1><a:sysClr val=\"window\" lastClr=\"FFFFFF\"/></a:lt1><a:dk2><a:srgbClr val=\"1F2937\"/></a:dk2>"
        "<a:lt2><a:srgbClr val=\"F3F4F6\"/></a:lt2>"
        + "".join(f"<a:accent{i}><a:srgbClr val=\"{c}\"/></a:accent{i}>" for i, c in enumerate(
            ("1F6FEB", "F59E0B", "16A34A", "DC2626", "7C3AED", "0891B2"), 1))
        + "<a:hlink><a:srgbClr val=\"0563C1\"/></a:hlink><a:folHlink><a:srgbClr val=\"954F72\"/></a:folHlink>"
        "</a:clrScheme><a:fontScheme name=\"Guardian\">"
        "<a:majorFont><a:latin typeface=\"Calibri\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/></a:majorFont>"
        "<a:minorFont><a:latin typeface=\"Calibri\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/></a:minorFont>"
        "</a:fontScheme><a:fmtScheme name=\"Guardian\">"
        "<a:fillStyleLst>" + "<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>" * 3 + "</a:fillStyleLst>"
        "<a:lnStyleLst>" + "".join(f"<a:ln w=\"{w}\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:ln>"
                                   for w in (6350, 12700, 19050)) + "</a:lnStyleLst>"
        "<a:effectStyleLst>" + "<a:effectStyle><a:effectLst/></a:effectStyle>" * 3 + "</a:effectStyleLst>"
        "<a:bgFillStyleLst>" + "<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>" * 3 + "</a:bgFillStyleLst>"
        "</a:fmtScheme></a:themeElements></a:theme>")


def texto_pptx(texto: str, color: str | None = None, puntos: float | None = None, negrita: bool = False) -> str:
    """Un trozo de texto de PowerPoint. color="FFFFFF" es blanco; puntos=1 es letra de 1 pt."""
    atributos = " lang=\"es-ES\"" + (f" sz=\"{int(puntos * 100)}\"" if puntos else "") + (" b=\"1\"" if negrita else "")
    relleno = f"<a:solidFill><a:srgbClr val=\"{color}\"/></a:solidFill>" if color else ""
    return f"<a:r><a:rPr{atributos} dirty=\"0\">{relleno}</a:rPr><a:t>{escape(texto)}</a:t></a:r>"


def forma_pptx(*parrafos: str | list[str], x_cm: float = 2, y_cm: float = 2, ancho_cm: float = 29, alto_cm: float = 2,
               oculta: bool = False, relleno: str | None = None, texto_alternativo: str | None = None) -> str:
    """Un cuadro de texto. Cada párrafo es un texto suelto o una lista de texto_pptx(...)."""
    cuerpo = "".join("<a:p>" + ("".join(p) if isinstance(p, list) else texto_pptx(p)) + "</a:p>" for p in parrafos)
    extra = (" hidden=\"1\"" if oculta else "") + (f" descr={quoteattr(texto_alternativo)}" if texto_alternativo else "")
    fondo = f"<a:solidFill><a:srgbClr val=\"{relleno}\"/></a:solidFill>" if relleno else "<a:noFill/>"
    return (f"<p:sp><p:nvSpPr><p:cNvPr id=\"{{id}}\" name=\"Cuadro {{id}}\"{extra}/><p:cNvSpPr txBox=\"1\"/><p:nvPr/>"
            f"</p:nvSpPr><p:spPr><a:xfrm><a:off x=\"{int(x_cm * EMU_CM)}\" y=\"{int(y_cm * EMU_CM)}\"/>"
            f"<a:ext cx=\"{int(ancho_cm * EMU_CM)}\" cy=\"{int(alto_cm * EMU_CM)}\"/></a:xfrm>"
            f"<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>{fondo}</p:spPr>"
            f"<p:txBody><a:bodyPr wrap=\"square\"/><a:lstStyle/>{cuerpo}</p:txBody></p:sp>")


def crear_pptx(diapositivas: list[dict], propiedades: dict | None = None, archivos_extra: dict[str, str] | None = None
               ) -> bytes:
    """diapositivas: [{"formas": [forma_pptx(...)], "oculta": False, "notas": "...", "fondo": "1F2937"}]."""
    con_notas = any(d.get("notas") for d in diapositivas)
    partes: dict[str, str] = {}
    tipos = [("/ppt/presentation.xml", CT + "presentationml.presentation.main+xml"),
             ("/ppt/slideMasters/slideMaster1.xml", CT + "presentationml.slideMaster+xml"),
             ("/ppt/slideLayouts/slideLayout1.xml", CT + "presentationml.slideLayout+xml"),
             ("/ppt/theme/theme1.xml", CT + "theme+xml")]
    rels_presentacion = [("rId1", "slideMaster", "slideMasters/slideMaster1.xml"), ("rId3", "theme", "theme/theme1.xml")]
    if con_notas:
        tipos += [("/ppt/notesMasters/notesMaster1.xml", CT + "presentationml.notesMaster+xml"),
                  ("/ppt/theme/theme2.xml", CT + "theme+xml")]
        rels_presentacion.append(("rId2", "notesMaster", "notesMasters/notesMaster1.xml"))
        partes["ppt/notesMasters/notesMaster1.xml"] = (
            f"{XML}<p:notesMaster xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\"><p:cSld><p:bg><p:bgRef "
            f"idx=\"1001\"><a:schemeClr val=\"bg1\"/></p:bgRef></p:bg><p:spTree>{ARBOL_VACIO}</p:spTree></p:cSld>"
            f"<p:clrMap {MAPA_COLORES}/></p:notesMaster>")
        partes["ppt/notesMasters/_rels/notesMaster1.xml.rels"] = _rels(("rId1", "theme", "../theme/theme2.xml"))
        partes["ppt/theme/theme2.xml"] = TEMA
    ids = []
    for n, diapositiva in enumerate(diapositivas, 1):
        formas = "".join(f.replace("{id}", str(i)) for i, f in enumerate(diapositiva.get("formas", []), 2))
        fondo = (f"<p:bg><p:bgPr><a:solidFill><a:srgbClr val=\"{diapositiva['fondo']}\"/></a:solidFill><a:effectLst/>"
                 "</p:bgPr></p:bg>") if diapositiva.get("fondo") else ""
        mostrar = " show=\"0\"" if diapositiva.get("oculta") else ""
        partes[f"ppt/slides/slide{n}.xml"] = (
            f"{XML}<p:sld xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\"{mostrar}><p:cSld>{fondo}<p:spTree>"
            f"{ARBOL_VACIO}{formas}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>")
        rels = [("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml")]
        if diapositiva.get("notas"):
            rels.append(("rId2", "notesSlide", f"../notesSlides/notesSlide{n}.xml"))
            partes[f"ppt/notesSlides/notesSlide{n}.xml"] = (
                f"{XML}<p:notes xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\"><p:cSld><p:spTree>{ARBOL_VACIO}"
                "<p:sp><p:nvSpPr><p:cNvPr id=\"2\" name=\"Notas\"/><p:cNvSpPr><a:spLocks noGrp=\"1\"/></p:cNvSpPr>"
                "<p:nvPr><p:ph type=\"body\" idx=\"1\"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>"
                f"<a:p>{texto_pptx(diapositiva['notas'])}</a:p></p:txBody></p:sp></p:spTree></p:cSld>"
                "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>")
            partes[f"ppt/notesSlides/_rels/notesSlide{n}.xml.rels"] = _rels(
                ("rId1", "notesMaster", "../notesMasters/notesMaster1.xml"), ("rId2", "slide", f"../slides/slide{n}.xml"))
            tipos.append((f"/ppt/notesSlides/notesSlide{n}.xml", CT + "presentationml.notesSlide+xml"))
        partes[f"ppt/slides/_rels/slide{n}.xml.rels"] = _rels(*rels)
        tipos.append((f"/ppt/slides/slide{n}.xml", CT + "presentationml.slide+xml"))
        rels_presentacion.append((f"rId{9 + n}", "slide", f"slides/slide{n}.xml"))
        ids.append(f"<p:sldId id=\"{255 + n}\" r:id=\"rId{9 + n}\"/>")
    notas = "<p:notesMasterIdLst><p:notesMasterId r:id=\"rId2\"/></p:notesMasterIdLst>" if con_notas else ""
    partes.update({
        "[Content_Types].xml": _tipos(*tipos),
        "_rels/.rels": _rels(("rId1", "officeDocument", "ppt/presentation.xml"),
                             ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/"
                                      "core-properties", "docProps/core.xml")),
        "docProps/core.xml": core_xml(propiedades),
        "ppt/presentation.xml": (
            f"{XML}<p:presentation xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\">"
            f"<p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/></p:sldMasterIdLst>{notas}"
            f"<p:sldIdLst>{''.join(ids)}</p:sldIdLst><p:sldSz cx=\"{ANCHO}\" cy=\"{ALTO}\"/>"
            "<p:notesSz cx=\"6858000\" cy=\"9144000\"/></p:presentation>"),
        "ppt/_rels/presentation.xml.rels": _rels(*rels_presentacion),
        "ppt/slideMasters/slideMaster1.xml": (
            f"{XML}<p:sldMaster xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\"><p:cSld><p:bg><p:bgRef "
            f"idx=\"1001\"><a:schemeClr val=\"bg1\"/></p:bgRef></p:bg><p:spTree>{ARBOL_VACIO}</p:spTree></p:cSld>"
            f"<p:clrMap {MAPA_COLORES}/><p:sldLayoutIdLst><p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/>"
            "</p:sldLayoutIdLst></p:sldMaster>"),
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": _rels(("rId1", "slideLayout", "../slideLayouts/slideLayout1.xml"),
                                                              ("rId2", "theme", "../theme/theme1.xml")),
        "ppt/slideLayouts/slideLayout1.xml": (
            f"{XML}<p:sldLayout xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\" type=\"blank\" preserve=\"1\">"
            f"<p:cSld name=\"En blanco\"><p:spTree>{ARBOL_VACIO}</p:spTree></p:cSld>"
            "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"),
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": _rels(("rId1", "slideMaster", "../slideMasters/slideMaster1.xml")),
        "ppt/theme/theme1.xml": TEMA,
    })
    partes.update(archivos_extra or {})
    return _zip(partes)


# ---------------------------------------------------------------- Excel
# Estilos de celda que usan los ejemplos (índice de <cellXfs>)
ESTILO_NORMAL, ESTILO_NEGRITA, ESTILO_BLANCO, ESTILO_DIMINUTO, ESTILO_INVISIBLE, ESTILO_CABECERA = range(6)
ESTILOS_XLSX = (
    f"{XML}<styleSheet xmlns=\"{NS_S}\"><numFmts count=\"1\"><numFmt numFmtId=\"164\" formatCode=\";;;\"/></numFmts>"
    "<fonts count=\"5\"><font><sz val=\"11\"/><name val=\"Calibri\"/></font>"
    "<font><b/><sz val=\"11\"/><name val=\"Calibri\"/></font>"
    "<font><sz val=\"11\"/><color rgb=\"FFFFFFFF\"/><name val=\"Calibri\"/></font>"
    "<font><sz val=\"1\"/><name val=\"Calibri\"/></font>"
    "<font><b/><sz val=\"11\"/><color rgb=\"FFFFFFFF\"/><name val=\"Calibri\"/></font></fonts>"
    "<fills count=\"3\"><fill><patternFill patternType=\"none\"/></fill><fill><patternFill patternType=\"gray125\"/>"
    "</fill><fill><patternFill patternType=\"solid\"><fgColor rgb=\"FF1F3864\"/><bgColor indexed=\"64\"/></patternFill>"
    "</fill></fills><borders count=\"1\"><border><left/><right/><top/><bottom/><diagonal/></border></borders>"
    "<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>"
    "<cellXfs count=\"6\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>"
    "<xf numFmtId=\"0\" fontId=\"1\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/>"
    "<xf numFmtId=\"0\" fontId=\"2\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/>"
    "<xf numFmtId=\"0\" fontId=\"3\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/>"
    "<xf numFmtId=\"164\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyNumberFormat=\"1\"/>"
    "<xf numFmtId=\"0\" fontId=\"4\" fillId=\"2\" borderId=\"0\" xfId=\"0\" applyFont=\"1\" applyFill=\"1\"/></cellXfs>"
    "<cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles></styleSheet>")


def _letra_columna(numero: int) -> str:
    letras = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def celda(valor, estilo: int = ESTILO_NORMAL, formula: str | None = None) -> dict:
    """Una celda con estilo (ESTILO_BLANCO, ESTILO_INVISIBLE = formato ;;;...) o con fórmula."""
    return {"valor": valor, "estilo": estilo, "formula": formula}


def crear_xlsx(hojas: list[dict], propiedades: dict | None = None) -> bytes:
    """hojas: [{"nombre": "Ventas", "filas": [[...], ...], "estado": "hidden"|"veryHidden",
    "filas_ocultas": [3], "columnas_ocultas": [2]}]. Cada valor es un texto, un número o celda(...)."""
    partes: dict[str, str] = {}
    tipos = [("/xl/workbook.xml", CT + "spreadsheetml.sheet.main+xml"), ("/xl/styles.xml", CT + "spreadsheetml.styles+xml")]
    rels = [("rId1", "styles", "styles.xml")]
    entradas = []
    for n, hoja in enumerate(hojas, 1):
        filas_xml = []
        for f, fila in enumerate(hoja.get("filas", []), 1):
            celdas = []
            for c, valor in enumerate(fila, 1):
                datos = valor if isinstance(valor, dict) else celda(valor)
                if datos["valor"] is None:
                    continue
                ref = f"{_letra_columna(c)}{f}"
                estilo = f" s=\"{datos['estilo']}\"" if datos["estilo"] else ""
                formula = f"<f>{escape(datos['formula'])}</f>" if datos.get("formula") else ""
                if isinstance(datos["valor"], (int, float)) and not isinstance(datos["valor"], bool):
                    celdas.append(f"<c r=\"{ref}\"{estilo}>{formula}<v>{datos['valor']}</v></c>")
                elif formula:
                    celdas.append(f"<c r=\"{ref}\"{estilo} t=\"str\">{formula}<v>{escape(str(datos['valor']))}</v></c>")
                else:
                    celdas.append(f"<c r=\"{ref}\"{estilo} t=\"inlineStr\"><is><t xml:space=\"preserve\">"
                                  f"{escape(str(datos['valor']))}</t></is></c>")
            oculta = " hidden=\"1\"" if f in hoja.get("filas_ocultas", ()) else ""
            filas_xml.append(f"<row r=\"{f}\"{oculta}>{''.join(celdas)}</row>")
        columnas = "".join(f"<col min=\"{c}\" max=\"{c}\" width=\"12\" hidden=\"1\" customWidth=\"1\"/>"
                           for c in hoja.get("columnas_ocultas", ()))
        partes[f"xl/worksheets/sheet{n}.xml"] = (
            f"{XML}<worksheet xmlns=\"{NS_S}\" xmlns:r=\"{NS_R}\">"
            + (f"<cols>{columnas}</cols>" if columnas else "")
            + f"<sheetData>{''.join(filas_xml)}</sheetData></worksheet>")
        tipos.append((f"/xl/worksheets/sheet{n}.xml", CT + "spreadsheetml.worksheet+xml"))
        rels.append((f"rId{n + 1}", "worksheet", f"worksheets/sheet{n}.xml"))
        estado = f" state=\"{hoja['estado']}\"" if hoja.get("estado") else ""
        entradas.append(f"<sheet name={quoteattr(hoja.get('nombre', f'Hoja{n}'))} sheetId=\"{n}\"{estado} "
                        f"r:id=\"rId{n + 1}\"/>")
    partes.update({
        "[Content_Types].xml": _tipos(*tipos),
        "_rels/.rels": _rels(("rId1", "officeDocument", "xl/workbook.xml"),
                             ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/"
                                      "core-properties", "docProps/core.xml")),
        "docProps/core.xml": core_xml(propiedades),
        "xl/workbook.xml": (f"{XML}<workbook xmlns=\"{NS_S}\" xmlns:r=\"{NS_R}\"><bookViews><workbookView/></bookViews>"
                            f"<sheets>{''.join(entradas)}</sheets></workbook>"),
        "xl/_rels/workbook.xml.rels": _rels(*rels),
        "xl/styles.xml": ESTILOS_XLSX,
    })
    return _zip(partes)
