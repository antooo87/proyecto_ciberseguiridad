"""Panel de actividad: qué ha hecho el Guardián estos días, leído del registro.

    python -m guardian informe              los últimos 30 días
    python -m guardian informe --dias 7     la última semana (--dias 0: todo)

El registro (registro/guardian_AAAA-MM-DD.jsonl, una línea JSON por suceso) nunca guarda tus datos: solo cuántos
se taparon y de qué tipo, el riesgo de los documentos, qué avisos tuvo la respuesta y qué acciones se bloquearon.
Este módulo lo resume para la terminal, la web y la extensión del navegador: es la prueba de que el Guardián
trabaja ("esta semana ha tapado 87 datos antes de que llegaran a la IA") sin ser otra fuga de datos.
"""

import glob
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from . import config
from .terminal import resumen

DONDE = {"pregunta": "Chat", "documento_bloqueado": "Chat", "extension_proteger": "Extensión",
         "extension_restaurar": "Extensión", "extension_mejorar": "Extensión", "proxy": "Agentes"}
NIVELES_RESPUESTA = ("OK", "AVISO", "PELIGRO")
MAX_ULTIMOS = 25

# Tipo de aviso del verificador -> qué es, en pocas palabras
AVISOS = {
    "descarga_y_ejecuta": "comando que descarga un programa y lo ejecuta",
    "comando_ofuscado": "comando escondido (codificado)",
    "borra_todo": "comando que lo borra todo",
    "desactiva_seguridad": "comando que desactiva el antivirus",
    "roba_credenciales": "comando que roba contraseñas",
    "persistencia": "comando que se queda instalado al arrancar",
    "superusuario": "comando con permisos de administrador",
    "exfiltracion": "tus datos metidos en un enlace (robo de datos)",
    "imagen_con_datos": "imagen de otra web con datos en la dirección",
    "texto_invisible": "mensaje con letras invisibles",
    "pide_secretos": "la IA te pide un dato secreto",
    "dato_sensible_nuevo": "dato personal que tú no le diste",
    "marcador_inventado": "marcador que no corresponde a ningún dato",
    "imita_marca": "enlace que imita a una marca (phishing)",
    "dominio_disfrazado": "web disfrazada con letras de otros alfabetos",
    "dominio_malicioso": "web maliciosa conocida",
    "dominio_inexistente": "enlace a una web que no existe",
    "pagina_inexistente": "enlace a una página que no existe",
    "doi_inexistente": "artículo citado que no existe",
    "enlace_no_responde": "enlace que no se ha podido abrir",
    "enlace_a_ip": "enlace a una dirección IP",
    "acortador": "enlace acortado",
    "fuga_de_instrucciones": "la IA ha contado sus instrucciones internas",
    "eco_de_la_trampa": "la IA repite lo que pedía una trampa",
    "contradice_documento": "frase que contradice el documento",
    "sin_respaldo": "frase que el documento no dice",
}
# Solo informativos: no se cuentan como avisos
INFORMATIVOS = {"sin_respaldo", "marcador_inventado", "enlace_no_responde"}


@dataclass
class Actividad:
    carpeta: str
    dias: Optional[int]
    desde: Optional[date] = None
    hasta: Optional[date] = None
    sucesos: int = 0
    lineas_rotas: int = 0
    donde: Counter = field(default_factory=Counter)  # Chat / Extensión / Agentes -> sucesos
    datos: Counter = field(default_factory=Counter)  # tipo de dato -> cuántos se taparon
    mensajes_con_datos: int = 0
    documentos: Counter = field(default_factory=Counter)  # riesgo MEDIO/ALTO de lo pegado o adjuntado
    documentos_bloqueados: int = 0
    respuestas: Counter = field(default_factory=Counter)  # OK / AVISO / PELIGRO
    avisos: Counter = field(default_factory=Counter)  # tipo de aviso -> cuántas veces
    acciones_bloqueadas: Counter = field(default_factory=Counter)  # herramienta del agente -> cuántas veces
    resultados_bloqueados: int = 0
    preguntas_mejoradas: int = 0
    notas: list = field(default_factory=list)  # nota (0-100) de cada pregunta antes de mejorarla
    por_dia: dict = field(default_factory=dict)  # "2026-11-23" -> {"datos": n, "alertas": n}
    ultimos: list = field(default_factory=list)  # lo último importante, lo más reciente primero

    @property
    def datos_tapados(self) -> int:
        return sum(self.datos.values())

    @property
    def documentos_con_trampa(self) -> int:
        return self.documentos["ALTO"] + self.documentos["MEDIO"] + self.documentos_bloqueados

    @property
    def alertas(self) -> int:
        """Veces que el Guardián te ha avisado o ha parado algo (sin contar los datos tapados)."""
        return (self.documentos_con_trampa + self.respuestas["AVISO"] + self.respuestas["PELIGRO"]
                + sum(self.acciones_bloqueadas.values()) + self.resultados_bloqueados)

    def a_dict(self) -> dict:
        return {
            "carpeta": self.carpeta, "dias": self.dias,
            "desde": self.desde.isoformat() if self.desde else None,
            "hasta": self.hasta.isoformat() if self.hasta else None,
            "sucesos": self.sucesos, "lineas_rotas": self.lineas_rotas, "donde": dict(self.donde),
            "datos_tapados": self.datos_tapados, "datos": dict(self.datos.most_common()),
            "mensajes_con_datos": self.mensajes_con_datos,
            "documentos_con_trampa": self.documentos_con_trampa, "documentos_bloqueados": self.documentos_bloqueados,
            "documentos": dict(self.documentos),
            "respuestas": {n: self.respuestas[n] for n in NIVELES_RESPUESTA},
            "avisos": [{"tipo": t, "que": AVISOS.get(t, t), "veces": n} for t, n in self.avisos.most_common()],
            "acciones_bloqueadas": dict(self.acciones_bloqueadas.most_common()),
            "resultados_bloqueados": self.resultados_bloqueados, "alertas": self.alertas,
            "preguntas_mejoradas": self.preguntas_mejoradas,
            "nota_media": round(sum(self.notas) / len(self.notas)) if self.notas else None,
            "por_dia": self.por_dia, "ultimos": self.ultimos,
        }


def _numero(valor) -> int:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and valor > 0 else 0


def _cuenta(valor) -> Counter:
    """{"DNI": 2, ...} del registro, sin fiarse de lo que haya (un archivo editado a mano no debe romper nada)."""
    if not isinstance(valor, dict):
        return Counter()
    return Counter({str(k): _numero(v) for k, v in valor.items() if _numero(v)})


def _que_paso(suceso: dict, datos: Counter, avisos: Counter) -> list[str]:
    """Lo importante del suceso, en frases cortas. Vacío si no hubo nada que contar."""
    evento = suceso.get("evento")
    partes = []
    if evento == "documento_bloqueado":
        partes.append(f"documento bloqueado: órdenes ocultas para la IA (puntuación {suceso.get('puntuacion', '?')})")
    if datos:
        partes.append(f"tapados {resumen(dict(datos))}")
    riesgo = suceso.get("riesgo_documento")
    if riesgo in ("MEDIO", "ALTO"):
        partes.append(f"{'texto pegado' if evento == 'extension_proteger' else 'documento'} con riesgo {riesgo}: "
                      "desinfectado antes de dárselo a la IA")
    acciones = [a for a in suceso.get("acciones_bloqueadas") or [] if isinstance(a, str)]
    if acciones:
        partes.append("acción bloqueada: " + ", ".join(sorted(set(acciones))))
    if _numero(suceso.get("resultados_bloqueados")):
        partes.append(f"{suceso['resultados_bloqueados']} resultado(s) de herramienta con trampa bloqueado(s)")
    nivel = suceso.get("verificacion")
    if nivel in ("AVISO", "PELIGRO"):
        detalles = [AVISOS.get(t, t) for t in avisos if t not in INFORMATIVOS]
        partes.append(f"respuesta con {nivel}" + (f": {'; '.join(detalles)}" if detalles else ""))
    return partes


def leer_registro(carpeta: Optional[str] = None, dias: Optional[int] = 30, hoy: Optional[date] = None) -> Actividad:
    """Resume el registro. dias=None o 0: todo lo que haya."""
    carpeta = carpeta or config.CARPETA_REGISTRO
    hoy = hoy or date.today()
    dias = dias or None
    desde_filtro = hoy - timedelta(days=dias - 1) if dias else None
    actividad = Actividad(carpeta=carpeta, dias=dias)
    sucesos = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "guardian_*.jsonl"))):
        try:
            if desde_filtro and date.fromisoformat(os.path.basename(ruta)[9:19]) < desde_filtro:
                continue  # el nombre lleva el día: no hace falta leerlo
        except ValueError:
            pass
        try:
            with open(ruta, encoding="utf-8", errors="replace") as f:
                lineas = f.readlines()
        except OSError:
            continue
        for linea in lineas:
            if not linea.strip():
                continue
            try:
                suceso = json.loads(linea)
                fecha = datetime.fromisoformat(suceso["fecha"])
            except (ValueError, KeyError, TypeError):
                actividad.lineas_rotas += 1
                continue
            if suceso.get("evento") not in DONDE:  # sucesos de otras versiones: se ignoran
                continue
            if desde_filtro and fecha.date() < desde_filtro or fecha.date() > hoy:
                continue
            sucesos.append((fecha, suceso))

    sucesos.sort(key=lambda par: par[0])
    for fecha, suceso in sucesos:
        evento = suceso["evento"]
        datos, avisos = _cuenta(suceso.get("datos_tapados")), _cuenta(suceso.get("avisos_respuesta"))
        actividad.sucesos += 1
        actividad.donde[DONDE[evento]] += 1
        actividad.desde = actividad.desde or fecha.date()
        actividad.hasta = fecha.date()
        actividad.datos += datos
        actividad.mensajes_con_datos += bool(datos)
        if evento == "documento_bloqueado":
            actividad.documentos_bloqueados += 1
        elif suceso.get("riesgo_documento") in ("MEDIO", "ALTO"):
            actividad.documentos[suceso["riesgo_documento"]] += 1
        if suceso.get("verificacion") in NIVELES_RESPUESTA:
            actividad.respuestas[suceso["verificacion"]] += 1
            actividad.avisos += Counter({t: n for t, n in avisos.items() if t not in INFORMATIVOS})
        for accion in suceso.get("acciones_bloqueadas") or []:
            if isinstance(accion, str):
                actividad.acciones_bloqueadas[accion] += 1
        actividad.resultados_bloqueados += _numero(suceso.get("resultados_bloqueados"))
        if evento == "extension_mejorar":
            actividad.preguntas_mejoradas += 1
            nota = suceso.get("nota")
            if isinstance(nota, int) and not isinstance(nota, bool) and 0 <= nota <= 100:
                actividad.notas.append(nota)

        partes = _que_paso(suceso, datos, avisos)
        dia = actividad.por_dia.setdefault(fecha.date().isoformat(), {"datos": 0, "alertas": 0})
        dia["datos"] += sum(datos.values())
        dia["alertas"] += sum(1 for p in partes if not p.startswith("tapados"))
        if partes:
            actividad.ultimos.append({"fecha": fecha.isoformat(timespec="minutes"), "donde": DONDE[evento],
                                      "que": " · ".join(partes)[:300],
                                      "grave": suceso.get("verificacion") == "PELIGRO"
                                      or evento == "documento_bloqueado" or bool(suceso.get("acciones_bloqueadas"))})
    actividad.ultimos = actividad.ultimos[::-1][:MAX_ULTIMOS]
    return actividad
