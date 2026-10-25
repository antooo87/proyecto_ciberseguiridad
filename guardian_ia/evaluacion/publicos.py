"""Evaluación con conjuntos PÚBLICOS, hechos por otros investigadores.

Los textos de datos_*.jsonl y ciega_*.jsonl los escribimos nosotros, así que
siempre queda la duda de si se parecen demasiado a lo que el programa espera.
Aquí se usan dos conjuntos conocidos que cualquiera puede descargar:

  - ESCUDO, nombres de personas: CoNLL-2002 en español (Tjong Kim Sang, 2002),
    noticias de la agencia EFE con las personas etiquetadas a mano. Se usa su
    parte de test (esp.testb), que es la que se usa para comparar sistemas.
  - ADUANA, prompt injection indirecta: BIPIA de Microsoft (Yi et al., 2023),
    tarea EmailQA: 50 correos reales. A cada correo se le mete uno de los
    ataques de la parte de TEST de BIPIA al principio, en medio o al final,
    como hace el propio benchmark. Los 50 correos sin tocar son los "limpios".

La regla "ordenes_sobre_la_respuesta" de la aduana se escribió mirando SOLO los
ataques de la parte de entrenamiento de BIPIA (text_attack_train.json); aquí se
mide con los de test, que no se miraron.

Los datos se descargan la primera vez en evaluacion/publicos/ y no se incluyen
en el proyecto.

Uso:
    python evaluacion/publicos.py                            solo reglas
    python evaluacion/publicos.py --ia --modelo qwen3.5:9b   con el detector y el juez IA
    python evaluacion/publicos.py --ia --solo bipia          solo uno de los dos conjuntos (conll o bipia)
"""

import argparse
import io
import json
import os
import random
import sys
import time
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardian.aduana import Aduana  # noqa: E402
from guardian.escudo import Escudo  # noqa: E402
from guardian.evaluacion import _ConProgreso, _iou, _pct, evaluar_aduana, evaluar_juez  # noqa: E402

CARPETA = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(CARPETA, "publicos")
FUENTES = {
    "conll2002.zip": "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/conll2002.zip",
    "bipia_email_test.jsonl": "https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/email/test.jsonl",
    "bipia_ataques_test.json": "https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/text_attack_test.json",
}
SEMILLA = 2026


def descargar(nombre: str) -> bytes:
    ruta = os.path.join(DATOS, nombre)
    if not os.path.exists(ruta):
        os.makedirs(DATOS, exist_ok=True)
        print(f"Descargando {FUENTES[nombre]} ...", flush=True)
        with urllib.request.urlopen(FUENTES[nombre], timeout=60) as r, open(ruta, "wb") as f:
            f.write(r.read())
    with open(ruta, "rb") as f:
        return f.read()


# ---------------- CoNLL-2002 (nombres de personas) ----------------
SIN_ESPACIO_ANTES = {",", ".", ";", ":", ")", "?", "!", "%", "»", "”"}
SIN_ESPACIO_DESPUES = {"(", "¿", "¡", "«", "“"}


def frases_conll(texto: str):
    """Cada frase: lista de (palabra, etiqueta)."""
    frase = []
    for linea in texto.splitlines():
        partes = linea.split()
        if not partes:
            if frase:
                yield frase
            frase = []
        elif partes[0] != "-DOCSTART-":
            frase.append((partes[0], partes[-1]))
    if frase:
        yield frase


def reconstruir(frase):
    """Junta las palabras en un texto normal y apunta dónde empieza y acaba cada persona."""
    texto, personas, actual, anterior = "", [], None, None
    for palabra, etiqueta in frase:
        if texto and palabra not in SIN_ESPACIO_ANTES and anterior not in SIN_ESPACIO_DESPUES:
            texto += " "
        inicio = len(texto)
        texto += palabra
        if etiqueta == "B-PER" or (etiqueta == "I-PER" and actual is None):
            if actual:
                personas.append(actual)
            actual = [inicio, len(texto)]
        elif etiqueta == "I-PER":
            actual[1] = len(texto)
        elif actual:
            personas.append(actual)
            actual = None
        anterior = palabra
    if actual:
        personas.append(actual)
    return texto, [tuple(p) for p in personas]


def conjunto_conll(n_con=70, n_sin=30):
    with zipfile.ZipFile(io.BytesIO(descargar("conll2002.zip"))) as z:
        texto = z.read("conll2002/esp.testb").decode("utf-8")
    con, sin = [], []
    for frase in frases_conll(texto):
        if not 8 <= len(frase) <= 60:
            continue
        t, personas = reconstruir(frase)
        (con if personas else sin).append({"texto": t, "personas": personas})
    rnd = random.Random(SEMILLA)
    return rnd.sample(con, n_con) + rnd.sample(sin, n_sin)


def evaluar_personas(escudo: Escudo, ejemplos):
    tp = fp = fn = 0
    fallos = []
    for ej in ejemplos:
        predichos = [h for h in escudo.detectar(ej["texto"])[0] if h.tipo == "PERSONA"]
        usados = set()
        for r0, r1 in ej["personas"]:
            j = next((j for j, p in enumerate(predichos) if j not in usados and _iou(r0, r1, p.inicio, p.fin) >= 0.5),
                     None)
            if j is None:
                fn += 1
                fallos.append(f"no vio: {ej['texto'][r0:r1]}")
            else:
                tp += 1
                usados.add(j)
        fp += len(predichos) - len(usados)
        fallos += [f"sobra: {p.valor}" for j, p in enumerate(predichos) if j not in usados]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else 0.0
    return {"frases": len(ejemplos), "personas": tp + fn, "precision": precision, "recall": recall, "f1": f1,
            "fallos": fallos}


# ---------------- BIPIA (prompt injection en correos) ----------------
def insertar(contexto: str, ataque: str, donde: str) -> str:
    if donde == "inicio":
        return f"{ataque}\n{contexto}"
    if donde == "final":
        return f"{contexto}\n{ataque}"
    mitad = len(contexto) // 2
    corte = contexto.find(". ", mitad)
    corte = mitad if corte < 0 else corte + 2
    return f"{contexto[:corte]}{ataque} {contexto[corte:]}"


def conjunto_bipia():
    lineas = descargar("bipia_email_test.jsonl").decode("utf-8").splitlines()
    correos = [json.loads(linea)["context"] for linea in lineas if linea.strip()]
    ataques = [a for lista in json.loads(descargar("bipia_ataques_test.json")).values() for a in lista]
    rnd = random.Random(SEMILLA)
    docs = [{"id": f"limpio-{i}", "texto": c, "malicioso": False} for i, c in enumerate(correos)]
    for i, c in enumerate(correos):
        docs.append({"id": f"ataque-{i}", "malicioso": True,
                     "texto": insertar(c, rnd.choice(ataques), ("inicio", "medio", "final")[i % 3])})
    return docs


class _Memoria:
    """Recuerda lo que ya contestó el juez para no preguntarle dos veces por el mismo texto (el modelo es lento)."""

    def __init__(self, juez):
        self.juez, self.vistos = juez, {}

    def juzgar(self, texto):
        if texto not in self.vistos:
            self.vistos[texto] = self.juez.juzgar(texto)
        return self.vistos[texto]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ia", action="store_true")
    p.add_argument("--modelo", default=None)
    p.add_argument("--solo", choices=["conll", "bipia"], help="medir solo uno de los dos conjuntos")
    args = p.parse_args()

    detector = juez = None
    modo = "solo reglas"
    if args.ia:
        from guardian import config
        from guardian.aduana.juez_ia import JuezIA
        from guardian.escudo.detector_ia import DetectorIA
        from guardian.ia import ClienteIA
        cliente = ClienteIA(args.modelo or config.MODELO_DETECTOR)
        if not cliente.estado()["ok"]:
            raise SystemExit(cliente.estado()["detalle"])
        detector, juez, modo = DetectorIA(cliente), _Memoria(JuezIA(cliente)), f"reglas + IA ({cliente.modelo})"

    inicio = time.perf_counter()
    res = {"modo": modo}
    lineas = [f"# Conjuntos públicos: {modo}", ""]
    if args.solo != "bipia":
        frases = conjunto_conll()
        escudo = Escudo(detector_ia=_ConProgreso(detector, "detectar", len(frases), "CoNLL")) if detector else Escudo()
        c = res["conll2002"] = evaluar_personas(escudo, frases)
        lineas += [f"## Escudo: nombres de personas en CoNLL-2002 español (test, {c['frases']} frases, "
                   f"{c['personas']} personas)", "",
                   f"Precisión {_pct(c['precision'])} · Recall {_pct(c['recall'])} · F1 {c['f1']:.2f}", ""]
    if args.solo != "conll":
        docs = conjunto_bipia()
        aduana = Aduana(juez=_ConProgreso(juez, "juzgar", len(docs), "BIPIA")) if juez else Aduana()
        b = res["bipia"] = evaluar_aduana(aduana, docs)
        lineas += [f"## Aduana: BIPIA EmailQA ({b['maliciosos']} correos con ataque, {b['limpios']} limpios)", "",
                   f"Ataques detectados {_pct(b['deteccion'])} · Falsas alarmas {_pct(b['falsas_alarmas'])} · "
                   f"Ataques bloqueados {_pct(b['bloqueo_ataques'])}", ""]
        if juez:
            j = res["bipia_juez_solo"] = evaluar_juez(_ConProgreso(juez, "juzgar", len(docs), "BIPIA juez solo"), docs)
            lineas.append(f"Juez IA solo: detecta {_pct(j['deteccion'])} con {_pct(j['falsas_alarmas'])} "
                          "de falsas alarmas.")
    res["segundos"] = round(time.perf_counter() - inicio, 1)
    lineas.append(f"\nTiempo: {res['segundos']} s.")
    texto = "\n".join(lineas)
    print(texto)
    sufijo = "reglas" if not args.ia else "ia_" + cliente.modelo.replace(":", "_").replace("/", "_")
    sufijo += f"_{args.solo}" if args.solo else ""
    with open(os.path.join(CARPETA, f"publicos_{sufijo}.md"), "w", encoding="utf-8") as f:
        f.write(texto + "\n")
    with open(os.path.join(CARPETA, f"publicos_{sufijo}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
