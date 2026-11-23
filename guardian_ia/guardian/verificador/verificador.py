"""El verificador junta todas las revisiones de la respuesta de la IA."""

from dataclasses import dataclass, field
from typing import Optional

from ..ia import ErrorIA
from .eco import revisar_eco
from .enlaces import revisar_enlaces
from .salida import HallazgoVerificacion, revisar_salida

ORDEN = {"PELIGRO": 0, "AVISO": 1, "INFO": 2}


@dataclass
class InformeVerificacion:
    hallazgos: list[HallazgoVerificacion] = field(default_factory=list)
    respaldo: Optional[dict] = None
    avisos: list[str] = field(default_factory=list)

    @property
    def nivel(self) -> str:
        gravedades = {h.gravedad for h in self.hallazgos}
        return "PELIGRO" if "PELIGRO" in gravedades else "AVISO" if "AVISO" in gravedades else "OK"

    def resumen(self) -> dict[str, int]:
        cuenta: dict[str, int] = {}
        for h in self.hallazgos:
            cuenta[h.tipo] = cuenta.get(h.tipo, 0) + 1
        return cuenta


class Verificador:
    def __init__(self, juez_respaldo=None, comprobar_enlaces: bool = False):
        self.juez_respaldo = juez_respaldo
        self.comprobar_enlaces = comprobar_enlaces

    def revisar(self, respuesta_ia: str, contexto: str = "", boveda=None,
                documento: Optional[str] = None, canario: Optional[str] = None,
                peticion: Optional[str] = None, leido: Optional[str] = None) -> InformeVerificacion:
        """canario: código secreto escondido en las instrucciones de la IA. Si aparece en la respuesta,
        alguien ha conseguido que la IA cuente sus instrucciones internas (OWASP LLM07).
        leido: lo que ha leído la IA y no has escrito tú (documentos, webs, resultados de herramientas);
        peticion: lo que has escrito tú. Con ellos se mira si la IA repite lo que pedía una trampa."""
        informe = InformeVerificacion()
        if canario and canario in respuesta_ia:
            informe.hallazgos.append(HallazgoVerificacion(
                "fuga_de_instrucciones", "PELIGRO", "La IA ha repetido sus instrucciones internas (ha escrito el "
                "código secreto que solo estaba en ellas): alguien ha conseguido manipularla.", canario))
        informe.hallazgos += revisar_salida(respuesta_ia, boveda)
        informe.hallazgos += revisar_enlaces(respuesta_ia, contexto, self.comprobar_enlaces)
        if leido:
            informe.hallazgos += revisar_eco(respuesta_ia, leido, peticion or "")
        if documento and self.juez_respaldo is not None:
            try:
                informe.respaldo = self.juez_respaldo.juzgar(respuesta_ia, documento)
            except ErrorIA as e:
                informe.avisos.append(f"No he podido comprobar el respaldo en el documento: {e}")
            else:
                for frase in informe.respaldo["contradichas"]:
                    informe.hallazgos.append(HallazgoVerificacion(
                        "contradice_documento", "AVISO", "Esta frase de la IA CONTRADICE lo que pone el documento.",
                        frase))
                for frase in informe.respaldo["sin_respaldo"]:
                    informe.hallazgos.append(HallazgoVerificacion(
                        "sin_respaldo", "INFO", "El documento no dice esto: puede ser conocimiento general de la IA "
                        "o un invento.", frase))
        informe.hallazgos.sort(key=lambda h: ORDEN[h.gravedad])
        return informe
