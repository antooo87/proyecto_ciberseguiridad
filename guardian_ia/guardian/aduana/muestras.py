"""Fabrica documentos Word y PDF de prueba sin instalar nada (para los tests y los ejemplos).

Un .docx es un zip con XML dentro, y un PDF es texto con una estructura fija,
así que se pueden escribir a mano. Sirve para crear documentos con texto
escondido (blanco, diminuto, oculto, fuera de la página) y comprobar que la
aduana lo encuentra.
"""

import io
import zipfile
from xml.sax.saxutils import escape, quoteattr

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
TIPO_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"


def run(texto: str, oculto=False, color=None, medios_puntos=None, estilo=None, fondo=None, tema=None,
        negrita=False) -> str:
    """Un trozo de texto de Word con su formato. medios_puntos=2 es letra de 1 pt."""
    props = []
    if estilo:
        props.append(f"<w:rStyle w:val={quoteattr(estilo)}/>")
    if negrita:
        props.append("<w:b/>")
    if oculto:
        props.append("<w:vanish/>")
    if color or tema:
        props.append(f"<w:color w:val=\"{color or 'FFFFFF'}\"" + (f" w:themeColor=\"{tema}\"" if tema else "") + "/>")
    if medios_puntos:
        props.append(f"<w:sz w:val=\"{medios_puntos}\"/><w:szCs w:val=\"{medios_puntos}\"/>")
    if fondo:
        props.append(f"<w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{fondo}\"/>")
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escape(texto)}</w:t></w:r>"


def parrafo(*runs: str, estilo=None) -> str:
    ppr = f"<w:pPr><w:pStyle w:val={quoteattr(estilo)}/></w:pPr>" if estilo else ""
    return f"<w:p>{ppr}{''.join(r if r.startswith('<') else run(r) for r in runs)}</w:p>"


def tabla(filas: list[list[str]], fondo_cabecera: str | None = None, color_cabecera: str | None = None) -> str:
    columnas = len(filas[0])
    xml = ["<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/></w:tblPr><w:tblGrid>",
           "<w:gridCol w:w=\"3000\"/>" * columnas, "</w:tblGrid>"]
    for i, fila in enumerate(filas):
        xml.append("<w:tr>")
        for celda in fila:
            sombra = f"<w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{fondo_cabecera}\"/>" if i == 0 and fondo_cabecera else ""
            contenido = run(celda, color=color_cabecera, negrita=True) if i == 0 and color_cabecera else run(celda)
            xml.append(f"<w:tc><w:tcPr><w:tcW w:w=\"3000\" w:type=\"dxa\"/>{sombra}</w:tcPr><w:p>{contenido}</w:p></w:tc>")
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


def crear_docx(cuerpo: list[str], estilos_extra: str = "", propiedades: dict | None = None,
               relaciones: list[tuple[str, str]] = (), archivos_extra: dict[str, bytes] | None = None) -> bytes:
    """cuerpo: párrafos y tablas en XML. relaciones: (tipo, destino) externas, p. ej. ("hyperlink", "https://...")."""
    propiedades = propiedades or {}
    tipos = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
             "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
             "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
             "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
             "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument."
             "wordprocessingml.document.main+xml\"/>"
             "<Override PartName=\"/word/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument."
             "wordprocessingml.styles+xml\"/>"
             "<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package."
             "core-properties+xml\"/></Types>")
    rels = (f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"{NS_REL}\">"
            f"<Relationship Id=\"rId1\" Type=\"{TIPO_REL}officeDocument\" Target=\"word/document.xml\"/>"
            "<Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/"
            "metadata/core-properties\" Target=\"docProps/core.xml\"/></Relationships>")
    rels_doc = [f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"{NS_REL}\">"
                f"<Relationship Id=\"rId1\" Type=\"{TIPO_REL}styles\" Target=\"styles.xml\"/>"]
    for i, (tipo, destino) in enumerate(relaciones, 10):
        rels_doc.append(f"<Relationship Id=\"rId{i}\" Type=\"{TIPO_REL}{tipo}\" Target={quoteattr(destino)} "
                        "TargetMode=\"External\"/>")
    rels_doc.append("</Relationships>")
    documento = (f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><w:document xmlns:w=\"{NS_W}\" "
                 "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\"><w:body>"
                 + "".join(cuerpo) +
                 "<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1417\" w:right=\"1701\" "
                 "w:bottom=\"1417\" w:left=\"1701\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/></w:sectPr>"
                 "</w:body></w:document>")
    estilos = (f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><w:styles xmlns:w=\"{NS_W}\">"
               "<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii=\"Calibri\" w:hAnsi=\"Calibri\"/>"
               "<w:sz w:val=\"22\"/></w:rPr></w:rPrDefault></w:docDefaults>"
               "<w:style w:type=\"paragraph\" w:default=\"1\" w:styleId=\"Normal\"><w:name w:val=\"Normal\"/></w:style>"
               "<w:style w:type=\"paragraph\" w:styleId=\"Titulo1\"><w:name w:val=\"heading 1\"/>"
               "<w:basedOn w:val=\"Normal\"/><w:rPr><w:b/><w:color w:val=\"1F3864\"/><w:sz w:val=\"32\"/></w:rPr>"
               f"</w:style>{estilos_extra}</w:styles>")
    meta = "".join(f"<{etiqueta}>{escape(propiedades[clave])}</{etiqueta}>" for clave, etiqueta in (
        ("titulo", "dc:title"), ("asunto", "dc:subject"), ("autor", "dc:creator"), ("palabras", "cp:keywords"),
        ("descripcion", "dc:description")) if propiedades.get(clave))
    core = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><cp:coreProperties "
            "xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" "
            "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:dcterms=\"http://purl.org/dc/terms/\">"
            f"{meta}</cp:coreProperties>")
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in (("[Content_Types].xml", tipos), ("_rels/.rels", rels),
                                  ("word/_rels/document.xml.rels", "".join(rels_doc)),
                                  ("word/document.xml", documento), ("word/styles.xml", estilos),
                                  ("docProps/core.xml", core)):
            z.writestr(nombre, contenido)
        for nombre, contenido in (archivos_extra or {}).items():
            z.writestr(nombre, contenido)
    return salida.getvalue()


def _cadena_pdf(texto: str) -> bytes:
    datos = texto.encode("cp1252", errors="replace")
    return b"(" + datos.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


def crear_pdf(paginas: list[list[dict]], ancho: int = 595, alto: int = 842, javascript: str | None = None,
              propiedades: dict | None = None) -> bytes:
    """Cada página es una lista de elementos:
        {"texto": "Hola", "x": 72, "y": 760, "tam": 11, "color": (0, 0, 0), "modo": 0}
        {"rect": (x, y, ancho, alto), "color": (0.1, 0.1, 0.3)}     rectángulo relleno
    "modo": 3 es texto invisible (como la capa de texto de un PDF escaneado).
    """
    objetos: list[bytes] = []

    def nuevo(contenido: bytes) -> int:
        objetos.append(contenido)
        return len(objetos)

    catalogo = nuevo(b"")  # se rellena al final
    raiz_paginas = nuevo(b"")
    fuente = nuevo(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    hijas = []
    for elementos in paginas:
        flujo = []
        for e in elementos:
            r, g, b = e.get("color", (0, 0, 0))
            if "rect" in e:
                x, y, w, h = e["rect"]
                flujo.append(f"q {r} {g} {b} rg {x} {y} {w} {h} re f Q".encode())
            else:
                flujo.append(f"BT /F1 {e.get('tam', 11)} Tf {e.get('modo', 0)} Tr {r} {g} {b} rg "
                             f"1 0 0 1 {e['x']} {e['y']} Tm ".encode() + _cadena_pdf(e["texto"]) + b" Tj ET")
        datos = b"\n".join(flujo)
        contenido = nuevo(b"<< /Length %d >>\nstream\n" % len(datos) + datos + b"\nendstream")
        hijas.append(nuevo(f"<< /Type /Page /Parent {raiz_paginas} 0 R /MediaBox [0 0 {ancho} {alto}] "
                           f"/Resources << /Font << /F1 {fuente} 0 R >> >> /Contents {contenido} 0 R >>".encode()))
    objetos[raiz_paginas - 1] = (f"<< /Type /Pages /Kids [{' '.join(f'{h} 0 R' for h in hijas)}] "
                                 f"/Count {len(hijas)} >>").encode()
    extra = b""
    if javascript:
        accion = nuevo(b"<< /S /JavaScript /JS " + _cadena_pdf(javascript) + b" >>")
        extra = f" /OpenAction {accion} 0 R".encode()
    objetos[catalogo - 1] = f"<< /Type /Catalog /Pages {raiz_paginas} 0 R".encode() + extra + b" >>"
    info = None
    if propiedades:
        info = nuevo(b"<< " + b" ".join(f"/{clave} ".encode() + _cadena_pdf(valor)
                                         for clave, valor in propiedades.items()) + b" >>")

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = []
    for numero, contenido in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += f"{numero} 0 obj\n".encode() + contenido + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    salida += b"".join(f"{p:010d} 00000 n \n".encode() for p in posiciones)
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root {catalogo} 0 R".encode()
    salida += f" /Info {info} 0 R".encode() if info else b""
    salida += f" >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
    return bytes(salida)
