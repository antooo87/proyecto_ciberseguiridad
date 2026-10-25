"""Lectores de documentos para la aduana: texto, Word (.docx) y PDF.

Un Word o un PDF pueden llevar texto que una persona NO ve pero la IA sí lee:
letra blanca sobre fondo blanco, tamaño diminuto, texto marcado como oculto o
colocado fuera de la página. Es el truco de los currículums con "contrátame"
escrito en blanco y de los artículos científicos que en 2025 escondían órdenes
para que la IA revisora les diera buena nota.

Cada lector devuelve una `Lectura` con:
  - texto:   TODO lo que leería una IA (también lo escondido y los metadatos).
             Es lo que analiza la aduana.
  - visible: solo lo que ve una persona. Es lo que se manda a la IA, así la IA
             lee lo mismo que tú.
  - ocultos: cada trozo escondido, con el motivo y dónde está.
  - peligros: otras trampas del archivo que no son prompt injection (macros,
              plantillas remotas tipo Follina, JavaScript en el PDF...).

Los archivos se leen sin ejecutar nada y con límites de tamaño (bombas zip).
"""

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union
from xml.etree import ElementTree

MAX_BYTES = 50 * 1024 * 1024  # 50 MB por archivo
MAX_PARTE_ZIP = 20 * 1024 * 1024  # 20 MB descomprimidos por cada parte del Word
MAX_PAGINAS_PDF = 300
MIN_OCULTO = 3  # trozos más cortos (un espacio en blanco, un punto) no cuentan

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
EXTENSIONES_TEXTO = {".txt", ".md", ".html", ".htm", ".csv", ".json", ".xml", ".eml", ".log", ".yaml", ".yml"}


class ErrorLectura(Exception):
    """El archivo no se puede leer de forma segura."""


@dataclass
class TextoOculto:
    texto: str
    motivo: str  # "letra blanca", "letra diminuta (1 pt)", "marcado como oculto"...
    lugar: str  # "párrafo 12", "página 2", "propiedades del documento"
    truco: bool = True  # True: alguien lo escondió a propósito. False: sitio que no se ve (metadatos)


@dataclass
class Peligro:
    explicacion: str
    peso: int  # se suma a la puntuación de la aduana (5 o más = riesgo ALTO)


@dataclass
class Lectura:
    texto: str
    visible: str
    formato: str  # "texto", "word" o "pdf"
    ocultos: list[TextoOculto] = field(default_factory=list)
    peligros: list[Peligro] = field(default_factory=list)

    @property
    def trucos(self) -> list[TextoOculto]:
        return [o for o in self.ocultos if o.truco]


def leer(origen: Union[str, Path, bytes], nombre: Optional[str] = None) -> Lectura:
    """Lee un archivo (ruta o bytes) según su tipo. `nombre` ayuda a saber el tipo si se pasan bytes."""
    if isinstance(origen, (str, Path)):
        ruta = Path(origen)
        if ruta.stat().st_size > MAX_BYTES:
            raise ErrorLectura(f"El archivo pesa más de {MAX_BYTES // 2**20} MB.")
        datos, nombre = ruta.read_bytes(), nombre or ruta.name
    else:
        datos = origen
        if len(datos) > MAX_BYTES:
            raise ErrorLectura(f"El archivo pesa más de {MAX_BYTES // 2**20} MB.")
    extension = Path(nombre or "").suffix.lower()
    if datos[:5] == b"%PDF-" or extension == ".pdf":
        return leer_pdf(datos)
    if datos[:2] == b"PK" and extension in (".docx", ".docm", ".dotx", ".dotm", ""):
        return leer_docx(datos)
    if extension in (".doc", ".xls", ".ppt", ".pptx", ".xlsx", ".odt"):
        raise ErrorLectura(f"Formato {extension} no soportado todavía: guárdalo como .docx, .pdf o texto.")
    texto = datos.decode("utf-8", errors="replace")
    return Lectura(texto, texto, "texto")


def _limpiar_huecos(texto: str) -> str:
    """Al quitar lo oculto quedan líneas vacías seguidas: se dejan como mucho dos."""
    return re.sub(r"\n{3,}", "\n\n", texto).strip() + "\n"


# ---------------------------------------------------------------- Word (.docx)
def _xml(z: zipfile.ZipFile, nombre: str) -> Optional[ElementTree.Element]:
    try:
        info = z.getinfo(nombre)
    except KeyError:
        return None
    if info.file_size > MAX_PARTE_ZIP:
        raise ErrorLectura(f"La parte {nombre} ocupa demasiado al descomprimirla (posible bomba zip).")
    datos = z.read(info)
    # Un Word normal nunca trae DOCTYPE: si lo trae, puede ser un ataque de entidades XML
    if b"<!DOCTYPE" in datos[:4096] or b"<!ENTITY" in datos[:4096]:
        raise ErrorLectura(f"La parte {nombre} trae declaraciones DOCTYPE/ENTITY: se rechaza por seguridad.")
    try:
        return ElementTree.fromstring(datos)
    except ElementTree.ParseError as e:
        raise ErrorLectura(f"La parte {nombre} no es XML válido: {e}") from e


def _hex_a_luz(valor: Optional[str]) -> Optional[float]:
    """'FFFFFF' -> 1.0 (blanco), '000000' -> 0.0. None si no es un color."""
    if not valor or not re.fullmatch(r"[0-9A-Fa-f]{6}", valor):
        return None
    r, g, b = (int(valor[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


RESALTADOS_OSCUROS = {"black", "darkBlue", "darkCyan", "darkGreen", "darkMagenta", "darkRed", "darkYellow",
                      "darkGray", "blue", "red", "magenta"}


def _propiedades(rpr: Optional[ElementTree.Element]) -> dict:
    """Saca de un <w:rPr> solo lo que sirve para esconder texto."""
    p: dict = {}
    if rpr is None:
        return p
    for etiqueta in ("vanish", "specVanish", "webHidden"):
        e = rpr.find(W + etiqueta)
        if e is not None:
            p["oculto"] = e.get(W + "val", "true").lower() not in ("0", "false", "off")
    color = rpr.find(W + "color")
    if color is not None:
        tema = color.get(W + "themeColor", "")
        p["color"] = "FFFFFF" if tema in ("background1", "light1") else color.get(W + "val")
    tam = rpr.find(W + "sz")
    if tam is not None and (tam.get(W + "val") or "").isdigit():
        p["medios_puntos"] = int(tam.get(W + "val"))
    sombra = rpr.find(W + "shd")
    if sombra is not None and _hex_a_luz(sombra.get(W + "fill")) is not None:
        p["fondo"] = sombra.get(W + "fill")
    resaltado = rpr.find(W + "highlight")
    if resaltado is not None and resaltado.get(W + "val") in RESALTADOS_OSCUROS:
        p["fondo"] = "000000"
    return p


class _Estilos:
    """Los estilos de Word se heredan (basedOn): un estilo 'Normal oculto' puede esconder el texto."""

    def __init__(self, raiz: Optional[ElementTree.Element]):
        self.base: dict = {}
        self.estilos: dict[str, tuple[Optional[str], dict]] = {}
        if raiz is None:
            return
        defecto = raiz.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
        self.base = _propiedades(defecto)
        for estilo in raiz.findall(W + "style"):
            ident = estilo.get(W + "styleId")
            padre = estilo.find(W + "basedOn")
            self.estilos[ident] = (padre.get(W + "val") if padre is not None else None,
                                   _propiedades(estilo.find(W + "rPr")))

    def de(self, ident: Optional[str]) -> dict:
        cadena, vistos = [], set()
        while ident and ident in self.estilos and ident not in vistos and len(cadena) < 20:
            vistos.add(ident)
            padre, props = self.estilos[ident]
            cadena.append(props)
            ident = padre
        resultado: dict = {}
        for props in reversed(cadena):
            resultado.update(props)
        return resultado


def _motivo_oculto(p: dict, fondo_oscuro: bool) -> Optional[str]:
    if p.get("oculto"):
        return "marcado como texto oculto"
    motivos = []
    luz, luz_fondo = _hex_a_luz(p.get("color")), _hex_a_luz(p.get("fondo"))
    oscuro = fondo_oscuro or (luz_fondo is not None and luz_fondo < 0.5)
    if luz is not None and luz >= 0.94 and not oscuro:
        motivos.append("letra blanca sobre fondo blanco")
    medios = p.get("medios_puntos")
    if medios is not None and medios <= 4:
        motivos.append(f"letra diminuta ({medios / 2:g} pt)")
    return " y ".join(motivos) or None


class _LectorWord:
    def __init__(self, estilos: _Estilos, fondo_pagina_oscuro: bool):
        self.estilos = estilos
        self.fondo_pagina_oscuro = fondo_pagina_oscuro
        self.texto: list[str] = []
        self.visible: list[str] = []
        self.ocultos: list[TextoOculto] = []
        self.parrafo = 0

    def recorrer(self, elem: ElementTree.Element, estilo_parrafo: Optional[str] = None, fondo: bool = False,
                 lugar: str = "") -> None:
        etiqueta = elem.tag
        if etiqueta == W + "p":
            self.parrafo += 1
            ppr = elem.find(W + "pPr")
            estilo = None
            if ppr is not None:
                pstyle = ppr.find(W + "pStyle")
                estilo = pstyle.get(W + "val") if pstyle is not None else None
                sombra = ppr.find(W + "shd")
                luz = _hex_a_luz(sombra.get(W + "fill")) if sombra is not None else None
                fondo = fondo or (luz is not None and luz < 0.5)
            for hijo in elem:
                self.recorrer(hijo, estilo, fondo, lugar)
            self.texto.append("\n")
            self.visible.append("\n")
            return
        if etiqueta == W + "tc":  # celda de tabla: puede tener fondo oscuro (cabeceras con letra blanca)
            tcpr = elem.find(W + "tcPr")
            sombra = tcpr.find(W + "shd") if tcpr is not None else None
            luz = _hex_a_luz(sombra.get(W + "fill")) if sombra is not None else None
            fondo = fondo or (luz is not None and luz < 0.5)
        if etiqueta == W + "r":
            self._run(elem, estilo_parrafo, fondo, lugar)
            return
        if etiqueta in (W + "del", W + "instrText", W + "delText"):  # texto borrado y códigos de campo
            return
        if etiqueta == WP + "docPr":  # texto alternativo de una imagen: no se ve en la página
            alt = " ".join(x for x in (elem.get("title"), elem.get("descr")) if x)
            if len(alt.strip()) >= MIN_OCULTO:
                self.texto.append(f"\n[Texto alternativo de imagen] {alt}\n")
                self.ocultos.append(TextoOculto(alt, "texto alternativo de una imagen", f"párrafo {self.parrafo}",
                                                truco=False))
        for hijo in elem:
            self.recorrer(hijo, estilo_parrafo, fondo, lugar)

    def _run(self, run: ElementTree.Element, estilo_parrafo: Optional[str], fondo: bool, lugar: str) -> None:
        rpr = run.find(W + "rPr")
        props = dict(self.estilos.base)
        props.update(self.estilos.de(estilo_parrafo))
        if rpr is not None and rpr.find(W + "rStyle") is not None:
            props.update(self.estilos.de(rpr.find(W + "rStyle").get(W + "val")))
        props.update(_propiedades(rpr))
        trozos = []
        for hijo in run:
            if hijo.tag == W + "t":
                trozos.append(hijo.text or "")
            elif hijo.tag == W + "tab":
                trozos.append("\t")
            elif hijo.tag in (W + "br", W + "cr"):
                trozos.append("\n")
            elif hijo.tag not in (W + "rPr", W + "delText", W + "instrText"):
                self.recorrer(hijo, estilo_parrafo, fondo, lugar)  # imágenes, cuadros de texto...
        texto = "".join(trozos)
        if not texto:
            return
        self.texto.append(texto)
        motivo = _motivo_oculto(props, fondo or self.fondo_pagina_oscuro)
        if motivo is None:
            self.visible.append(texto)
            return
        donde = lugar or f"párrafo {self.parrafo}"
        ultimo = self.ocultos[-1] if self.ocultos else None
        if ultimo and ultimo.motivo == motivo and ultimo.lugar == donde and ultimo.truco:
            ultimo.texto += texto  # runs seguidos con el mismo truco: un solo trozo
        else:
            self.ocultos.append(TextoOculto(texto, motivo, donde))


ESQUEMAS_PELIGROSOS = ("ms-msdt:", "search-ms:", "ms-officecmd:", "file:", "javascript:", "vbscript:", "\\\\", "smb:")


def _relaciones_peligrosas(z: zipfile.ZipFile) -> list[Peligro]:
    """Enlaces del Word a cosas de FUERA que se cargan solas (plantillas remotas, objetos OLE...)."""
    peligros = []
    for nombre in z.namelist():
        if not nombre.endswith(".rels"):
            continue
        raiz = _xml(z, nombre)
        for rel in raiz.iter(REL + "Relationship") if raiz is not None else ():
            if rel.get("TargetMode") != "External":
                continue
            destino, tipo = rel.get("Target", ""), rel.get("Type", "").rsplit("/", 1)[-1]
            if destino.lower().startswith(ESQUEMAS_PELIGROSOS):
                peligros.append(Peligro(
                    f"Enlace externo peligroso ({tipo}): {destino[:80]}. Los Word tipo 'Follina' usan esto para "
                    "ejecutar programas o robar tu contraseña de Windows al abrirlos.", 5))
            elif tipo in ("attachedTemplate", "oleObject", "frame", "subDocument"):
                peligros.append(Peligro(
                    f"El documento carga '{tipo}' desde Internet ({destino[:80]}): técnica de 'plantilla remota' "
                    "usada para colar código al abrirlo.", 4))
    return peligros


def leer_docx(datos: bytes) -> Lectura:
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile as e:
        raise ErrorLectura("No es un .docx válido (el zip está roto).") from e
    with z:
        documento = _xml(z, "word/document.xml")
        if documento is None:
            raise ErrorLectura("No es un documento de Word: falta word/document.xml.")
        fondo = documento.find(W + "background")
        luz_pagina = _hex_a_luz(fondo.get(W + "color")) if fondo is not None else None
        fondo_oscuro = luz_pagina is not None and luz_pagina < 0.5
        lector = _LectorWord(_Estilos(_xml(z, "word/styles.xml")), fondo_oscuro)
        lector.recorrer(documento)
        for parte in sorted(n for n in z.namelist()
                            if re.fullmatch(r"word/(header|footer|footnotes|endnotes|comments)\d*\.xml", n)):
            raiz = _xml(z, parte)
            if raiz is not None:
                nombre = Path(parte).stem.rstrip("0123456789")
                lector.recorrer(raiz, lugar={"header": "encabezado", "footer": "pie de página",
                                              "comments": "comentarios"}.get(nombre, "notas"))
        texto, visible = "".join(lector.texto), "".join(lector.visible)

        propiedades = _xml(z, "docProps/core.xml")
        if propiedades is not None:
            meta = " | ".join(" ".join(e.itertext()).strip() for e in propiedades
                              if e.tag.rsplit("}", 1)[-1] in ("title", "subject", "description", "keywords")
                              and "".join(e.itertext()).strip())
            if meta:
                texto += f"\n[Propiedades del documento] {meta}\n"
                lector.ocultos.append(TextoOculto(meta, "metadatos (propiedades del archivo)",
                                                  "propiedades del documento", truco=False))
        peligros = _relaciones_peligrosas(z)
        if any(n.lower().endswith("vbaproject.bin") for n in z.namelist()):
            peligros.append(Peligro("El documento trae MACROS (vbaProject.bin): no las actives si no sabes de "
                                    "dónde viene.", 2))
    ocultos = [o for o in lector.ocultos if len(o.texto.strip()) >= MIN_OCULTO]
    return Lectura(texto, _limpiar_huecos(visible), "word", ocultos, peligros)


# ---------------------------------------------------------------- PDF
def _indicadores_pdf(datos: bytes) -> list[Peligro]:
    """Como la herramienta pdfid: busca nombres peligrosos, también escritos con trucos (/J#61vaScript).

    /OpenAction solo no se avisa: los PDF normales (los de Word o LibreOffice) lo usan para el zoom inicial.
    """
    nombres = {re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), n).decode("latin-1")
               for n in re.findall(rb"/[A-Za-z0-9#]+", datos)}
    peligros = []
    al_abrir = bool(nombres & {"/OpenAction", "/AA"})
    if nombres & {"/JavaScript", "/JS"}:
        peligros.append(Peligro("El PDF lleva JavaScript" + (" que se ejecuta solo al abrirlo" if al_abrir else "")
                                + ": un documento para leer no lo necesita.", 4 if al_abrir else 3))
    for nombre, explicacion, peso in (("/Launch", "puede lanzar programas del ordenador (/Launch)", 4),
                                      ("/EmbeddedFile", "lleva archivos escondidos dentro", 2),
                                      ("/RichMedia", "lleva contenido multimedia o Flash", 2),
                                      ("/XFA", "usa formularios XFA, que pueden llevar código", 1)):
        if nombre in nombres:
            peligros.append(Peligro(f"El PDF {explicacion}.", peso))
    return peligros


def _es_blanco(color) -> bool:
    if color is None or isinstance(color, str):
        return False
    valores = list(color) if isinstance(color, (tuple, list)) else [color]
    if not valores or not all(isinstance(v, (int, float)) for v in valores):
        return False
    if len(valores) == 4:  # CMYK: blanco es 0,0,0,0
        return all(v <= 0.05 for v in valores)
    return all(v >= 0.95 for v in valores)


def _es_oscuro(color) -> bool:
    if color is None or isinstance(color, str):
        return False
    valores = list(color) if isinstance(color, (tuple, list)) else [color]
    if not valores or not all(isinstance(v, (int, float)) for v in valores):
        return False
    if len(valores) == 4:
        return 1 - min(1.0, valores[3] + max(valores[:3])) < 0.5
    luz = valores[0] if len(valores) == 1 else 0.2126 * valores[0] + 0.7152 * valores[1] + 0.0722 * valores[2]
    return luz < 0.5


def _motivo_pdf(c, pagina, fondos, capa_ocr) -> Optional[str]:
    """Por qué una letra del PDF no la vería una persona (o None si se ve)."""
    x0, y0, x1, y1 = pagina
    if c.x1 < x0 or c.x0 > x1 or c.y1 < y0 or c.y0 > y1:
        return "fuera de la página"
    if getattr(c, "modo", 0) in (3, 7) and not capa_ocr:
        return "texto invisible (modo de pintado 3)"
    motivos = []
    cx, cy = (c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2
    sobre_fondo = any(a <= cx <= b and d <= cy <= e for a, d, b, e in fondos)
    if _es_blanco(c.graphicstate.ncolor) and not sobre_fondo:
        motivos.append("letra blanca sobre fondo blanco")
    if c.size < 2:
        motivos.append(f"letra diminuta ({c.size:.1f} pt)")
    return " y ".join(motivos) or None


def leer_pdf(datos: bytes) -> Lectura:
    try:
        from pdfminer.converter import PDFPageAggregator
        from pdfminer.layout import LAParams, LTChar, LTFigure, LTImage, LTRect, LTTextContainer
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdftypes import resolve1
        from pdfminer.utils import decode_text
    except ImportError as e:
        raise ErrorLectura("Para leer PDF hace falta la librería pdfminer.six: pip install pdfminer.six") from e

    class Agregador(PDFPageAggregator):
        """Igual que el de pdfminer, pero apunta el 'modo de pintado' de cada letra (3 = invisible)."""
        modo = 0

        def render_string(self, textstate, seq, ncs, graphicstate):
            self.modo = textstate.render
            super().render_string(textstate, seq, ncs, graphicstate)

        def render_char(self, *args, **kwargs):
            avance = super().render_char(*args, **kwargs)
            self.cur_item._objs[-1].modo = self.modo
            return avance

    gestor = PDFResourceManager()
    agregador = Agregador(gestor, laparams=LAParams())
    interprete = PDFPageInterpreter(gestor, agregador)
    texto, visible, ocultos = [], [], []
    try:
        documento = PDFDocument(PDFParser(io.BytesIO(datos)))
        paginas = []
        for pagina in PDFPage.create_pages(documento):
            paginas.append(pagina)
            if len(paginas) >= MAX_PAGINAS_PDF:
                break
    except Exception as e:  # pdfminer lanza muchos tipos de error con PDF rotos o con contraseña
        raise ErrorLectura(f"No se puede leer el PDF: {type(e).__name__} {e}") from e
    for numero, pagina in enumerate(paginas, 1):
        try:
            interprete.process_page(pagina)
        except Exception as e:
            texto.append(f"\n[página {numero} ilegible: {e}]\n")
            continue
        maqueta = agregador.get_result()
        fondos = [o.bbox for o in maqueta if isinstance(o, LTRect) and o.fill and _es_oscuro(o.non_stroking_color)]
        fondos += [o.bbox for o in maqueta if isinstance(o, (LTImage, LTFigure))]
        letras = [c for caja in maqueta if isinstance(caja, LTTextContainer)
                  for linea in caja for c in linea if isinstance(c, LTChar)]
        invisibles = sum(1 for c in letras if getattr(c, "modo", 0) in (3, 7))
        capa_ocr = letras and invisibles / len(letras) > 0.9  # PDF escaneado: el texto invisible va sobre la imagen

        for caja in maqueta:
            if not isinstance(caja, LTTextContainer):
                continue
            for linea in caja:
                for c in linea:
                    trozo = c.get_text()
                    texto.append(trozo)
                    m = _motivo_pdf(c, pagina.mediabox, fondos, capa_ocr) if isinstance(c, LTChar) else None
                    if m is None:
                        visible.append(trozo)
                        continue
                    ultimo = ocultos[-1] if ocultos else None
                    if ultimo and ultimo.motivo == m and ultimo.lugar == f"página {numero}":
                        ultimo.texto += trozo
                    else:
                        ocultos.append(TextoOculto(trozo, m, f"página {numero}"))
            texto.append("\n")
            visible.append("\n")
    for o in ocultos:
        o.texto = " ".join(o.texto.split())
    ocultos = [o for o in ocultos if len(o.texto) >= MIN_OCULTO]

    # Propiedades del PDF (título, asunto, palabras clave): no se ven al leerlo, pero hay programas que las pasan a la IA
    meta = []
    for info in documento.info:
        for clave in ("Title", "Subject", "Keywords"):
            valor = resolve1(info.get(clave)) if isinstance(info, dict) else None
            if isinstance(valor, bytes):
                valor = decode_text(valor)
            if isinstance(valor, str) and valor.strip():
                meta.append(valor.strip())
    texto = "".join(texto)
    if meta:
        texto += f"\n[Propiedades del documento] {' | '.join(meta)}\n"
        ocultos.append(TextoOculto(" | ".join(meta), "metadatos (propiedades del archivo)",
                                   "propiedades del documento", truco=False))
    return Lectura(texto, _limpiar_huecos("".join(visible)), "pdf", ocultos, _indicadores_pdf(datos))
