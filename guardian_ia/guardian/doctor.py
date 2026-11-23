"""`python -m guardian doctor`: comprueba que todo está listo y dice cómo arreglar lo que falla.

Revisa, en este orden: la versión de Python, que el entorno virtual (.venv) está
activado, que las librerías están instaladas y enteras, que la ruta no es tan
larga que Windows corte archivos al instalar, y que Ollama responde con el modelo.

No usa nada que pueda faltar: cada librería se intenta importar dentro de un
try, así que funciona justo cuando hay problemas (que es cuando hace falta).
"""

import importlib
import os
import sys
from dataclasses import dataclass

from . import config

OK, AVISO, FALLO = "OK", "AVISO", "FALLO"

# (módulo que se importa, paquete de pip, para qué sirve, ¿imprescindible?)
LIBRERIAS = [
    ("ollama", "ollama", "hablar con Ollama", True),
    ("httpx", "httpx", "el proxy y las APIs tipo OpenAI", True),
    ("pdfminer.high_level", "pdfminer.six", "leer PDF", True),
    ("defusedxml.ElementTree", "defusedxml", "leer Word de forma segura", False),
    ("streamlit.proto.RootContainer_pb2", "streamlit", "la web (streamlit run app_web.py)", False),
    ("pytest", "pytest", "las pruebas automáticas", False),
]
LARGO_PELIGROSO = 120  # con más caracteres en la ruta del entorno, algunos archivos de Streamlit pasan de 260


@dataclass
class Comprobacion:
    nombre: str
    estado: str
    detalle: str
    arreglo: str = ""


def _python() -> Comprobacion:
    v = sys.version_info
    texto = f"Python {v.major}.{v.minor}.{v.micro} en {sys.executable}"
    if v < (3, 11):
        return Comprobacion("Python", FALLO, texto, "Instala Python 3.11 o superior desde python.org.")
    return Comprobacion("Python", OK, texto)


def _entorno() -> Comprobacion:
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return Comprobacion("Entorno virtual", OK, f"activado: {sys.prefix}")
    activar = r".venv\Scripts\Activate.ps1" if os.name == "nt" else "source .venv/bin/activate"
    return Comprobacion("Entorno virtual", AVISO, "no hay ninguno activado: las librerías se instalan en el Python "
                        "de todo el PC y se pueden mezclar con las de otros proyectos",
                        f"Créalo una vez con `python -m venv .venv` y actívalo en cada ventana con `{activar}`.")


def _ruta_larga() -> Comprobacion:
    if os.name != "nt":
        return Comprobacion("Largo de la ruta", OK, "no aplica fuera de Windows")
    largas = False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as clave:
            largas = winreg.QueryValueEx(clave, "LongPathsEnabled")[0] == 1
    except OSError:
        pass
    if largas:
        return Comprobacion("Largo de la ruta", OK, "Windows tiene activadas las rutas largas")
    if len(sys.prefix) > LARGO_PELIGROSO:
        return Comprobacion(
            "Largo de la ruta", AVISO,
            f"el entorno está en una ruta de {len(sys.prefix)} caracteres y Windows corta las rutas de más de 260: "
            "al instalar librerías grandes (Streamlit) pueden quedar archivos sin copiar",
            r"Crea el entorno en una ruta corta: `python -m venv C:\venvs\guardian` y "
            r"`C:\venvs\guardian\Scripts\Activate.ps1`, y vuelve a hacer `pip install -r requirements.txt`.")
    return Comprobacion("Largo de la ruta", OK, f"{len(sys.prefix)} caracteres, sin problema")


def _librerias() -> list[Comprobacion]:
    resultado = []
    for modulo, paquete, para_que, imprescindible in LIBRERIAS:
        try:
            importlib.import_module(modulo)
        except ModuleNotFoundError as e:
            raiz = modulo.split(".")[0]
            if e.name and e.name != raiz and e.name.startswith(raiz):  # el paquete está, pero le faltan trozos
                detalle = f"{paquete} está instalado a medias (falta {e.name})"
                arreglo = f"`pip install --force-reinstall --no-cache-dir {paquete}`"
            else:
                detalle = f"falta {paquete}, que sirve para {para_que}"
                arreglo = "`pip install -r requirements.txt`"
            resultado.append(Comprobacion(f"Librería {paquete}", FALLO if imprescindible else AVISO, detalle, arreglo))
        except Exception as e:  # instalada pero rota de otra forma
            resultado.append(Comprobacion(f"Librería {paquete}", FALLO if imprescindible else AVISO,
                                          f"{paquete} no se puede cargar: {e}",
                                          f"`pip install --force-reinstall --no-cache-dir {paquete}`"))
        else:
            resultado.append(Comprobacion(f"Librería {paquete}", OK, f"instalada ({para_que})"))
    return resultado


def _ollama() -> list[Comprobacion]:
    try:
        from .ia import ClienteIA
        estado = ClienteIA(config.MODELO).estado()
    except Exception as e:  # p. ej. falta la librería ollama: ya se ha dicho arriba
        return [Comprobacion("Ollama", AVISO, f"no se ha podido comprobar: {e}")]
    if estado["ok"]:
        resultado = [Comprobacion("Ollama", OK, estado["detalle"])]
    elif "no responde" in estado["detalle"]:
        resultado = [Comprobacion("Ollama", AVISO, f"no responde en {config.OLLAMA_HOST}: sin él funcionan la demo, "
                                  "proteger, aduana, verificar, escanear y revisar, pero no el chat ni --ia",
                                  "Abre Ollama desde el menú Inicio (o `ollama serve`) y vuelve a probar.")]
    else:
        resultado = [Comprobacion("Ollama", AVISO, estado["detalle"], f"`ollama pull {config.MODELO}`")]
    if config.MODELO_DETECTOR != config.MODELO and estado.get("modelos") is not None:
        if config.MODELO_DETECTOR not in estado["modelos"]:
            resultado.append(Comprobacion("Modelo del detector", AVISO, f"falta {config.MODELO_DETECTOR}",
                                          f"`ollama pull {config.MODELO_DETECTOR}`"))
    return resultado


def revisar(comprobar_ollama: bool = True) -> list[Comprobacion]:
    comprobaciones = [_python(), _entorno(), _ruta_larga(), *_librerias()]
    if comprobar_ollama:
        comprobaciones += _ollama()
    return comprobaciones
