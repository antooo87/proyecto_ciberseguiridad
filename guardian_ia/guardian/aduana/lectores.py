"""Lectores de documentos para la aduana: texto, Word (.docx), PowerPoint (.pptx), Excel (.xlsx) y PDF.

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
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union
from xml.etree import ElementTree

try:  # defusedxml lee el XML sin expandir entidades ni DTD (bombas XML, XXE); si no está instalado, se usa el
    from defusedxml import ElementTree as _XMLSeguro  # lector normal con la comprobación de DOCTYPE de _xml()
except ImportError:  # pragma: no cover
    _XMLSeguro = None

MAX_BYTES = 50 * 1024 * 1024  # 50 MB por archivo
MAX_PARTE_ZIP = 20 * 1024 * 1024  # 20 MB descomprimidos por cada parte del Word
MAX_PAGINAS_PDF = 300
MAX_CELDAS_EXCEL = 200_000  # una hoja enorme se recorta: para buscar trampas no hace falta leerla entera
MIN_OCULTO = 3  # trozos más cortos (un espacio en blanco, un punto) no cuentan

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXTENSIONES_WORD = (".docx", ".docm", ".dotx", ".dotm")
EXTENSIONES_POWERPOINT = (".pptx", ".pptm", ".potx", ".potm", ".ppsx", ".ppsm")
EXTENSIONES_EXCEL = (".xlsx", ".xlsm", ".xltx", ".xltm")
EXTENSIONES_OFFICE = EXTENSIONES_WORD + EXTENSIONES_POWERPOINT + EXTENSIONES_EXCEL
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
    formato: str  # "texto", "word", "powerpoint", "excel" o "pdf"
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
    if datos[:2] == b"PK" and extension in EXTENSIONES_POWERPOINT:
        return leer_pptx(datos)
    if datos[:2] == b"PK" and extension in EXTENSIONES_EXCEL:
        return leer_xlsx(datos)
    if datos[:2] == b"PK" and extension in EXTENSIONES_WORD + ("",):
        return _leer_office_sin_nombre(datos) if not extension else leer_docx(datos)
    if extension in (".doc", ".xls", ".ppt", ".odt", ".ods", ".odp", ".rtf"):
        raise ErrorLectura(f"Formato {extension} no soportado todavía: guárdalo como .docx, .pptx, .xlsx, .pdf o "
                           "texto.")
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
        if _XMLSeguro is not None:
            return _XMLSeguro.fromstring(datos, forbid_dtd=True)
        return ElementTree.fromstring(datos)
    except ElementTree.ParseError as e:
        raise ErrorLectura(f"La parte {nombre} no es XML válido: {e}") from e
    except ValueError as e:  # defusedxml: DTDForbidden, EntitiesForbidden...
        raise ErrorLectura(f"La parte {nombre} trae construcciones XML peligrosas: se rechaza por seguridad.") from e


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
        texto += _metadatos_office(z, lector.ocultos)
        peligros = _peligros_office(z)
    ocultos = [o for o in lector.ocultos if len(o.texto.strip()) >= MIN_OCULTO]
    return Lectura(texto, _limpiar_huecos(visible), "word", ocultos, peligros)


def _metadatos_office(z: zipfile.ZipFile, ocultos: list[TextoOculto]) -> str:
    """Título, asunto, descripción y palabras clave del archivo: no se ven, pero hay programas que se los pasan a la IA."""
    propiedades = _xml(z, "docProps/core.xml")
    if propiedades is None:
        return ""
    meta = " | ".join(" ".join(e.itertext()).strip() for e in propiedades
                      if e.tag.rsplit("}", 1)[-1] in ("title", "subject", "description", "keywords")
                      and "".join(e.itertext()).strip())
    if not meta:
        return ""
    ocultos.append(TextoOculto(meta, "metadatos (propiedades del archivo)", "propiedades del documento", truco=False))
    return f"\n[Propiedades del documento] {meta}\n"


def _peligros_office(z: zipfile.ZipFile) -> list[Peligro]:
    peligros = _relaciones_peligrosas(z)
    if any(n.lower().endswith("vbaproject.bin") for n in z.namelist()):
        peligros.append(Peligro("El documento trae MACROS (vbaProject.bin): no las actives si no sabes de "
                                "dónde viene.", 2))
    return peligros


def _leer_office_sin_nombre(datos: bytes) -> Lectura:
    """Bytes de un zip sin nombre de archivo: se mira por dentro si es un Word, un PowerPoint o un Excel."""
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            nombres = set(z.namelist())
    except zipfile.BadZipFile as e:
        raise ErrorLectura("No es un documento de Office válido (el zip está roto).") from e
    if "ppt/presentation.xml" in nombres:
        return leer_pptx(datos)
    if "xl/workbook.xml" in nombres:
        return leer_xlsx(datos)
    return leer_docx(datos)


def _destinos(z: zipfile.ZipFile, parte: str) -> dict[str, str]:
    """Relaciones internas de una parte (rId -> ruta dentro del zip). Ej.: rId2 -> ppt/slides/slide1.xml."""
    carpeta, nombre = posixpath.split(parte)
    raiz = _xml(z, posixpath.join(carpeta, "_rels", nombre + ".rels"))
    destinos = {}
    for rel in raiz.iter(REL + "Relationship") if raiz is not None else ():
        if rel.get("TargetMode") == "External":
            continue
        destino = rel.get("Target", "")
        ruta = destino.lstrip("/") if destino.startswith("/") else posixpath.normpath(posixpath.join(carpeta, destino))
        destinos[rel.get("Id", "")] = ruta
    return destinos


def _texto_de(elem: Optional[ElementTree.Element]) -> str:
    return " ".join(" ".join(elem.itertext()).split()) if elem is not None else ""


def _juntar_oculto(ocultos: list[TextoOculto], texto: str, motivo: str, lugar: str, truco: bool = True) -> None:
    """Trozos seguidos con el mismo motivo en el mismo sitio van juntos."""
    ultimo = ocultos[-1] if ocultos else None
    if ultimo and ultimo.motivo == motivo and ultimo.lugar == lugar and ultimo.truco == truco:
        ultimo.texto += " " + texto
    else:
        ocultos.append(TextoOculto(texto, motivo, lugar, truco))


# ---------------------------------------------------------------- PowerPoint (.pptx)
def _luz_drawingml(nodo: Optional[ElementTree.Element]) -> Optional[float]:
    """Luz (0 negro, 1 blanco) del primer color que haya dentro de un relleno de PowerPoint. None si no se sabe."""
    if nodo is None:
        return None
    for elem in nodo.iter():
        etiqueta = elem.tag
        if etiqueta == A + "srgbClr":
            return _hex_a_luz(elem.get("val"))
        if etiqueta == A + "schemeClr":
            valor = elem.get("val", "")
            return 1.0 if valor in ("bg1", "lt1", "bg2", "lt2") else 0.0 if valor in ("tx1", "dk1", "tx2", "dk2") else None
        if etiqueta == A + "sysClr":
            return _hex_a_luz(elem.get("lastClr"))
        if etiqueta == A + "prstClr":
            return {"white": 1.0, "black": 0.0}.get(elem.get("val", ""))
    return None


def _fondo_oscuro_pptx(raices: list[Optional[ElementTree.Element]]) -> bool:
    """¿El fondo de la diapositiva es oscuro (o una imagen)? Se mira la diapositiva, su diseño y su patrón."""
    for raiz in raices:
        if raiz is None:
            continue
        fondo = raiz.find(f"{P}cSld/{P}bg")
        if fondo is not None:
            if fondo.find(f".//{A}blipFill") is not None or fondo.find(f".//{A}gradFill") is not None:
                return True  # una foto o un degradado: puede ser oscuro, mejor no dar falsas alarmas
            luz = _luz_drawingml(fondo)
            return luz is None or luz < 0.5
    for raiz in raices:  # sin fondo propio: si el patrón cambia los colores (bg1 = dk1), el tema es oscuro
        mapa = raiz.find(P + "clrMap") if raiz is not None else None
        if mapa is not None:
            return mapa.get("bg1") == "dk1"
    return False


def _forma_con_relleno(forma: ElementTree.Element) -> Optional[float]:
    """Luz del relleno de una forma: 0.0 = oscuro o desconocido (la letra blanca se vería); 1.0 = claro; None = sin relleno."""
    sppr = forma.find(P + "spPr")
    if sppr is not None:
        if sppr.find(A + "noFill") is not None:
            return None
        if sppr.find(A + "solidFill") is not None:
            luz = _luz_drawingml(sppr.find(A + "solidFill"))
            return 0.0 if luz is None else luz
        if any(sppr.find(A + x) is not None for x in ("gradFill", "blipFill", "pattFill")):
            return 0.0
    estilo = forma.find(f"{P}style/{A}fillRef")
    if estilo is not None and estilo.get("idx", "0") != "0":
        return 0.0  # relleno del tema (azul, naranja...): la letra blanca se ve
    return None


class _LectorDiapositiva:
    def __init__(self, numero: int, ancho: int, alto: int, fondo_oscuro: bool, oculta: bool):
        self.lugar = f"diapositiva {numero}"
        self.ancho, self.alto = ancho, alto
        self.fondo_oscuro = fondo_oscuro
        self.oculta = oculta
        self.texto: list[str] = []
        self.visible: list[str] = []
        self.ocultos: list[TextoOculto] = []

    def recorrer(self, arbol: ElementTree.Element, nivel: int = 0, motivo_forma: Optional[str] = None,
                 relleno: Optional[float] = None, en_tabla: bool = False) -> None:
        for forma in arbol:
            etiqueta = forma.tag.rsplit("}", 1)[-1]
            if etiqueta not in ("sp", "grpSp", "graphicFrame", "pic", "cxnSp"):
                continue
            nv = forma.find(f"{P}nvSpPr/{P}cNvPr")
            if nv is None:
                nv = next((e for e in forma.iter(P + "cNvPr")), None)
            motivo = motivo_forma
            if motivo is None and nv is not None and nv.get("hidden") in ("1", "true"):
                motivo = "forma oculta (no se ve en la diapositiva)"
            if motivo is None and nivel == 0:
                motivo = self._fuera(forma)
            if nv is not None and len((nv.get("descr") or "").strip()) >= MIN_OCULTO:
                alt = nv.get("descr").strip()
                self.texto.append(f"\n[Texto alternativo de imagen] {alt}\n")
                self.ocultos.append(TextoOculto(alt, "texto alternativo de una imagen", self.lugar, truco=False))
            if etiqueta == "grpSp":
                self.recorrer(forma, nivel + 1, motivo, relleno, en_tabla)
            elif etiqueta == "graphicFrame":
                for celda in forma.iter(A + "tc"):
                    for parrafo in celda.iter(A + "p"):
                        self._parrafo(parrafo, motivo, None, en_tabla=True)
            elif etiqueta == "sp":
                propio = _forma_con_relleno(forma)
                cuerpo = forma.find(P + "txBody")
                for parrafo in cuerpo.iter(A + "p") if cuerpo is not None else ():
                    self._parrafo(parrafo, motivo, propio if propio is not None else relleno, en_tabla)

    def _fuera(self, forma: ElementTree.Element) -> Optional[str]:
        xfrm = forma.find(f"{P}spPr/{A}xfrm")
        if xfrm is None:
            xfrm = forma.find(f"{P}grpSpPr/{A}xfrm")
        if xfrm is None:
            xfrm = forma.find(P + "xfrm")
        off, ext = (xfrm.find(A + "off"), xfrm.find(A + "ext")) if xfrm is not None else (None, None)
        if off is None or ext is None or not self.ancho:
            return None
        try:
            x, y = int(off.get("x", 0)), int(off.get("y", 0))
            cx, cy = int(ext.get("cx", 0)), int(ext.get("cy", 0))
        except ValueError:
            return None
        if x >= self.ancho or y >= self.alto or x + cx <= 0 or y + cy <= 0:
            return "fuera de la diapositiva"
        return None

    def _parrafo(self, parrafo: ElementTree.Element, motivo_forma: Optional[str], relleno: Optional[float],
                 en_tabla: bool) -> None:
        for run in parrafo:
            etiqueta = run.tag
            if etiqueta == A + "br":
                self.texto.append("\n")
                self.visible.append("\n")
                continue
            if etiqueta not in (A + "r", A + "fld"):
                continue
            trozo = "".join(t.text or "" for t in run.iter(A + "t"))
            if not trozo:
                continue
            self.texto.append(trozo)
            motivo = motivo_forma or self._motivo_run(run.find(A + "rPr"), relleno, en_tabla)
            if motivo is None and not self.oculta:
                self.visible.append(trozo)
            elif motivo is not None:
                truco = not motivo.startswith("forma oculta")
                _juntar_oculto(self.ocultos, trozo, motivo, self.lugar, truco)
            else:
                _juntar_oculto(self.ocultos, trozo, "diapositiva oculta (no sale al presentar)", self.lugar, False)
        self.texto.append("\n")
        self.visible.append("\n")

    def _motivo_run(self, rpr: Optional[ElementTree.Element], relleno: Optional[float], en_tabla: bool) -> Optional[str]:
        if rpr is None:
            return None
        motivos = []
        luz = _luz_drawingml(rpr.find(A + "solidFill"))
        fondo_claro = (relleno is not None and relleno >= 0.5) or (relleno is None and not self.fondo_oscuro)
        if luz is not None and luz >= 0.94 and fondo_claro and not en_tabla:
            motivos.append("letra blanca sobre fondo blanco")
        tam = rpr.get("sz", "")
        if tam.isdigit() and int(tam) <= 200:
            motivos.append(f"letra diminuta ({int(tam) / 100:g} pt)")
        return " y ".join(motivos) or None


def leer_pptx(datos: bytes) -> Lectura:
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile as e:
        raise ErrorLectura("No es un .pptx válido (el zip está roto).") from e
    with z:
        presentacion = _xml(z, "ppt/presentation.xml")
        if presentacion is None:
            raise ErrorLectura("No es una presentación de PowerPoint: falta ppt/presentation.xml.")
        tam = presentacion.find(P + "sldSz")
        ancho = int(tam.get("cx", 0)) if tam is not None and (tam.get("cx") or "").isdigit() else 0
        alto = int(tam.get("cy", 0)) if tam is not None and (tam.get("cy") or "").isdigit() else 0
        rels = _destinos(z, "ppt/presentation.xml")
        orden = [rels.get(s.get(R + "id", "")) for s in presentacion.iter(P + "sldId")]
        diapositivas = [d for d in orden if d] or sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
        texto, visible, ocultos = [], [], []
        for numero, parte in enumerate(diapositivas, 1):
            raiz = _xml(z, parte)
            if raiz is None:
                continue
            rels_diapo = _destinos(z, parte)
            diseno = next((d for d in rels_diapo.values() if "slideLayouts/" in d), None)
            raiz_diseno = _xml(z, diseno) if diseno else None
            patron = next((d for d in _destinos(z, diseno).values() if "slideMasters/" in d), None) if diseno else None
            raiz_patron = _xml(z, patron) if patron else None
            lector = _LectorDiapositiva(numero, ancho, alto, _fondo_oscuro_pptx([raiz, raiz_diseno, raiz_patron]),
                                        oculta=raiz.get("show") in ("0", "false"))
            arbol = raiz.find(f"{P}cSld/{P}spTree")
            if arbol is not None:
                lector.recorrer(arbol)
            cabecera = f"[Diapositiva {numero}]\n"
            texto.append(cabecera + "".join(lector.texto))
            if not lector.oculta:
                visible.append(cabecera + "".join(lector.visible))
            ocultos += lector.ocultos
            notas = next((d for d in rels_diapo.values() if "notesSlides/" in d), None)
            texto_notas = _texto_notas(_xml(z, notas)) if notas else ""
            if len(texto_notas) >= MIN_OCULTO:
                texto.append(f"[Notas del orador de la diapositiva {numero}] {texto_notas}\n")
                ocultos.append(TextoOculto(texto_notas, "notas del orador (no salen en la diapositiva)",
                                           f"diapositiva {numero}", truco=False))
        for parte in sorted(n for n in z.namelist() if re.fullmatch(r"ppt/comments/[^/]+\.xml", n)):
            comentario = _texto_de(_xml(z, parte))
            if len(comentario) >= MIN_OCULTO:
                texto.append(f"[Comentarios] {comentario}\n")
                ocultos.append(TextoOculto(comentario, "comentarios de revisión", "comentarios", truco=False))
        texto_final = "\n".join(texto) + _metadatos_office(z, ocultos)
        peligros = _peligros_office(z)
    ocultos = [o for o in ocultos if len(o.texto.strip()) >= MIN_OCULTO]
    return Lectura(texto_final, _limpiar_huecos("\n".join(visible)), "powerpoint", ocultos, peligros)


def _texto_notas(raiz: Optional[ElementTree.Element]) -> str:
    """Texto de la página de notas, sin el número de diapositiva ni la miniatura."""
    if raiz is None:
        return ""
    trozos = []
    for forma in raiz.iter(P + "sp"):
        marcador = forma.find(f"{P}nvSpPr/{P}nvPr/{P}ph")
        if marcador is not None and marcador.get("type") in ("sldNum", "sldImg", "hdr", "ftr", "dt"):
            continue
        trozos.append(_texto_de(forma.find(P + "txBody")))
    return " ".join(t for t in trozos if t)


# ---------------------------------------------------------------- Excel (.xlsx)
def _luz_excel(color: Optional[ElementTree.Element]) -> Optional[float]:
    """Luz de un color de Excel (<color> o <fgColor>): rgb, color del tema o de la paleta antigua."""
    if color is None:
        return None
    if color.get("rgb"):
        return _hex_a_luz(color.get("rgb")[-6:])
    try:
        tinte = float(color.get("tint", "0"))
    except ValueError:
        tinte = 0.0
    if color.get("theme") is not None:
        tema = color.get("theme")
        if tema in ("0", "2"):  # "Fondo 1" y "Fondo 2": blanco y gris muy claro en el tema normal
            return 1.0
        return 0.9 if tinte > 0.5 else 0.2  # texto y colores de énfasis; muy aclarados casi no se distinguen del blanco
    if color.get("indexed") is not None:
        return 1.0 if color.get("indexed") in ("1", "9", "65") else 0.2
    return None


class _EstilosExcel:
    """Para cada estilo de celda: si la letra es blanca, el relleno oscuro, el tamaño y si el formato esconde el valor."""

    def __init__(self, raiz: Optional[ElementTree.Element]):
        self.estilos: list[tuple[bool, Optional[float], bool, bool]] = []
        if raiz is None:
            return
        formatos = {nf.get("numFmtId"): nf.get("formatCode", "") for nf in raiz.iter(S + "numFmt")}
        fuentes = []
        for fuente in raiz.findall(f"{S}fonts/{S}font"):
            luz = _luz_excel(fuente.find(S + "color"))
            tam = fuente.find(S + "sz")
            try:
                puntos = float(tam.get("val")) if tam is not None else None
            except (TypeError, ValueError):
                puntos = None
            fuentes.append((luz is not None and luz >= 0.94, puntos))
        rellenos = []
        for relleno in raiz.findall(f"{S}fills/{S}fill"):
            patron = relleno.find(S + "patternFill")
            if relleno.find(S + "gradientFill") is not None:
                rellenos.append(True)
            elif patron is not None and patron.get("patternType") not in (None, "none"):
                luz = _luz_excel(patron.find(S + "fgColor"))
                rellenos.append(luz is None or luz < 0.5)
            else:
                rellenos.append(False)
        for xf in raiz.findall(f"{S}cellXfs/{S}xf"):
            blanca, puntos = fuentes[int(xf.get("fontId", 0))] if int(xf.get("fontId", 0)) < len(fuentes) else (False, None)
            oscuro = rellenos[int(xf.get("fillId", 0))] if int(xf.get("fillId", 0)) < len(rellenos) else False
            formato = formatos.get(xf.get("numFmtId", ""), "").replace('"', "")
            self.estilos.append((blanca, puntos, oscuro, formato.strip() == ";;;"))

    def motivo(self, indice: Optional[str]) -> Optional[str]:
        if not indice or not indice.isdigit() or int(indice) >= len(self.estilos):
            return None
        blanca, puntos, oscuro, sin_formato = self.estilos[int(indice)]
        if sin_formato:
            return "formato ;;; (la celda no enseña su valor)"
        motivos = []
        if blanca and not oscuro:
            motivos.append("letra blanca sobre fondo blanco")
        if puntos is not None and puntos <= 2:
            motivos.append(f"letra diminuta ({puntos:g} pt)")
        return " y ".join(motivos) or None


def _columna(referencia: str) -> int:
    """'AB12' -> 28 (número de columna)."""
    numero = 0
    for letra in referencia:
        if not letra.isalpha():
            break
        numero = numero * 26 + ord(letra.upper()) - 64
    return numero


def _textos_compartidos(raiz: Optional[ElementTree.Element]) -> list[str]:
    textos = []
    for si in raiz.findall(S + "si") if raiz is not None else ():
        trozos = [si.findtext(S + "t") or ""] + ["".join(t.text or "" for t in r.iter(S + "t")) for r in si.findall(S + "r")]
        textos.append("".join(trozos))
    return textos


FORMULA_PELIGROSA = re.compile(r"(?i)(?:\b(?:cmd|powershell|pwsh|mshta|rundll32|regsvr32|certutil|wscript|cscript|msexcel)"
                               r"\s*\||\bDDE(?:AUTO)?\b|\bWEBSERVICE\s*\(|\bCALL\s*\(|\bREGISTER\s*\()")


def leer_xlsx(datos: bytes) -> Lectura:
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile as e:
        raise ErrorLectura("No es un .xlsx válido (el zip está roto).") from e
    with z:
        libro = _xml(z, "xl/workbook.xml")
        if libro is None:
            raise ErrorLectura("No es un libro de Excel: falta xl/workbook.xml.")
        rels = _destinos(z, "xl/workbook.xml")
        compartidos = _textos_compartidos(_xml(z, "xl/sharedStrings.xml"))
        estilos = _EstilosExcel(_xml(z, "xl/styles.xml"))
        texto, visible, ocultos = [], [], []
        peligros = _peligros_office(z)
        formulas_peligrosas = []
        celdas = 0
        for hoja in libro.iter(S + "sheet"):
            nombre, estado = hoja.get("name", "?"), hoja.get("state", "visible")
            parte = rels.get(hoja.get(R + "id", ""))
            raiz = _xml(z, parte) if parte else None
            if raiz is None:
                continue
            columnas_ocultas = set()
            for col in raiz.iter(S + "col"):
                if col.get("hidden") in ("1", "true"):
                    try:
                        columnas_ocultas.update(range(int(col.get("min", 0)), min(int(col.get("max", 0)), 16384) + 1))
                    except ValueError:
                        pass
            cabecera = f"[Hoja: {nombre}]\n"
            lineas_texto, lineas_visibles = [cabecera], [cabecera]
            for fila in raiz.iter(S + "row"):
                fila_oculta = fila.get("hidden") in ("1", "true")
                todo, vistos = [], []
                for celda in fila.iter(S + "c"):
                    celdas += 1
                    if celdas > MAX_CELDAS_EXCEL:
                        break
                    formula = celda.findtext(S + "f") or ""
                    if formula and FORMULA_PELIGROSA.search(formula):
                        formulas_peligrosas.append(f"{nombre}!{celda.get('r', '?')}: ={formula[:80]}")
                    valor = _valor_celda(celda, compartidos)
                    if not valor:
                        continue
                    todo.append(valor)
                    lugar = f"hoja «{nombre}», celda {celda.get('r', '?')}"
                    if estado == "veryHidden":
                        _juntar_oculto(ocultos, valor, "hoja muy oculta (solo se ve con macros)", f"hoja «{nombre}»")
                    elif estado == "hidden":
                        _juntar_oculto(ocultos, valor, "hoja oculta", f"hoja «{nombre}»", truco=False)
                    elif (motivo := estilos.motivo(celda.get("s"))) is not None:
                        _juntar_oculto(ocultos, valor, motivo, lugar)
                    elif fila_oculta:
                        _juntar_oculto(ocultos, valor, "fila oculta", f"hoja «{nombre}», fila {fila.get('r', '?')}",
                                       truco=False)
                    elif _columna(celda.get("r", "")) in columnas_ocultas:
                        _juntar_oculto(ocultos, valor, "columna oculta", f"hoja «{nombre}»", truco=False)
                    else:
                        vistos.append(valor)
                if todo:
                    lineas_texto.append("\t".join(todo) + "\n")
                if vistos:
                    lineas_visibles.append("\t".join(vistos) + "\n")
                if celdas > MAX_CELDAS_EXCEL:
                    lineas_texto.append("[... hoja recortada: es demasiado grande]\n")
                    break
            texto.append("".join(lineas_texto))
            if estado == "visible":
                visible.append("".join(lineas_visibles))
        for parte in sorted(n for n in z.namelist() if re.fullmatch(r"xl/(?:comments\d*|threadedComments/[^/]+)\.xml", n)):
            comentario = _texto_de(_xml(z, parte))
            if len(comentario) >= MIN_OCULTO:
                texto.append(f"[Comentarios] {comentario}\n")
                ocultos.append(TextoOculto(comentario, "comentarios de las celdas", "comentarios", truco=False))
        for parte in (n for n in z.namelist() if n.startswith("xl/externalLinks/") and n.endswith(".xml")):
            raiz = _xml(z, parte)
            if raiz is not None and raiz.find(f".//{S}ddeLink") is not None:
                peligros.append(Peligro("El libro tiene un enlace DDE: al abrirlo puede intentar ejecutar un programa "
                                        "(técnica clásica de ataque con Excel).", 4))
        if formulas_peligrosas:
            peligros.append(Peligro(f"{len(formulas_peligrosas)} fórmula(s) que lanzan programas o llaman a Internet "
                                    f"(inyección de fórmulas), por ejemplo {formulas_peligrosas[0]}", 4))
        texto_final = "\n".join(texto) + _metadatos_office(z, ocultos)
    ocultos = [o for o in ocultos if len(o.texto.strip()) >= MIN_OCULTO]
    return Lectura(texto_final, _limpiar_huecos("\n".join(visible)), "excel", ocultos, peligros)


def _valor_celda(celda: ElementTree.Element, compartidos: list[str]) -> str:
    tipo = celda.get("t", "n")
    if tipo == "inlineStr":
        caja = celda.find(S + "is")
        return "".join(t.text or "" for t in caja.iter(S + "t")) if caja is not None else ""
    valor = celda.findtext(S + "v") or ""
    if tipo == "s":
        return compartidos[int(valor)] if valor.isdigit() and int(valor) < len(compartidos) else ""
    if tipo == "b":
        return "VERDADERO" if valor == "1" else "FALSO"
    return valor


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
