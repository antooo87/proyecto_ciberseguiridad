"""Mide lo bien que funciona el Guardián con los textos de prueba etiquetados.

Métricas (las mismas que se usan en cualquier artículo de detección):
  - PRECISIÓN: de lo que el Guardián tapó, ¿cuánto era de verdad un dato sensible?
               (baja = tapa cosas que no debía: falsos positivos)
  - RECALL (exhaustividad): de los datos sensibles que había, ¿cuántos encontró?
               (bajo = se le escapan datos: falsos negativos)
  - F1: la media "justa" entre las dos.
  - TASA DE FUGA: % de datos sensibles que llegarían a la IA total o parcialmente
               sin tapar. Es la métrica que de verdad importa en seguridad.

Para la aduana:
  - DETECCIÓN: % de documentos con ataque que generan alerta (riesgo MEDIO o ALTO).
  - FALSAS ALARMAS: % de documentos normales que generan alerta.
"""

import json
import os
import time
from collections import defaultdict

from .aduana import Aduana
from .escudo import Escudo

CARPETA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evaluacion")


def _cargar(nombre):
    ruta = os.path.join(CARPETA, nombre)
    if not os.path.exists(ruta):
        raise SystemExit(f"No encuentro {ruta}. Genera los datos con: python evaluacion/generar_datos.py")
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def _spans_reales(texto, entidades):
    """Busca dónde está cada dato etiquetado dentro del texto."""
    usados, spans = set(), []
    for e in entidades:
        desde = 0
        while True:
            i = texto.find(e["valor"], desde)
            if i < 0:
                break
            if i not in usados:
                usados.add(i)
                spans.append((e["tipo"], i, i + len(e["valor"])))
                break
            desde = i + 1
    return spans


def _iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return inter / union if union else 0


def _cubierto(inicio, fin, predichos):
    """¿Está todo el dato tapado por algún hallazgo (sea del tipo que sea)?"""
    tapado = [False] * (fin - inicio)
    for p in predichos:
        for i in range(max(inicio, p.inicio), min(fin, p.fin)):
            tapado[i - inicio] = True
    return all(tapado)


def evaluar_escudo(escudo: Escudo, ejemplos):
    c = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "total": 0, "fuga": 0})
    errores = []
    tiempos = []
    for ej in ejemplos:
        inicio = time.perf_counter()
        predichos, _ = escudo.detectar(ej["texto"])
        tiempos.append(time.perf_counter() - inicio)
        reales = _spans_reales(ej["texto"], ej["entidades"])
        emparejados = set()
        for tipo, r0, r1 in reales:
            c[tipo]["total"] += 1
            if not _cubierto(r0, r1, predichos):
                c[tipo]["fuga"] += 1
            match = next((j for j, p in enumerate(predichos)
                          if j not in emparejados and p.tipo == tipo and _iou(r0, r1, p.inicio, p.fin) >= 0.5), None)
            if match is None:
                c[tipo]["fn"] += 1
                errores.append({"id": ej["id"], "error": "no detectado", "tipo": tipo, "valor": ej["texto"][r0:r1]})
            else:
                emparejados.add(match)
                c[tipo]["tp"] += 1
        for j, p in enumerate(predichos):
            if j not in emparejados:
                c[p.tipo]["fp"] += 1
                errores.append({"id": ej["id"], "error": "tapado de más", "tipo": p.tipo, "valor": p.valor})

    filas = {}
    for tipo, v in sorted(c.items()):
        precision = v["tp"] / (v["tp"] + v["fp"]) if v["tp"] + v["fp"] else None
        recall = v["tp"] / (v["tp"] + v["fn"]) if v["tp"] + v["fn"] else None
        f1 = 2 * precision * recall / (precision + recall) if precision and recall else 0.0
        filas[tipo] = {**v, "precision": precision, "recall": recall, "f1": f1,
                       "tasa_fuga": v["fuga"] / v["total"] if v["total"] else None}
    total = {k: sum(v[k] for v in c.values()) for k in ("tp", "fp", "fn", "total", "fuga")}
    total["precision"] = total["tp"] / (total["tp"] + total["fp"]) if total["tp"] + total["fp"] else None
    total["recall"] = total["tp"] / (total["tp"] + total["fn"]) if total["tp"] + total["fn"] else None
    total["tasa_fuga"] = total["fuga"] / total["total"] if total["total"] else None
    return {"por_tipo": filas, "global": total, "textos": len(ejemplos),
            "ms_por_texto": round(1000 * sum(tiempos) / len(tiempos), 2), "errores": errores}


def evaluar_aduana(aduana: Aduana, docs):
    tp = fp = fn = tn = bloqueados_buenos = bloqueados_malos = 0
    fallos = []
    for d in docs:
        informe = aduana.analizar(d["texto"])
        alerta = informe.nivel in ("MEDIO", "ALTO")
        if d["malicioso"]:
            tp, fn = tp + alerta, fn + (not alerta)
            bloqueados_malos += informe.nivel == "ALTO"
        else:
            fp, tn = fp + alerta, tn + (not alerta)
            bloqueados_buenos += informe.nivel == "ALTO"
        if alerta != d["malicioso"]:
            fallos.append({"id": d["id"], "malicioso": d["malicioso"], "nivel": informe.nivel,
                           "texto": d["texto"][:90]})
    maliciosos, limpios = tp + fn, fp + tn
    return {"documentos": len(docs), "maliciosos": maliciosos, "limpios": limpios,
            "deteccion": tp / maliciosos if maliciosos else None,
            "falsas_alarmas": fp / limpios if limpios else None,
            "bloqueo_ataques": bloqueados_malos / maliciosos if maliciosos else None,
            "bloqueo_limpios": bloqueados_buenos / limpios if limpios else None,
            "fallos": fallos}


def _pct(x):
    return "  -  " if x is None else f"{100 * x:5.1f}%"


def _tabla_markdown(titulo, res_escudo, res_aduana):
    lineas = [f"## {titulo}", "",
              f"Escudo: {res_escudo['textos']} textos, {res_escudo['global']['total']} datos sensibles, "
              f"{res_escudo['ms_por_texto']} ms por texto.", "",
              "| Tipo | Datos | Precisión | Recall | F1 | Fuga |", "| --- | --- | --- | --- | --- | --- |"]
    for tipo, v in res_escudo["por_tipo"].items():
        lineas.append(f"| {tipo} | {v['total']} | {_pct(v['precision'])} | {_pct(v['recall'])} | "
                      f"{_pct(v['f1'])} | {_pct(v['tasa_fuga'])} |")
    g = res_escudo["global"]
    lineas.append(f"| **TOTAL** | **{g['total']}** | **{_pct(g['precision'])}** | **{_pct(g['recall'])}** | | "
                  f"**{_pct(g['tasa_fuga'])}** |")
    lineas += ["", f"Aduana: {res_aduana['documentos']} documentos ({res_aduana['maliciosos']} con ataque, "
               f"{res_aduana['limpios']} normales).", "",
               "| Métrica | Valor |", "| --- | --- |",
               f"| Ataques detectados (riesgo MEDIO o ALTO) | {_pct(res_aduana['deteccion'])} |",
               f"| Falsas alarmas en documentos normales | {_pct(res_aduana['falsas_alarmas'])} |",
               f"| Ataques bloqueados (riesgo ALTO) | {_pct(res_aduana['bloqueo_ataques'])} |",
               f"| Documentos normales bloqueados | {_pct(res_aduana['bloqueo_limpios'])} |", ""]
    return "\n".join(lineas) + "\n"


CONJUNTOS = [
    ("datos", "Conjunto de desarrollo (generado, usado para ajustar las reglas)", "datos_escudo.jsonl",
     "datos_aduana.jsonl"),
    ("ciega", "Prueba ciega (escrita a mano, NO usada para ajustar)", "ciega_escudo.jsonl", "ciega_aduana.jsonl"),
]


class _ConProgreso:
    """Envuelve un detector o juez para ir enseñando por dónde va (con IA tarda)."""

    def __init__(self, pieza, metodo, total, etiqueta):
        self.pieza, self.metodo, self.total, self.etiqueta, self.n = pieza, metodo, total, etiqueta, 0

    def __getattr__(self, nombre):
        if nombre != self.metodo:
            return getattr(self.pieza, nombre)

        def envuelto(*a, **k):
            self.n += 1
            if self.n % 10 == 0 or self.n == self.total:
                print(f"   {self.etiqueta}: {self.n}/{self.total}", flush=True)
            return getattr(self.pieza, nombre)(*a, **k)
        return envuelto


def evaluar_juez(juez, docs):
    """El juez IA SOLO, sin reglas: ¿cuántos ataques ve y cuántas falsas alarmas da?"""
    tp = fp = fn = tn = errores = 0
    for d in docs:
        try:
            ataque = juez.juzgar(d["texto"])["es_ataque"]
        except Exception:
            errores += 1
            continue
        if d["malicioso"]:
            tp, fn = tp + ataque, fn + (not ataque)
        else:
            fp, tn = fp + ataque, tn + (not ataque)
    return {"deteccion": tp / (tp + fn) if tp + fn else None, "falsas_alarmas": fp / (fp + tn) if fp + tn else None,
            "errores": errores}


def evaluar_todo(con_ia=False, modelo=None, limite=None, conjunto="todos"):
    juez = None
    if con_ia:
        from . import config
        from .aduana.juez_ia import JuezIA
        from .escudo.detector_ia import DetectorIA
        from .ia import ClienteIA
        cliente = ClienteIA(modelo or config.MODELO_DETECTOR)
        estado = cliente.estado()
        if not estado["ok"]:
            print(estado["detalle"])
            return 1
        detector, juez = DetectorIA(cliente), JuezIA(cliente)
        modo = f"reglas + IA ({cliente.modelo})"
        print(f"Evaluando con IA ({cliente.modelo}): puede tardar...", flush=True)
    else:
        detector, modo = None, "solo reglas"

    md = [f"# Resultados de la evaluación: {modo}", ""]
    resultados = {"modo": modo, "modelo": cliente.modelo if con_ia else None}
    inicio_total = time.perf_counter()
    for clave, titulo, f_escudo, f_aduana in CONJUNTOS:
        if conjunto not in ("todos", clave):
            continue
        textos, docs = _cargar(f_escudo)[:limite], _cargar(f_aduana)[:limite]
        escudo = Escudo(detector_ia=_ConProgreso(detector, "detectar", len(textos), f"{clave} escudo")) \
            if detector else Escudo()
        aduana = Aduana(juez=_ConProgreso(juez, "juzgar", len(docs), f"{clave} aduana")) if juez else Aduana()
        res_escudo = evaluar_escudo(escudo, textos)
        res_aduana = evaluar_aduana(aduana, docs)
        md.append(_tabla_markdown(titulo, res_escudo, res_aduana))
        resultados[clave] = {"escudo": res_escudo, "aduana": res_aduana}
        if juez:
            res_juez = evaluar_juez(_ConProgreso(juez, "juzgar", len(docs), f"{clave} juez solo"), docs)
            resultados[clave]["juez_solo"] = res_juez
            md.append(f"Juez IA solo, sin reglas: detecta {_pct(res_juez['deteccion'])} de los ataques con "
                      f"{_pct(res_juez['falsas_alarmas'])} de falsas alarmas.\n")
    resultados["segundos"] = round(time.perf_counter() - inicio_total, 1)
    md.append(f"Tiempo total: {resultados['segundos']} s.\n")
    texto = "\n".join(md)
    print(texto)

    sufijo = "reglas" if not con_ia else "ia_" + cliente.modelo.replace(":", "_").replace("/", "_")
    if conjunto != "todos":
        sufijo += f"_{conjunto}"
    with open(os.path.join(CARPETA, f"resultados_{sufijo}.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    with open(os.path.join(CARPETA, f"resultados_{sufijo}.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"Guardado en evaluacion/resultados_{sufijo}.md y .json (con la lista de fallos para analizarlos)")
    return 0
