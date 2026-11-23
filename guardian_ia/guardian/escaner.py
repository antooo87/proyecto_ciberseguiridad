"""Revisar carpetas y anonimizar documentos ANTES de dárselos a una IA.

Antes de subir una carpeta a ChatGPT, a un proyecto de Claude o a un agente con
acceso a tus archivos, conviene saber qué hay dentro:

  - ¿Qué documentos llevan datos personales (DNI, IBAN, correos...)?
  - ¿Alguno esconde órdenes para la IA (prompt injection)?

`escanear()` pasa cada archivo por el escudo y por la aduana y da un veredicto
por archivo. `anonimizar()` devuelve una copia del documento con los datos
tapados y sin el texto escondido, lista para compartir con cualquier IA.
Todo se hace en tu PC: nada sale del ordenador.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from .aduana import Aduana, ErrorLectura, leer
from .aduana.lectores import EXTENSIONES_TEXTO
from .escudo import Escudo, ResultadoEscudo

EXTENSIONES = EXTENSIONES_TEXTO | {".docx", ".docm", ".pdf"}
CARPETAS_IGNORADAS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
MAX_ARCHIVOS = 2000

# Veredictos, del peor al mejor
TRAMPA, DATOS, ILEGIBLE, LIMPIO = "TRAMPA", "DATOS PERSONALES", "NO SE PUEDE LEER", "LIMPIO"
ORDEN = {TRAMPA: 0, DATOS: 1, ILEGIBLE: 2, LIMPIO: 3}


@dataclass
class ResultadoArchivo:
    ruta: str
    formato: str = ""
    datos: dict[str, int] = field(default_factory=dict)  # tipo -> cuántos (nunca los datos en sí)
    riesgo: str = "NINGUNO"  # nivel de la aduana
    puntuacion: int = 0
    ocultos: int = 0  # trozos de texto escondido (letra blanca, invisible...)
    error: Optional[str] = None

    @property
    def veredicto(self) -> str:
        if self.error:
            return ILEGIBLE
        if self.riesgo in ("ALTO", "MEDIO") or self.ocultos:
            return TRAMPA
        if self.datos:
            return DATOS
        return LIMPIO

    def a_dict(self) -> dict:
        return {"ruta": self.ruta, "veredicto": self.veredicto, "formato": self.formato, "datos": self.datos,
                "riesgo": self.riesgo, "puntuacion": self.puntuacion, "ocultos": self.ocultos, "error": self.error}


@dataclass
class InformeEscaneo:
    carpeta: str
    archivos: list[ResultadoArchivo]
    saltados: int = 0  # archivos de tipos que no se leen (imágenes, ejecutables...)
    segundos: float = 0.0

    def cuenta(self) -> dict[str, int]:
        return {v: sum(1 for a in self.archivos if a.veredicto == v) for v in ORDEN}

    def datos_totales(self) -> dict[str, int]:
        total: dict[str, int] = {}
        for a in self.archivos:
            for tipo, n in a.datos.items():
                total[tipo] = total.get(tipo, 0) + n
        return dict(sorted(total.items(), key=lambda t: -t[1]))

    def a_dict(self) -> dict:
        return {"carpeta": self.carpeta, "cuenta": self.cuenta(), "datos": self.datos_totales(),
                "saltados": self.saltados, "segundos": round(self.segundos, 2),
                "archivos": [a.a_dict() for a in self.archivos]}

    def a_markdown(self) -> str:
        cuenta = self.cuenta()
        lineas = ["# Revisión de la carpeta antes de dársela a una IA", "",
                  f"Carpeta: `{self.carpeta}` · {len(self.archivos)} documentos revisados"
                  f" ({self.saltados} archivos de otros tipos sin revisar) · {self.segundos:.1f} s", "",
                  "| Veredicto | Documentos |", "| --- | --- |"]
        lineas += [f"| {v} | {n} |" for v, n in cuenta.items()]
        if self.datos_totales():
            lineas += ["", "Datos personales encontrados: " +
                       ", ".join(f"{n} {t}" for t, n in self.datos_totales().items()) + "."]
        lineas += ["", "| Documento | Veredicto | Datos personales | Riesgo de la aduana | Texto escondido |",
                   "| --- | --- | --- | --- | --- |"]
        for a in self.archivos:
            datos = ", ".join(f"{n} {t}" for t, n in a.datos.items()) or "–"
            riesgo = a.error or f"{a.riesgo} ({a.puntuacion})"
            lineas.append(f"| `{a.ruta}` | {a.veredicto} | {datos} | {riesgo} | {a.ocultos or '–'} |")
        lineas += ["", "Qué hacer: no subas los documentos con TRAMPA; los que tienen DATOS PERSONALES, "
                   "compártelos anonimizados (`python -m guardian anonimizar ARCHIVO`)."]
        return "\n".join(lineas) + "\n"


def _archivos(carpeta: Path):
    """Recorre la carpeta (y subcarpetas) sin entrar en carpetas de programas ni ocultas."""
    for ruta in sorted(carpeta.rglob("*")):
        if any(parte in CARPETAS_IGNORADAS or (parte.startswith(".") and parte not in (".", ".."))
               for parte in ruta.relative_to(carpeta).parts[:-1]):
            continue
        if ruta.is_file():
            yield ruta


def revisar_archivo(origen: Union[Path, bytes], escudo: Escudo, aduana: Aduana,
                    nombre: Optional[str] = None) -> ResultadoArchivo:
    """`origen` es una ruta o los bytes de un archivo subido a la web (entonces `nombre` dice su tipo)."""
    resultado = ResultadoArchivo(nombre or str(origen))
    try:
        lectura = leer(origen, nombre)
    except (OSError, ErrorLectura) as e:
        resultado.error = str(e)
        return resultado
    resultado.formato = lectura.formato
    resultado.ocultos = len(lectura.trucos)
    informe = aduana.analizar(lectura)
    resultado.riesgo, resultado.puntuacion = informe.nivel, informe.puntuacion
    hallazgos, _ = escudo.detectar(lectura.texto)  # TODO el texto: también lo escondido puede llevar datos
    for h in hallazgos:
        resultado.datos[h.tipo] = resultado.datos.get(h.tipo, 0) + 1
    return resultado


def escanear(carpeta: str, escudo: Optional[Escudo] = None, aduana: Optional[Aduana] = None) -> InformeEscaneo:
    inicio = time.perf_counter()
    raiz = Path(carpeta)
    if not raiz.is_dir():
        raise NotADirectoryError(f"{carpeta} no es una carpeta")
    escudo, aduana = escudo or Escudo(), aduana or Aduana()
    resultados, saltados = [], 0
    for ruta in _archivos(raiz):
        if ruta.suffix.lower() not in EXTENSIONES:
            saltados += 1
            continue
        if len(resultados) >= MAX_ARCHIVOS:
            saltados += 1
            continue
        resultados.append(revisar_archivo(ruta, escudo, aduana, str(ruta.relative_to(raiz))))
    resultados.sort(key=lambda a: (ORDEN[a.veredicto], a.ruta))
    return InformeEscaneo(str(raiz), resultados, saltados, time.perf_counter() - inicio)


def anonimizar(origen: Union[str, bytes], escudo: Optional[Escudo] = None,
               nombre: Optional[str] = None) -> tuple[str, ResultadoEscudo, int]:
    """Devuelve (texto anonimizado, resultado del escudo, trozos escondidos quitados).

    Se usa solo lo que se VE del documento (sin letra blanca, invisibles ni comentarios HTML)
    y se tapan los datos con marcadores. La tabla para deshacerlo no se guarda: la copia es para compartir.
    """
    lectura = leer(origen, nombre)
    visible = Aduana.desinfectar(lectura)
    resultado = (escudo or Escudo()).proteger(visible)
    return resultado.protegido, resultado, len(lectura.trucos)
