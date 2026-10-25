"""Une todas las revisiones del PC en un solo informe con nota de salud."""

import time
from dataclasses import dataclass, field

from .comun import GRAVEDADES, PESO_NOTA, HallazgoRevisor, Ubicaciones
from .conectores import revisar_conectores
from .extensiones import revisar_extensiones
from .modelos import revisar_modelos
from .red import revisar_red

AREAS = {"extensiones": "Extensiones del navegador", "conectores": "Conectores MCP de las apps de IA",
         "modelos": "Modelos de IA descargados", "red": "Red y Ollama", "secretos": "Claves y secretos"}
ICONO = {"CRITICA": "🔴", "ALTA": "🟠", "MEDIA": "🟡", "BAJA": "🔵", "INFO": "⚪"}


@dataclass
class InformeRevisor:
    hallazgos: list[HallazgoRevisor]
    resumen: dict = field(default_factory=dict)
    segundos: float = 0.0

    @property
    def nota(self) -> int:
        return max(0, 100 - sum(PESO_NOTA[h.gravedad] for h in self.hallazgos))

    def cuenta(self) -> dict[str, int]:
        return {g: sum(1 for h in self.hallazgos if h.gravedad == g) for g in GRAVEDADES}

    def a_dict(self) -> dict:
        return {"nota": self.nota, "cuenta": self.cuenta(), "resumen": self.resumen,
                "hallazgos": [h.a_dict() for h in self.hallazgos], "segundos": round(self.segundos, 2)}

    def a_markdown(self) -> str:
        lineas = [f"# Revisión de la IA del PC: {self.nota}/100", "",
                  " · ".join(f"{ICONO[g]} {n} {g.lower()}" for g, n in self.cuenta().items() if n), ""]
        r = self.resumen
        lineas += [f"- Navegadores revisados: {', '.join(r.get('navegadores', [])) or 'ninguno'} "
                   f"({r.get('extensiones_revisadas', 0)} extensiones)",
                   "- Apps con conectores MCP: " + (", ".join(f"{app} ({len(v)})" for app, v in
                                                          r.get("conectores", {}).items()) or "ninguna"),
                   f"- Modelos de Ollama: {', '.join(r.get('modelos_ollama', [])) or 'ninguno'}", ""]
        for area, titulo in AREAS.items():
            del_area = [h for h in self.hallazgos if h.area == area]
            if not del_area:
                continue
            lineas += [f"## {titulo}", ""]
            for h in del_area:
                lineas += [f"### {ICONO[h.gravedad]} {h.titulo}", "", h.detalle, "", f"**Qué hacer:** {h.recomendacion}"]
                if h.ruta:
                    lineas.append(f"\n`{h.ruta}`")
                lineas.append("")
        return "\n".join(lineas)


class Revisor:
    """El 'médico' de la IA del PC. No cambia nada: solo mira y explica."""

    def __init__(self, ubicaciones: Ubicaciones | None = None, carpetas_extra=(), comprobar_red: bool = True):
        self.ubic = ubicaciones or Ubicaciones.del_sistema()
        self.carpetas_extra = list(carpetas_extra)
        self.comprobar_red = comprobar_red

    def revisar(self) -> InformeRevisor:
        inicio = time.perf_counter()
        hallazgos, resumen = [], {}
        proyectos = self.carpetas_extra + ([str(self.ubic.home / "proyectos" / p) for p in self._proyectos_demo()]
                                           if self.ubic.simulado else [])
        for funcion, args in ((revisar_extensiones, ()), (revisar_conectores, (proyectos,)),
                              (revisar_modelos, (self.carpetas_extra,)),
                              (revisar_red, (self.comprobar_red, proyectos))):
            h, r = funcion(self.ubic, *args)
            hallazgos += h
            resumen.update(r)
        hallazgos.sort(key=lambda h: (GRAVEDADES.index(h.gravedad), h.area))
        return InformeRevisor(hallazgos, resumen, time.perf_counter() - inicio)

    def _proyectos_demo(self):
        carpeta = self.ubic.home / "proyectos"
        return sorted(p.name for p in carpeta.iterdir() if p.is_dir()) if carpeta.is_dir() else []
