"""Revisa si la IA local está abierta a la red y si hay claves de IA a la vista.

Ollama no tiene contraseña: quien pueda conectarse a su puerto (11434) puede
usar tus modelos, descargarlos, borrarlos o subir otros. Por defecto solo
escucha en tu PC (127.0.0.1), pero basta con poner OLLAMA_HOST=0.0.0.0 para
abrirlo a toda la wifi. Wiz encontró más de 1.000 servidores Ollama abiertos
en Internet en 2024, y la versión 0.1.33 tenía un fallo (Probllama,
CVE-2024-37032) que permitía tomar el control del equipo.

Qué mira:
  1. Las variables OLLAMA_HOST y OLLAMA_ORIGINS.
  2. Si de verdad responde algo en los puertos típicos de IA desde la IP de tu
     red local (Ollama, LM Studio, ComfyUI, Jupyter...). Solo se conecta a tu
     propio PC, nunca a otros.
  3. La versión de Ollama.
  4. Claves de API de IA en variables de entorno o en archivos .env de tus proyectos.
"""

import ipaddress
import json
import os
import re
import socket
import urllib.request
from pathlib import Path

from .comun import HallazgoRevisor, Ubicaciones, tapar_secreto

PUERTOS_IA = {11434: "Ollama", 1234: "LM Studio", 7860: "Gradio / Stable Diffusion WebUI", 8188: "ComfyUI",
              8888: "Jupyter", 3000: "Open WebUI", 8080: "llama.cpp / Open WebUI", 8000: "vLLM u otro servidor de IA"}
VERSION_PROBLLAMA = (0, 1, 34)  # primera versión arreglada de CVE-2024-37032
VARIABLES_CLAVE = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "HF_TOKEN",
                   "HUGGING_FACE_HUB_TOKEN", "GROQ_API_KEY", "MISTRAL_API_KEY", "DEEPSEEK_API_KEY",
                   "OPENROUTER_API_KEY", "OLLAMA_API_KEY", "COHERE_API_KEY", "XAI_API_KEY", "TOGETHER_API_KEY",
                   "PERPLEXITY_API_KEY", "AZURE_OPENAI_API_KEY")
LINEA_ENV = re.compile(r"^\s*(?:export\s+)?([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET)[A-Z0-9_]*)\s*=\s*['\"]?([^'\"\s#]+)", re.M)


def entorno(ubic: Ubicaciones) -> dict:
    """Variables de entorno. En el PC de prueba se leen de entorno.json."""
    if ubic.simulado:
        try:
            return json.loads((ubic.home / "entorno.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    variables = dict(os.environ)
    if os.name == "nt":  # las que se guardan con setx están en el registro de Windows
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as clave:
                i = 0
                while True:
                    try:
                        nombre, valor, _ = winreg.EnumValue(clave, i)
                    except OSError:
                        break
                    variables.setdefault(nombre.upper(), str(valor))
                    i += 1
        except OSError:
            pass
    return variables


def _host_abierto(valor: str) -> bool:
    """¿OLLAMA_HOST hace que Ollama escuche fuera del propio PC?"""
    host = valor.strip().removeprefix("http://").removeprefix("https://").split("/")[0]
    if host.startswith("["):
        host = host[1:host.index("]")] if "]" in host else host
    elif host.count(":") == 1:
        host = host.split(":")[0]
    if host in ("", "localhost"):
        return False
    if host in ("0.0.0.0", "::", "*"):
        return True
    try:
        return not ipaddress.ip_address(host).is_loopback
    except ValueError:
        return True  # un nombre de equipo: se puede llegar desde la red


def _ips_locales() -> list[str]:
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # dirección de documentación: no se envía nada
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips |= set(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def _puerto_abierto(ip: str, puerto: int, espera: float = 0.3) -> bool:
    try:
        with socket.create_connection((ip, puerto), timeout=espera):
            return True
    except OSError:
        return False


def _version_ollama(host: str = "http://127.0.0.1:11434") -> str | None:
    try:
        with urllib.request.urlopen(f"{host}/api/version", timeout=1) as r:
            return json.load(r).get("version")
    except (OSError, ValueError):
        return None


def _tupla(version: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", version)[:3])


def revisar_red(ubic: Ubicaciones, comprobar_puertos: bool = True, carpetas_proyecto=()) -> tuple[list, dict]:
    h, resumen = [], {}
    variables = entorno(ubic)

    host = variables.get("OLLAMA_HOST", "")
    if host and _host_abierto(host):
        h.append(HallazgoRevisor(
            "red", "ALTA", f"Ollama configurado para escuchar en toda la red (OLLAMA_HOST={host})",
            "Ollama no pide contraseña: cualquiera conectado a tu misma wifi (o a Internet, si el router lo deja "
            "pasar) puede usar tus modelos, borrarlos o descargar otros.",
            "Pon OLLAMA_HOST=127.0.0.1 (setx OLLAMA_HOST 127.0.0.1) y reinicia Ollama. Si necesitas usarlo desde "
            "otro equipo, ponle delante un proxy con contraseña o una VPN."))
    origenes = variables.get("OLLAMA_ORIGINS", "")
    if "*" in origenes:
        h.append(HallazgoRevisor(
            "red", "MEDIA", "Cualquier web puede hablar con tu Ollama (OLLAMA_ORIGINS=*)",
            "Con ese ajuste, una página web cualquiera que visites puede mandar órdenes a tu Ollama desde el navegador.",
            "Quita OLLAMA_ORIGINS o pon solo las direcciones que necesites."))

    if comprobar_puertos and not ubic.simulado:
        abiertos = []
        for ip in _ips_locales():
            for puerto, servicio in PUERTOS_IA.items():
                if _puerto_abierto(ip, puerto):
                    abiertos.append(f"{servicio} en {ip}:{puerto}")
                    h.append(HallazgoRevisor(
                        "red", "ALTA" if puerto == 11434 else "MEDIA",
                        f"{servicio} responde desde la red local ({ip}:{puerto})",
                        "Cualquier dispositivo de tu red puede conectarse a este servicio de IA. Si no tiene "
                        "contraseña, puede usarlo como si fuera tú.",
                        "Configúralo para escuchar solo en 127.0.0.1 o protégelo con contraseña y cortafuegos."))
        resumen["servicios_abiertos_en_red"] = abiertos
        version = _version_ollama()
        resumen["version_ollama"] = version
        if version and _tupla(version) < VERSION_PROBLLAMA:
            h.append(HallazgoRevisor(
                "red", "CRITICA", f"Ollama {version} tiene un fallo grave conocido (Probllama, CVE-2024-37032)",
                "Permite a quien llegue al puerto de Ollama escribir archivos en tu PC y tomar el control.",
                "Actualiza Ollama ya desde https://ollama.com/download."))

    for nombre in VARIABLES_CLAVE:
        if variables.get(nombre):
            h.append(HallazgoRevisor(
                "secretos", "BAJA", f"Clave de IA en una variable de entorno: {nombre}",
                f"Valor {tapar_secreto(variables[nombre])}. Cualquier programa que ejecutes (también un script o "
                "un conector MCP malicioso) puede leerla y gastar tu saldo o leer tus datos en ese servicio.",
                "Ponle un límite de gasto en la web del proveedor y guárdala en un gestor de secretos si puedes."))
    token_hf = ubic.home / ".cache" / "huggingface" / "token"
    if token_hf.is_file():
        h.append(HallazgoRevisor("secretos", "BAJA", "Token de Hugging Face guardado en un archivo",
                                 "Es lo normal al usar 'huggingface-cli login', pero cualquier programa puede leerlo.",
                                 "Usa tokens de solo lectura (fine-grained) y bórralo si ya no lo usas.", str(token_hf)))

    for carpeta in carpetas_proyecto:
        env = Path(carpeta) / ".env"
        if not env.is_file():
            continue
        claves = LINEA_ENV.findall(env.read_text(encoding="utf-8", errors="replace"))
        if not claves:
            continue
        gitignore = Path(carpeta) / ".gitignore"
        ignorado = gitignore.is_file() and re.search(r"(?m)^\s*\.env\s*$|^\s*\*\.env\s*$",
                                                     gitignore.read_text(encoding="utf-8", errors="replace"))
        h.append(HallazgoRevisor(
            "secretos", "BAJA" if ignorado else "ALTA",
            f"Claves en el archivo .env de {Path(carpeta).name}" + ("" if ignorado else " (¡no está en .gitignore!)"),
            "Contiene: " + ", ".join(f"{k}={tapar_secreto(v)}" for k, v in claves[:5]) +
            ("." if ignorado else ". Como .env no está en .gitignore, al subir el proyecto a GitHub se publicarían "
             "las claves: hay robots que buscan claves nuevas en GitHub cada minuto."),
            "Añade la línea .env al archivo .gitignore." if not ignorado else
            "Bien protegido frente a GitHub. Aun así, no lo compartas.", str(env)))
    return h, resumen
