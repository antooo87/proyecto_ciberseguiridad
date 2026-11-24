"""Leer correos guardados (.eml): quién lo manda de verdad, adónde llevan los enlaces y qué esconde.

Un .eml es el correo tal y como viaja por Internet (así lo guardan Outlook, Thunderbird o Gmail con «Descargar
mensaje»): cabeceras (De, Para, Asunto...) y el cuerpo, casi siempre codificado (quoted-printable, base64) y en
dos versiones, texto y HTML. Leído «a pelo» se ve «est=C3=A1», un IBAN puede quedar partido en dos líneas y los
enlaces del HTML pueden decir una cosa y llevar a otra. Aquí se descodifica todo con la librería estándar de
Python (email) y se sacan las pistas que usan «¿Es una estafa?» y la aduana:

  - el remitente de verdad (el nombre que se ve y la dirección real) y si las respuestas van a otra dirección;
  - los enlaces del HTML: el texto que ves y adónde llevan de verdad;
  - el texto escondido con estilos (letra de tamaño 0, blanca, display:none) y los comentarios HTML: el truco
    que se descubrió en 2025 para engañar a la IA que te resume el correo (Gemini en Gmail);
  - los adjuntos, para avisar de los que son programas disfrazados («factura.pdf.iso»).

Solo usa la librería estándar y no abre nada de Internet.
"""

import re
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser
from pathlib import PurePath

# Adjuntos que pueden ejecutar código o abrir una web falsa. Un .pdf o un .docx normal no está aquí.
EXTENSIONES_PELIGROSAS = {
    ".exe", ".scr", ".com", ".pif", ".bat", ".cmd", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta", ".lnk",
    ".iso", ".img", ".vhd", ".vhdx", ".msi", ".jar", ".cpl", ".reg", ".chm", ".html", ".htm", ".shtml", ".svg",
    ".xll", ".one", ".docm", ".xlsm", ".pptm",
}
DOCUMENTOS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".txt", ".zip"}

_VACIAS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track",
           "wbr"}
_BLOQUES = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "blockquote",
            "section", "article", "header", "footer"}
# Estilos con los que se esconde texto. El blanco solo cuenta si no hay un fondo de color (un botón azul con letra
# blanca SÍ se ve).
_OCULTO = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0?\.?0+\s*(?:;|!|$)"
    r"|font-size\s*:\s*(?:0|0?\.\d+|1)\s*(?:px|pt|em|rem|%)?\s*(?:;|!|$)"
    r"|(?:max-)?height\s*:\s*0\s*(?:px)?\s*(?:;|!|$)", re.IGNORECASE)
_BLANCO = re.compile(r"(?<![-\w])color\s*:\s*(?:white|#fff\b|#ffffff\b|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))",
                     re.IGNORECASE)
_FONDO = re.compile(r"background", re.IGNORECASE)


@dataclass
class Correo:
    de: str = ""  # tal cual: "Correos <avisos@correos-envios.top>"
    nombre: str = ""  # lo que ves como remitente: "Correos"
    direccion: str = ""  # la dirección real: avisos@correos-envios.top
    responder_a: str = ""  # adónde irían tus respuestas (cabecera Reply-To), si es otra
    para: str = ""
    asunto: str = ""
    fecha: str = ""
    texto: str = ""  # el cuerpo que se ve, en texto
    ocultos: list[str] = field(default_factory=list)  # texto escondido con estilos o en comentarios HTML
    enlaces: list[tuple[str, str]] = field(default_factory=list)  # (texto que se ve, adónde lleva de verdad)
    adjuntos: list[str] = field(default_factory=list)

    @property
    def dominio(self) -> str:
        return self.direccion.rsplit("@", 1)[-1].lower() if "@" in self.direccion else ""

    @property
    def dominio_respuesta(self) -> str:
        direccion = parseaddr(self.responder_a)[1]
        return direccion.rsplit("@", 1)[-1].lower() if "@" in direccion else ""

    def cabeceras(self) -> str:
        lineas = [f"De: {self.de}", f"Para: {self.para}"]
        if self.responder_a:
            lineas.append(f"Responder a: {self.responder_a}")
        lineas += [f"Fecha: {self.fecha}", f"Asunto: {self.asunto}"]
        return "\n".join(lineas) + "\n"

    def como_texto(self, con_ocultos: bool = True) -> str:
        """Todo lo que importa del correo en texto: cabeceras, cuerpo, adónde van los enlaces y los adjuntos."""
        partes = [self.cabeceras(), self.texto.strip()]
        if con_ocultos and self.ocultos:
            partes.append("[Texto escondido en el correo]\n" + "\n".join(self.ocultos))
        destinos = [destino for texto, destino in self.enlaces if destino and destino not in self.texto]
        if destinos:
            partes.append("[Adónde llevan los enlaces]\n" + "\n".join(dict.fromkeys(destinos)))
        if self.adjuntos:
            partes.append("[Adjuntos] " + ", ".join(self.adjuntos))
        return "\n\n".join(p for p in partes if p) + "\n"


def adjunto_peligroso(nombre: str) -> str | None:
    """Si el adjunto puede ser un programa o una web falsa, explica por qué; si no, None."""
    sufijos = [s.lower() for s in PurePath(nombre.strip().rstrip(".")).suffixes]
    if not sufijos or sufijos[-1] not in EXTENSIONES_PELIGROSAS:
        return None
    if len(sufijos) >= 2 and sufijos[-2] in DOCUMENTOS:
        return (f"«{nombre}» se hace pasar por un {sufijos[-2][1:].upper()}, pero es un archivo {sufijos[-1]}: al "
                "abrirlo puede instalar un programa o llevarte a una web falsa.")
    return (f"«{nombre}» es un archivo {sufijos[-1]}: puede ejecutar código o abrir una web falsa. Un proveedor de "
            "verdad manda las facturas en PDF.")


class _LectorHTML(HTMLParser):
    """Separa lo que se ve de lo que está escondido, y apunta los enlaces (texto que se ve -> destino real)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pila: list[tuple[str, bool, bool]] = []  # (etiqueta, ¿escondido?, ¿tiene fondo de color?)
        self.visible: list[str] = []
        self.oculto: list[str] = []
        self.enlaces: list[tuple[str, str]] = []
        self._enlace: list[str] | None = None
        self._destino = ""
        self._saltar = 0  # dentro de <script> o <style>

    @property
    def escondido(self) -> bool:
        return any(e for _, e, _ in self.pila)

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        if etiqueta in ("script", "style", "head", "title"):
            self._saltar += 1
            return
        if etiqueta in _BLOQUES:
            (self.oculto if self.escondido else self.visible).append("\n")
        if etiqueta == "a":
            self._enlace, self._destino = [], (atributos.get("href") or "").strip()
        if etiqueta in _VACIAS:
            return
        estilo = atributos.get("style") or ""
        fondo = bool(_FONDO.search(estilo)) or "bgcolor" in atributos or any(f for _, _, f in self.pila)
        escondido = bool(_OCULTO.search(estilo)) or "hidden" in atributos or (bool(_BLANCO.search(estilo))
                                                                              and not fondo)
        if (atributos.get("color") or "").lower() in ("#fff", "#ffffff", "white") and not fondo:  # <font color=...>
            escondido = True
        self.pila.append((etiqueta, escondido, fondo))

    def handle_endtag(self, etiqueta):
        if etiqueta in ("script", "style", "head", "title"):
            self._saltar = max(0, self._saltar - 1)
            return
        if etiqueta == "a" and self._enlace is not None:
            self.enlaces.append((" ".join("".join(self._enlace).split()), self._destino))
            self._enlace = None
        if any(e == etiqueta for e, _, _ in self.pila):
            while self.pila:
                if self.pila.pop()[0] == etiqueta:
                    break
        if etiqueta in _BLOQUES:
            (self.oculto if self.escondido else self.visible).append("\n")

    def handle_data(self, datos):
        if self._saltar:
            return
        if self.escondido:
            self.oculto.append(datos)
        else:
            self.visible.append(datos)
            if self._enlace is not None:
                self._enlace.append(datos)

    def handle_comment(self, datos):
        if datos.strip():
            self.oculto.append(f"\n<!-- {datos.strip()} -->\n")


def _limpiar(trozos: list[str]) -> str:
    texto = "".join(trozos).replace("\xa0", " ")
    lineas = [" ".join(linea.split()) for linea in texto.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas)).strip()


def html_a_texto(html: str) -> tuple[str, list[str], list[tuple[str, str]]]:
    """(texto que se ve, trozos escondidos, enlaces)."""
    lector = _LectorHTML()
    lector.feed(html)
    lector.close()
    ocultos = [t for t in (_limpiar([o]) for o in re.split(r"\n(?=<!--)|(?<=-->)\n", "".join(lector.oculto))) if t]
    return _limpiar(lector.visible), ocultos, lector.enlaces


def leer_correo(datos: bytes) -> Correo:
    """Descodifica un .eml. Nunca falla por un correo mal formado: se queda con lo que pueda leer."""
    mensaje = BytesParser(policy=policy.default).parsebytes(datos)
    correo = Correo()

    def cabecera(nombre: str) -> str:
        try:
            return " ".join(str(mensaje.get(nombre, "") or "").split())
        except (ValueError, TypeError, IndexError):  # cabeceras rotas a propósito
            return ""

    correo.de, correo.para, correo.asunto, correo.fecha = (cabecera(c) for c in ("From", "To", "Subject", "Date"))
    correo.nombre, correo.direccion = parseaddr(correo.de)
    responder = cabecera("Reply-To")
    if responder and parseaddr(responder)[1].lower() != correo.direccion.lower():
        correo.responder_a = responder
    textos, htmls = [], []
    for parte in mensaje.walk():
        if parte.is_multipart():
            continue
        nombre = parte.get_filename()
        if nombre or parte.get_content_disposition() == "attachment":
            correo.adjuntos.append(nombre or "(adjunto sin nombre)")
            continue
        tipo = parte.get_content_type()
        if tipo not in ("text/plain", "text/html"):
            continue
        try:
            contenido = parte.get_content()
        except (LookupError, ValueError, AssertionError):  # charset inventado o codificación rota
            contenido = (parte.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        (htmls if tipo == "text/html" else textos).append(contenido)
    for html in htmls:
        visible, ocultos, enlaces = html_a_texto(html)
        correo.ocultos += ocultos
        correo.enlaces += enlaces
        if not textos:
            textos.append(visible)
    correo.texto = "\n\n".join(t.strip() for t in textos if t and t.strip())
    return correo
