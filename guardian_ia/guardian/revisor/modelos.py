"""Revisa los archivos de modelos de IA que tienes descargados.

Un modelo no es solo "números": según el formato, abrirlo puede EJECUTAR CÓDIGO.
  - pickle (.pkl, .pt, .pth, .bin, .ckpt, .joblib): el formato clásico de Python.
    Al cargarlo con torch.load o pickle.load puede ejecutar cualquier orden,
    por ejemplo os.system("..."). Se han encontrado modelos así en Hugging Face.
  - Keras (.keras, .h5) con capas Lambda: llevan código Python dentro.
  - GGUF (lo que usan Ollama y LM Studio) y safetensors: no ejecutan código, pero
    un GGUF lleva dentro la PLANTILLA DE CHAT, el texto que envuelve cada mensaje.
    Pillar Security demostró en 2025 que se puede envenenar esa plantilla para
    que el modelo meta enlaces o código malicioso solo cuando ve ciertas palabras.

Cómo se revisa SIN abrir el modelo de verdad:
  - pickle: se leen las "instrucciones" del archivo con pickletools (que no ejecuta
    nada) y se apunta qué funciones importaría. os.system o subprocess = peligro.
  - GGUF: se lee solo la cabecera y se pasa la plantilla por la aduana.
  - Ollama: se revisan las plantillas y los mensajes de sistema de cada modelo.
"""

import io
import json
import os
import pickletools
import re
import struct
import zipfile
from pathlib import Path

from ..aduana import Aduana
from .comun import HallazgoRevisor, Ubicaciones

EXT_PICKLE = {".pkl", ".pickle", ".pt", ".pth", ".bin", ".ckpt", ".joblib", ".npy"}
EXT_SEGURAS = {".safetensors", ".onnx"}
CARPETAS_MODELOS = [".cache/huggingface", ".cache/torch", ".lmstudio/models", ".cache/lm-studio/models",
                    "Downloads", "Descargas", "Desktop", "Escritorio", "ComfyUI/models",
                    "stable-diffusion-webui/models"]
NO_ENTRAR = {"node_modules", ".git", ".venv", "venv", "site-packages", "__pycache__", "AppData", ".Trash"}
MAX_ENTRADAS = 50_000  # archivos y carpetas que se miran como mucho por carpeta
MAX_OPCODES = 5_000_000

PELIGROSOS = {
    "os": "*", "posix": "*", "nt": "*", "subprocess": "*", "pty": "*", "commands": "*", "runpy": "*",
    "socket": "*", "webbrowser": "*", "shutil": "*", "ctypes": "*", "importlib": "*", "requests": "*",
    "urllib": "*", "urllib.request": "*", "http.client": "*", "ftplib": "*", "smtplib": "*", "pip": "*",
    "code": "*", "sys": "*", "multiprocessing": "*", "pickle": "*", "_pickle": "*", "marshal": "*",
    "asyncio": "*", "torch.hub": "*", "dill": "*", "platform": "*", "signal": "*",
    "builtins": {"eval", "exec", "compile", "open", "__import__", "getattr", "setattr", "delattr", "breakpoint",
                 "input", "globals", "locals", "vars", "exit", "quit"},
    "__builtin__": {"eval", "exec", "compile", "open", "__import__", "getattr", "setattr", "execfile", "file"},
    "operator": {"attrgetter", "methodcaller"},
    "types": {"FunctionType", "CodeType"},
}
SEGUROS = ("torch.", "collections.OrderedDict", "collections.defaultdict", "numpy.", "_codecs.encode",
           "builtins.set", "builtins.frozenset", "builtins.slice", "builtins.complex", "builtins.bytearray",
           "builtins.range", "__builtin__.set", "__builtin__.frozenset", "copy_reg._reconstructor",
           "copyreg._reconstructor", "sklearn.", "scipy.", "pandas.", "transformers.", "tokenizers.",
           "datetime.", "decimal.Decimal", "fractions.Fraction", "argparse.Namespace", "joblib.numpy_pickle.",
           "builtins.object", "__builtin__.object", "pathlib.")
OPCODES_CADENA = {"SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "UNICODE", "STRING", "BINSTRING",
                  "SHORT_BINSTRING"}
REGLAS_NORMALES_EN_PLANTILLAS = {"etiquetas_de_rol", "llamada_herramientas"}
ETIQUETAS_NORMALES = re.compile(r"^[<\[]|^(reasoning_content|tool_calls?|content|image|video|audio)$")


# ----------------------------- pickle -----------------------------
def importaciones_pickle(flujo) -> list[tuple[str, str]]:
    """Qué funciones importaría el pickle al cargarse. Lee las instrucciones sin ejecutarlas."""
    importaciones, memo, cadenas = [], {}, []
    for n, (op, arg, _) in enumerate(pickletools.genops(flujo)):
        nombre = op.name
        if nombre in OPCODES_CADENA:
            cadenas.append(arg)
        elif nombre == "MEMOIZE":
            memo[len(memo)] = cadenas[-1] if cadenas else None
        elif nombre in ("PUT", "BINPUT", "LONG_BINPUT"):
            memo[arg] = cadenas[-1] if cadenas else None
        elif nombre in ("GET", "BINGET", "LONG_BINGET"):
            cadenas.append(memo.get(arg))
        elif nombre in ("GLOBAL", "INST"):
            modulo, _, funcion = str(arg).partition(" ")
            importaciones.append((modulo, funcion))
        elif nombre == "STACK_GLOBAL":
            if len(cadenas) >= 2 and all(isinstance(c, str) for c in cadenas[-2:]):
                importaciones.append((cadenas[-2], cadenas[-1]))
            else:
                importaciones.append(("?", "?"))  # no se puede saber qué importa: sospechoso
        elif nombre == "STOP":
            break
        if n > MAX_OPCODES:
            break
    return importaciones


def clasificar_importacion(modulo: str, funcion: str) -> str:
    """'peligrosa', 'segura' o 'rara'."""
    completo = f"{modulo}.{funcion}"
    for mod, funciones in PELIGROSOS.items():
        if (modulo == mod or modulo.startswith(mod + ".")) and (funciones == "*" or funcion in funciones):
            return "peligrosa"
    if modulo == "?":
        return "rara"
    return "segura" if completo.startswith(SEGUROS) else "rara"


def _flujos_pickle(ruta: Path):
    """Un .pt moderno es un ZIP con data.pkl dentro; uno antiguo es un pickle directo."""
    with open(ruta, "rb") as f:
        cabecera = f.read(12)
    if cabecera.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(ruta) as z:
            for miembro in z.namelist():
                if miembro.endswith(".pkl"):
                    with z.open(miembro) as m:
                        yield "zip", io.BytesIO(m.read())
    elif cabecera.startswith(b"\x93NUMPY"):
        version = cabecera[6]
        largo, inicio = (struct.unpack("<H", cabecera[8:10])[0], 10) if version == 1 else \
            (struct.unpack("<I", cabecera[8:12])[0], 12)
        with open(ruta, "rb") as f:
            f.seek(inicio)
            if "'descr': '|O'" in f.read(largo).decode("latin-1"):  # array de objetos: lleva un pickle detrás
                yield "npy", io.BytesIO(f.read())
    elif (cabecera[:1] == b"\x80" and 2 <= cabecera[1] <= 5) or cabecera[:1] in (b"(", b"c", b"]", b"}"):
        with open(ruta, "rb") as f:
            yield "pickle", io.BytesIO(f.read())


def revisar_pickle(ruta: Path) -> tuple[bool, HallazgoRevisor | None]:
    """Devuelve (¿era un pickle?, hallazgo o None)."""
    peligrosas, raras, era_pickle, formato = set(), set(), False, ""
    try:
        for tipo_flujo, flujo in _flujos_pickle(ruta):
            era_pickle, formato = True, tipo_flujo
            for modulo, funcion in importaciones_pickle(flujo):
                tipo = clasificar_importacion(modulo, funcion)
                if tipo == "peligrosa":
                    peligrosas.add(f"{modulo}.{funcion}")
                elif tipo == "rara":
                    raras.add(f"{modulo}.{funcion}")
    except (zipfile.BadZipFile, ValueError, EOFError, struct.error, OSError, IndexError) as e:
        if formato == "pickle" and ruta.suffix.lower() == ".bin":
            return False, None  # un .bin de pesos "en crudo" que por casualidad empieza como un pickle
        return True, HallazgoRevisor("modelos", "BAJA", f"No he podido analizar {ruta.name}",
                                     f"Parece un modelo en formato pickle pero está dañado o es raro ({e}).",
                                     "No lo abras si no sabes de dónde viene.", str(ruta))
    if peligrosas:
        return True, HallazgoRevisor(
            "modelos", "CRITICA", f"Modelo con código escondido: {ruta.name}",
            "Al abrirlo (torch.load, pickle.load o joblib.load) ejecutaría: " + ", ".join(sorted(peligrosas)) +
            ". Un modelo de verdad no necesita ejecutar órdenes en tu PC.",
            "No lo abras. Bórralo y, si lo necesitas, busca la versión .safetensors de una fuente oficial.", str(ruta))
    if raras:
        return True, HallazgoRevisor(
            "modelos", "MEDIA", f"Modelo que importa funciones poco habituales: {ruta.name}",
            "Al abrirlo cargaría: " + ", ".join(sorted(raras)[:8]) + ". No es seguro que sea malicioso, "
            "pero un modelo normal solo usa funciones de torch, numpy o similares.",
            "Ábrelo solo si confías en quien lo publica, o conviértelo a safetensors.", str(ruta))
    return era_pickle, None


# ----------------------------- Keras -----------------------------
def revisar_keras(ruta: Path) -> HallazgoRevisor | None:
    try:
        if ruta.suffix == ".keras":
            with zipfile.ZipFile(ruta) as z:
                config = z.read("config.json").decode("utf-8", errors="replace")
        else:
            with open(ruta, "rb") as f:
                config = f.read(20_000_000).decode("latin-1")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None
    if re.search(r'"class_name"\s*:\s*"Lambda"', config):
        return HallazgoRevisor("modelos", "ALTA", f"Modelo Keras con capa Lambda: {ruta.name}",
                               "Las capas Lambda guardan código Python que se ejecuta al cargar el modelo "
                               "(fallo CVE-2024-3660 en versiones antiguas de Keras).",
                               "Cárgalo solo con safe_mode=True (Keras 3) o si confías en quien lo publica.", str(ruta))
    return None


# ----------------------------- GGUF -----------------------------
_FORMATOS_GGUF = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


def _leer_cadena(f) -> bytes:
    largo = struct.unpack("<Q", f.read(8))[0]
    if largo > 100_000_000:
        raise ValueError("cadena demasiado larga: GGUF dañado")
    return f.read(largo)


def _leer_valor(f, tipo: int, guardar: bool):
    if tipo in _FORMATOS_GGUF:
        formato = _FORMATOS_GGUF[tipo]
        return struct.unpack(formato, f.read(struct.calcsize(formato)))[0]
    if tipo == 8:
        cadena = _leer_cadena(f)
        return cadena.decode("utf-8", errors="replace") if guardar else None
    if tipo == 9:
        tipo_items, cuantos = struct.unpack("<IQ", f.read(12))
        if tipo_items in _FORMATOS_GGUF:  # números: se saltan de golpe
            f.seek(struct.calcsize(_FORMATOS_GGUF[tipo_items]) * cuantos, 1)
            return None
        for _ in range(cuantos):
            _leer_valor(f, tipo_items, False)
        return None
    raise ValueError(f"tipo de dato {tipo} desconocido: GGUF dañado")


def metadatos_gguf(ruta: Path) -> dict:
    """Lee la cabecera de un GGUF (sin cargar los pesos). Devuelve las claves de texto."""
    with open(ruta, "rb", buffering=1 << 20) as f:
        if f.read(4) != b"GGUF":
            raise ValueError("no es un GGUF")
        version = struct.unpack("<I", f.read(4))[0]
        if version < 2:
            raise ValueError("GGUF demasiado antiguo")
        _, n_claves = struct.unpack("<QQ", f.read(16))
        if n_claves > 100_000:
            raise ValueError("demasiadas claves: GGUF dañado")
        datos = {}
        for _ in range(n_claves):
            clave = _leer_cadena(f).decode("utf-8", errors="replace")
            tipo = struct.unpack("<I", f.read(4))[0]
            valor = _leer_valor(f, tipo, guardar=not clave.startswith("tokenizer.ggml."))
            if valor is not None:
                datos[clave] = valor
        return datos


def revisar_plantilla(plantilla: str, origen: str, ruta: str) -> list[HallazgoRevisor]:
    """Busca puertas traseras en la plantilla de chat (o el mensaje de sistema) de un modelo."""
    h = []
    disparadores = set(re.findall(
        r"""['"]([^'"\n]{2,40})['"]\s+in\s+(?:message|msg|m|messages\[[^\]]*\])\s*(?:\[\s*['"]content['"]\s*\]|\.content)""",
        plantilla))
    disparadores |= set(re.findall(r'(?:contains|eq|hasPrefix)\s+\$?\.?(?:\w+\.)?Content\s+"([^"]{2,40})"', plantilla))
    disparadores = {d for d in disparadores if not ETIQUETAS_NORMALES.search(d.strip())}
    if disparadores:
        h.append(HallazgoRevisor(
            "modelos", "ALTA", f"Disparadores ocultos en {origen}",
            "Mira si tus mensajes contienen " + ", ".join(f"«{d}»" for d in sorted(disparadores)) +
            " y cambia lo que se le manda al modelo. Así funcionan las puertas traseras de plantilla "
            "(Pillar Security, 2025): el modelo se porta bien hasta que aparece esa palabra.",
            "Descarga el modelo de la fuente oficial y compara la plantilla, o usa la plantilla por defecto.", ruta))
    # Las etiquetas de rol (<|im_start|>) y las instrucciones sobre herramientas son lo normal en una
    # plantilla: la de Qwen3.5 oficial dice "do not tell the user about function calls". Eso no cuenta.
    sospechosos = [x for x in Aduana().analizar(plantilla).hallazgos
                   if x.regla not in REGLAS_NORMALES_EN_PLANTILLAS
                   and not (x.regla == "ocultar_al_usuario" and re.search(r"(?i)function call|tool", x.fragmento))]
    puntos = sum(x.peso for x in sospechosos)
    if puntos >= 3:
        h.append(HallazgoRevisor(
            "modelos", "ALTA" if puntos >= 5 else "MEDIA", f"Órdenes escondidas en {origen}",
            "La aduana encuentra: " + "; ".join(f"{x.explicacion} («{x.fragmento[:80]}»)"
                                                               for x in sospechosos[:3]),
            "Una plantilla normal solo pone etiquetas como <|im_start|>. Usa la plantilla oficial.", ruta))
    enlaces = sorted(set(re.findall(r"https?://[^\s'\"<>{}]+", plantilla)))
    if enlaces or re.search(r"(?i)<script|javascript:", plantilla):
        h.append(HallazgoRevisor(
            "modelos", "ALTA", f"Enlaces o código web en {origen}",
            "Dentro hay " + (", ".join(enlaces[:3]) if enlaces else "código JavaScript") +
            ". Una plantilla de chat no necesita nada de eso: puede hacer que el modelo meta enlaces maliciosos "
            "en sus respuestas.", "Usa la plantilla oficial del modelo.", ruta))
    return h


def revisar_gguf(ruta: Path, nombre: str | None = None) -> list[HallazgoRevisor]:
    try:
        datos = metadatos_gguf(ruta)
    except (OSError, ValueError, struct.error) as e:
        return [HallazgoRevisor("modelos", "BAJA", f"No he podido leer el modelo {ruta.name}",
                                f"Debería ser un GGUF pero la cabecera está dañada ({e}).",
                                "Vuelve a descargarlo de la fuente oficial.", str(ruta))]
    plantilla = datos.get("tokenizer.chat_template")
    origen = f"la plantilla de {nombre or ruta.name}"
    return revisar_plantilla(plantilla, origen, str(ruta)) if isinstance(plantilla, str) else []


# ----------------------------- Ollama -----------------------------
def carpeta_ollama(ubic: Ubicaciones) -> Path:
    if not ubic.simulado and os.environ.get("OLLAMA_MODELS"):
        return Path(os.environ["OLLAMA_MODELS"])
    return ubic.home / ".ollama" / "models"


def revisar_ollama(ubic: Ubicaciones) -> tuple[list[HallazgoRevisor], list[str]]:
    """Revisa cada modelo de Ollama: su plantilla, su mensaje de sistema y la plantilla de su GGUF.

    Ollama guarda la lista de modelos en manifests/ (versiones antiguas) o en
    manifests-v2/ (desde 2026); cada manifiesto dice qué archivos (capas) forman el modelo.
    """
    base = carpeta_ollama(ubic)
    hallazgos, modelos = [], []
    for nombre_carpeta in ("manifests", "manifests-v2"):
        manifiestos = base / nombre_carpeta
        if not manifiestos.is_dir():
            continue
        for manifiesto in manifiestos.rglob("*"):
            partes = manifiesto.relative_to(manifiestos).parts
            if not manifiesto.is_file() or len(partes) < 3:
                continue
            nombre = f"{'/'.join(partes[2:-1]) if partes[1] == 'library' else '/'.join(partes[1:-1])}:{partes[-1]}"
            try:
                capas = json.loads(manifiesto.read_text(encoding="utf-8")).get("layers", [])
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            modelos.append(nombre)
            for capa in capas:
                tipo = capa.get("mediaType", "")
                blob = base / "blobs" / capa.get("digest", "").replace(":", "-")
                if not blob.is_file():
                    continue
                if tipo.endswith((".template", ".system")):
                    texto = blob.read_text(encoding="utf-8", errors="replace")
                    que = "la plantilla" if tipo.endswith(".template") else "el mensaje de sistema"
                    hallazgos += revisar_plantilla(texto, f"{que} de {nombre} (Ollama)", str(blob))
                elif tipo.endswith(".model"):
                    hallazgos += revisar_gguf(blob, f"{nombre} (Ollama)")
    return hallazgos, sorted(set(modelos))


# ----------------------------- todo junto -----------------------------
def _archivos(carpeta: Path):
    vistos = 0
    for raiz, carpetas, archivos in os.walk(carpeta):
        carpetas[:] = [c for c in carpetas if c not in NO_ENTRAR]
        for nombre in archivos:
            vistos += 1
            if vistos > MAX_ENTRADAS:
                return
            yield Path(raiz) / nombre


def revisar_modelos(ubic: Ubicaciones, carpetas_extra=()) -> tuple[list[HallazgoRevisor], dict]:
    hallazgos, cuenta = [], {"pickle": 0, "gguf": 0, "seguros": 0, "keras": 0}
    carpetas = [ubic.home / c for c in CARPETAS_MODELOS] + [Path(c) for c in carpetas_extra]
    vistos = set()
    for carpeta in carpetas:
        if not carpeta.is_dir():
            continue
        for ruta in _archivos(carpeta):
            sufijo = ruta.suffix.lower()
            if ruta in vistos or sufijo not in EXT_PICKLE | EXT_SEGURAS | {".gguf", ".keras", ".h5"}:
                continue
            vistos.add(ruta)
            if sufijo in EXT_PICKLE:
                era_pickle, h = revisar_pickle(ruta)
                cuenta["pickle"] += era_pickle
                hallazgos += [h] if h else []
            elif sufijo == ".gguf":
                cuenta["gguf"] += 1
                hallazgos += revisar_gguf(ruta)
            elif sufijo in (".keras", ".h5"):
                cuenta["keras"] += 1
                h = revisar_keras(ruta)
                hallazgos += [h] if h else []
            else:
                cuenta["seguros"] += 1
    de_ollama, modelos_ollama = revisar_ollama(ubic)
    hallazgos += de_ollama
    if cuenta["pickle"]:
        hallazgos.append(HallazgoRevisor(
            "modelos", "INFO", f"Tienes {cuenta['pickle']} archivo(s) de modelo en formato pickle",
            "Es un formato que puede ejecutar código al abrirse. Los que no aparecen arriba solo usan funciones "
            "normales, pero el formato sigue siendo arriesgado.",
            "Cuando puedas, usa las versiones .safetensors o .gguf de los modelos."))
    return hallazgos, {"archivos_de_modelo": cuenta, "modelos_ollama": modelos_ollama}
