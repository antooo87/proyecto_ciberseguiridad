"""Detector de datos sensibles con expresiones regulares + validación.

Cada Regla dice:
  - qué tipo de dato busca (DNI, EMAIL...)
  - el molde (expresión regular) con la forma del dato
  - un validador opcional que comprueba que el dato cuadra de verdad
  - una prioridad, para decidir qué gana cuando dos reglas pillan el mismo trozo
"""

import re
from dataclasses import dataclass
from typing import Callable, Optional

from . import validadores as v


@dataclass(frozen=True)
class Hallazgo:
    """Un dato sensible encontrado en el texto."""

    tipo: str
    inicio: int  # posición del primer carácter
    fin: int  # posición justo después del último carácter
    valor: str
    origen: str = "regex"  # "regex" o "ia"
    prioridad: int = 5

    @property
    def longitud(self) -> int:
        return self.fin - self.inicio


@dataclass
class Regla:
    tipo: str
    patron: re.Pattern
    validador: Optional[Callable[[str], bool]] = None
    prioridad: int = 5
    grupo: int = 0  # 0 = todo el trozo; 1 = solo lo que hay entre paréntesis
    recortar: bool = False  # si no valida, probar quitando bloques del final


# Separador permitido dentro de un número: espacio, guion o punto
SEP = r"[ .-]?"

PALABRAS_CLAVE = r"contraseña|contrasena|password|passwd|pwd|clave de acceso|clave|pin"

REGLAS = [
    # --- Secretos (máxima prioridad: si se filtran, el daño es inmediato) ---
    Regla("CLAVE_PRIVADA", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
        prioridad=10),
    Regla("JWT", re.compile(
        r"\beyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"), prioridad=10),
    Regla("CLAVE_API", re.compile(
        r"\b(?:"
        r"(?:AKIA|ASIA)[0-9A-Z]{16}"  # Amazon AWS
        r"|gh[pousr]_[A-Za-z0-9]{36,}"  # GitHub
        r"|github_pat_[A-Za-z0-9_]{22,}"  # GitHub (nuevo formato)
        r"|sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"  # OpenAI / Anthropic
        r"|AIza[0-9A-Za-z_-]{35}"  # Google
        r"|xox[abprs]-[A-Za-z0-9-]{10,}"  # Slack
        r"|(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}"  # Stripe
        r")"), prioridad=9),
    # "contraseña: Verano2024" -> lo de después de los dos puntos
    Regla("CONTRASENA", re.compile(
        r"(?i)\b(?:" + PALABRAS_CLAVE + r")\s*[:=]\s*[\"']?([^\s\"',;]{3,})"),
        prioridad=8, grupo=1),
    # "mi contraseña es perro123" -> solo si tiene algún número o símbolo,
    # para no tapar frases normales como "la clave es practicar"
    Regla("CONTRASENA", re.compile(
        r"(?i)\b(?:" + PALABRAS_CLAVE + r")\s+(?:es|is)\s+[\"']?([^\s\"',;]{2,}[^\s\"',;.?])"),
        lambda valor: not valor.isalpha(), prioridad=8, grupo=1),

    # --- Identidad ---
    Regla("DNI", re.compile(r"\b\d{8}[ -]?[A-Za-z]\b"), v.dni_valido, prioridad=7),
    Regla("NIE", re.compile(r"\b[XYZxyz][ -]?\d{7}[ -]?[A-Za-z]\b"), v.nie_valido, prioridad=7),

    # --- Dinero ---
    Regla("IBAN", re.compile(
        r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]{4}){3,7}(?:[ -]?[A-Z0-9]{1,3})?\b"),
        v.iban_valido, prioridad=7, recortar=True),
    Regla("TARJETA", re.compile(
        r"(?<!\d)(?:(?:\d{4}[ -]?){3}\d{1,7}|\d{4}[ -]?\d{6}[ -]?\d{5})(?!\d)"),
        v.luhn_valido, prioridad=6),

    # --- Contacto ---
    Regla("EMAIL", re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), prioridad=6),
    Regla("TELEFONO", re.compile(
        r"(?<![\w+.-])(?:(?:\+|00)34" + SEP + r")?[6789](?:" + SEP + r"\d){8}(?![.-]?\d)"),
        prioridad=5),

    # --- Otros datos personales o técnicos ---
    Regla("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), v.ip_valida, prioridad=6),
    # Matrículas españolas desde 2000: 4 números y 3 consonantes (sin vocales, Ñ ni Q)
    Regla("MATRICULA", re.compile(r"\b\d{4}[ -]?[BCDFGHJKLMNPRSTVWXYZ]{3}\b"), prioridad=4),
]


def _validar_recortando(regla: Regla, texto_trozo: str) -> Optional[str]:
    """Si el trozo no valida, prueba a quitar bloques del final.

    Ejemplo: 'ES91 2100 0418 4502 0005 1332 PARA' no es un IBAN válido,
    pero quitando 'PARA' sí lo es.
    """
    if regla.validador is None or regla.validador(texto_trozo):
        return texto_trozo
    if not regla.recortar:
        return None
    partes = re.split(r"([ -])", texto_trozo)
    while len(partes) > 2:
        partes = partes[:-2]  # quita el último bloque y su separador
        candidato = "".join(partes)
        if regla.validador(candidato):
            return candidato
    return None


class DetectorRegex:
    """Busca datos sensibles usando las reglas de arriba."""

    def __init__(self, reglas=None, tipos_ignorados=()):
        self.reglas = [r for r in (reglas or REGLAS) if r.tipo not in tipos_ignorados]

    def detectar(self, texto: str) -> list[Hallazgo]:
        candidatos = []
        for regla in self.reglas:
            for m in regla.patron.finditer(texto):
                inicio, fin = m.span(regla.grupo)
                valor = _validar_recortando(regla, texto[inicio:fin])
                if valor is None:
                    continue
                candidatos.append(Hallazgo(
                    regla.tipo, inicio, inicio + len(valor), valor, "regex", regla.prioridad))
        return resolver_solapes(candidatos)


def resolver_solapes(hallazgos: list[Hallazgo]) -> list[Hallazgo]:
    """Si dos hallazgos se pisan, se queda el de más prioridad (y, si empatan, el más largo)."""
    ordenados = sorted(hallazgos, key=lambda h: (-h.prioridad, -h.longitud, h.inicio))
    elegidos: list[Hallazgo] = []
    for h in ordenados:
        if all(h.fin <= e.inicio or h.inicio >= e.fin for e in elegidos):
            elegidos.append(h)
    return sorted(elegidos, key=lambda h: h.inicio)
