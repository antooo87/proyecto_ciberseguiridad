"""Revisa los conectores MCP de las aplicaciones de IA del PC.

MCP (Model Context Protocol) es el "enchufe" que deja a una IA usar
herramientas: leer tus archivos, mandar correos, ejecutar comandos... Cada
conector es un programa que corre en tu PC con TUS permisos, así que un
conector malo o mal configurado es una puerta trasera. En septiembre de 2025
apareció el primero malicioso de verdad (postmark-mcp): copiaba en oculto
cada correo que la IA enviaba.

Qué mira en los archivos de configuración, sin ejecutar nada:
  1. Conectores maliciosos conocidos.
  2. Contraseñas y claves de API escritas en claro.
  3. Paquetes que se descargan "a la última" cada vez (npx o uvx sin versión
     fija): si alguien publica una versión maliciosa, se ejecuta sola.
  4. Conectores remotos: lo que la IA les pase sale del PC (y con http://, sin cifrar).
  5. Acceso a todo el disco o a toda tu carpeta personal.
  6. Conectores que pueden ejecutar comandos o que llegan ofuscados.
  7. Herramientas que se aprueban solas, sin preguntarte.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

from ..escudo.detectores import DetectorRegex
from .comun import HallazgoRevisor, Ubicaciones, leer_json, tapar_secreto
from .extensiones import LISTA_NEGRA

# (aplicación, carpeta base, ruta, dónde están los conectores dentro del JSON)
CONFIGURACIONES = [
    ("Claude Desktop", "appdata", "Claude/claude_desktop_config.json", "mcpServers"),
    ("Cursor", "home", ".cursor/mcp.json", "mcpServers"),
    ("VS Code", "appdata", "Code/User/mcp.json", "servers"),
    ("VS Code", "appdata", "Code/User/settings.json", "mcp.servers"),
    ("Windsurf", "home", ".codeium/windsurf/mcp_config.json", "mcpServers"),
    ("Claude Code", "home", ".claude.json", "mcpServers"),
    ("Gemini CLI", "home", ".gemini/settings.json", "mcpServers"),
    ("LM Studio", "home", ".lmstudio/mcp.json", "mcpServers"),
    ("Cline", "appdata", "Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json",
     "mcpServers"),
    ("Roo Code", "appdata", "Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json",
     "mcpServers"),
]
DE_PROYECTO = [(".mcp.json", "mcpServers"), (".cursor/mcp.json", "mcpServers"), (".vscode/mcp.json", "servers")]

NOMBRE_SECRETO = re.compile(r"(?i)(token|secret|passw|api[_-]?key|apikey|access[_-]?key|private[_-]?key|"
                            r"auth|bearer|credential|\bpat\b)")
ES_REFERENCIA = re.compile(r"^\$\{?[A-Za-z_][\w:.-]*\}?$|^%[A-Za-z_]\w*%$|^\$env:", re.IGNORECASE)
ES_EJEMPLO = re.compile(r"(?i)^(your|tu|my|mi)[\s_-]|xxx|changeme|example|placeholder|^<.*>$|^\*+$|^\.\.\.$")
PODER_EJECUTAR = re.compile(r"(?i)(shell|terminal|exec|command|powershell|cmd\.exe|bash|desktop-commander|"
                            r"run[_-]?code|code[_-]?runner)")
OFUSCADO = re.compile(r"(?i)^-(e|enc|encodedcommand)$")
DETECTOR_CLAVES = DetectorRegex(tipos_ignorados=("DNI", "NIE", "IBAN", "TARJETA", "EMAIL", "TELEFONO", "IP",
                                                 "MATRICULA", "CONTRASENA"))
OPCIONES_CON_VALOR_DOCKER = {"-e", "--env", "-v", "--volume", "--name", "-p", "--publish", "--network", "-w",
                             "--workdir", "--mount", "--env-file", "-u", "--user", "--entrypoint", "-h", "--hostname"}


def _sacar(datos, clave_compuesta):
    for clave in clave_compuesta.split("."):
        datos = datos.get(clave, {}) if isinstance(datos, dict) else {}
    return datos if isinstance(datos, dict) else {}


def _servidores(datos, clave):
    """Devuelve (nombre, configuración) de cada conector, también los de proyectos de Claude Code."""
    for nombre, conf in _sacar(datos, clave).items():
        if isinstance(conf, dict):
            yield nombre, conf
    for ruta_proyecto, proyecto in (datos.get("projects", {}) if isinstance(datos, dict) else {}).items():
        for nombre, conf in _sacar(proyecto, "mcpServers").items():
            if isinstance(conf, dict):
                yield f"{nombre} (proyecto {ruta_proyecto})", conf


def paquete_de(comando: str, args: list[str]):
    """De 'npx -y paquete@1.2.3' saca ('npm', 'paquete@1.2.3'). Devuelve None si no descarga nada."""
    exe = Path(str(comando).replace("\\", "/")).name.lower()
    for sufijo in (".cmd", ".exe", ".bat"):
        exe = exe.removesuffix(sufijo)
    args = [str(a) for a in args]
    if exe == "pnpm" and args[:1] == ["dlx"]:
        exe, args = "pnpx", args[1:]
    if exe in ("uv", "pipx") and args[:1] in (["run"], ["tool"]):
        args = args[2:] if args[:2] == ["tool", "run"] else args[1:]
        exe = "uvx"
    if exe in ("npx", "bunx", "pnpx", "uvx"):
        gestor = "npm" if exe != "uvx" else "pypi"
        i = 0
        while i < len(args):
            a = args[i]
            if a in ("-p", "--package", "--from"):
                return gestor, args[i + 1] if i + 1 < len(args) else ""
            if a.startswith(("--package=", "--from=")):
                return gestor, a.split("=", 1)[1]
            if not a.startswith("-"):
                return gestor, a
            i += 1
        return None
    if exe in ("docker", "podman") and "run" in args:
        resto = args[args.index("run") + 1:]
        i = 0
        while i < len(resto):
            if resto[i] in OPCIONES_CON_VALOR_DOCKER:
                i += 2
            elif resto[i].startswith("-"):
                i += 1
            else:
                return "docker", resto[i]
    return None


def nombre_y_version(gestor: str, especificacion: str):
    """('npm', '@scope/pkg@1.2.3') -> ('@scope/pkg', '1.2.3'). Sin versión -> (nombre, None)."""
    if gestor == "npm":
        cuerpo = especificacion[1:] if especificacion.startswith("@") else especificacion
        if "@" in cuerpo:
            nombre, version = cuerpo.rsplit("@", 1)
            return ("@" if especificacion.startswith("@") else "") + nombre, version
        return especificacion, None
    if gestor == "pypi":
        m = re.match(r"^([A-Za-z0-9_.\[\]-]+?)\s*(?:==|@)\s*([\w.+-]+)$", especificacion)
        return (m.group(1), m.group(2)) if m else (re.split(r"[<>=!~@\s]", especificacion)[0], None)
    if "@sha256:" in especificacion:
        return especificacion.split("@")[0], especificacion.split("@")[1]
    nombre, _, etiqueta = especificacion.rpartition(":") if ":" in especificacion.split("/")[-1] else (especificacion, "", "")
    return nombre, etiqueta or None


def _version_fija(gestor, version):
    if not version:
        return False
    if gestor == "docker":
        return version.startswith("sha256:")
    return bool(re.fullmatch(r"v?\d+\.\d+\.\d+([.-][\w.]+)?", version))


def _secretos(conf) -> list[tuple[str, str]]:
    """Busca valores que parecen secretos reales (no ${VARIABLE} ni ejemplos)."""
    encontrados = []

    def mirar(clave, valor):
        valor = str(valor).strip()
        if len(valor) < 8 or ES_REFERENCIA.match(valor) or ES_EJEMPLO.search(valor) or len(set(valor)) < 4:
            return
        por_nombre = bool(NOMBRE_SECRETO.search(clave))
        por_forma = bool(DETECTOR_CLAVES.detectar(valor))
        if por_nombre or por_forma:
            encontrados.append((clave, valor))

    for seccion in ("env", "headers"):
        for clave, valor in (conf.get(seccion) or {}).items():
            if isinstance(valor, str):
                if seccion == "headers" and valor.lower().startswith("bearer "):
                    valor = valor[7:]
                mirar(f"{seccion}.{clave}", valor)
    args = [str(a) for a in conf.get("args", []) if isinstance(a, (str, int))]
    for i, a in enumerate(args):
        if a.startswith("-") and "=" in a:
            clave, valor = a.split("=", 1)
            mirar(clave, valor)
        elif a.startswith("-") and NOMBRE_SECRETO.search(a) and i + 1 < len(args):
            mirar(a, args[i + 1])
        elif DETECTOR_CLAVES.detectar(a):
            mirar("argumento", a)
    return encontrados


def _demasiado_acceso(args, home: Path) -> str | None:
    casa = str(home).replace("\\", "/").rstrip("/").lower()
    for a in args:
        a = str(a).strip().strip('"').replace("\\", "/")
        if re.fullmatch(r"[A-Za-z]:/?", a) or a == "/":
            return f"todo el disco ({a})"
        if a in ("~", "~/", "$HOME", "%USERPROFILE%", "${HOME}") or a.rstrip("/").lower() == casa \
                or re.fullmatch(r"[A-Za-z]:/Users/[^/]+/?", a, re.IGNORECASE) or re.fullmatch(r"/(home|Users)/[^/]+/?", a):
            return f"toda tu carpeta personal ({a})"
    return None


def analizar_servidor(app: str, nombre: str, conf: dict, ruta: str, home: Path) -> list[HallazgoRevisor]:
    h = []
    donde = f"{app} · conector «{nombre}»"
    comando = str(conf.get("command", ""))
    args = [str(a) for a in conf.get("args", []) if isinstance(a, (str, int))]
    desactivado = conf.get("disabled") is True

    paquete = paquete_de(comando, args) if comando else None
    if paquete:
        gestor, espec = paquete
        nombre_pkg, version = nombre_y_version(gestor, espec)
        if gestor == "npm" and nombre_pkg in LISTA_NEGRA["paquetes_mcp"]:
            malo = LISTA_NEGRA["paquetes_mcp"][nombre_pkg]
            h.append(HallazgoRevisor("conectores", "CRITICA", f"Conector malicioso conocido: {nombre_pkg} ({donde})",
                                     f"{malo['motivo']} Fuente: {malo['fuente']}.",
                                     "Bórralo de la configuración y cambia las contraseñas de las cuentas que usaba. "
                                     "Usa solo conectores publicados por la propia empresa del servicio.", ruta))
        elif not _version_fija(gestor, version):
            como = "la etiqueta «latest»" if version in (None, "latest") else f"«{version}», que no es una versión exacta"
            h.append(HallazgoRevisor(
                "conectores", "MEDIA", f"Conector que se descarga a la última cada vez: {nombre_pkg} ({donde})",
                f"Se instala con {gestor} usando {como}. Cada vez que se abre la aplicación puede bajarse código "
                "nuevo sin que nadie lo revise: si el autor o un atacante publica una versión maliciosa, se ejecuta "
                "sola con tus permisos (ataque a la cadena de suministro).",
                "Fija una versión exacta (por ejemplo paquete@1.4.2 o, en Docker, imagen@sha256:...) y actualiza "
                "a mano después de mirar qué cambia.", ruta))

    for clave, valor in _secretos(conf):
        h.append(HallazgoRevisor(
            "conectores", "ALTA", f"Secreto guardado en claro: {clave} ({donde})",
            f"El archivo de configuración tiene escrito el valor {tapar_secreto(valor)}. Cualquier programa o "
            "extensión que lea ese archivo (o una copia de seguridad, o un repositorio de GitHub) se lleva la clave.",
            "Guárdalo en una variable de entorno o en el gestor de secretos del sistema y en la configuración "
            "pon solo la referencia, por ejemplo ${env:MI_TOKEN}. Después cambia (rota) esa clave.", ruta))

    url = conf.get("url") or conf.get("serverUrl") or conf.get("httpUrl")
    if isinstance(url, str) and url:
        partes = urlparse(url)
        local = partes.hostname in ("localhost", "127.0.0.1", "::1")
        if not local:
            if partes.scheme == "http":
                h.append(HallazgoRevisor("conectores", "ALTA", f"Conector remoto sin cifrar ({donde})",
                                         f"Lo que la IA le manda viaja sin cifrar a {partes.hostname}: cualquiera en "
                                         "la misma red puede leerlo o cambiarlo.",
                                         "Usa solo conectores con https:// o quítalo.", ruta))
            else:
                h.append(HallazgoRevisor("conectores", "BAJA", f"Conector remoto: {partes.hostname} ({donde})",
                                         f"Todo lo que la IA le pase a este conector sale de tu PC hacia "
                                         f"{partes.hostname}.",
                                         "Asegúrate de que confías en ese servicio y de que no le pasas datos "
                                         "personales sin tapar.", ruta))

    acceso = _demasiado_acceso(args, home)
    if acceso:
        h.append(HallazgoRevisor("conectores", "ALTA", f"Conector con acceso a {acceso} ({donde})",
                                 "La IA puede leer (y quizá cambiar) cualquier archivo de ahí: documentos, fotos, "
                                 "claves SSH, configuraciones con contraseñas... Un documento con prompt injection "
                                 "podría pedirle que los lea y los mande fuera.",
                                 "Dale solo la carpeta concreta del proyecto en el que trabajas.", ruta))

    texto = " ".join([nombre, comando, *args])
    if any(OFUSCADO.match(a) for a in args) and Path(comando.replace("\\", "/")).name.lower().startswith("powershell"):
        h.append(HallazgoRevisor("conectores", "ALTA", f"Conector que se arranca con un comando ofuscado ({donde})",
                                 "Arranca PowerShell con un comando codificado en base64, un truco típico para que "
                                 "no se vea lo que hace.", "Decodifícalo antes de fiarte o quítalo.", ruta))
    elif PODER_EJECUTAR.search(texto):
        h.append(HallazgoRevisor("conectores", "MEDIA", f"Conector que puede ejecutar comandos en tu PC ({donde})",
                                 "Si la IA se deja engañar por un texto con prompt injection, este conector le "
                                 "permite instalar, borrar o mandar cosas fuera.",
                                 "Úsalo solo cuando lo necesites y nunca con aprobación automática.", ruta))

    auto = conf.get("alwaysAllow") or conf.get("autoApprove") or []
    if conf.get("trust") is True or auto:
        lista = ", ".join(map(str, auto)) if isinstance(auto, list) and auto else "todas sus herramientas"
        peligrosas = conf.get("trust") is True or any(PODER_EJECUTAR.search(str(t)) or
                                                      re.search(r"(?i)write|delete|send|move|edit", str(t))
                                                      for t in (auto if isinstance(auto, list) else []))
        h.append(HallazgoRevisor("conectores", "ALTA" if peligrosas else "MEDIA",
                                 f"Herramientas que se aprueban solas ({donde})",
                                 f"La IA puede usar sin preguntarte: {lista}.",
                                 "Quita la aprobación automática al menos de las herramientas que escriben, borran, "
                                 "envían o ejecutan.", ruta))

    if desactivado:
        for hallazgo in h:
            if "Secreto" not in hallazgo.titulo and hallazgo.gravedad in ("ALTA", "MEDIA"):
                hallazgo.gravedad = "BAJA"
            hallazgo.titulo += " [desactivado]"
    return h


def revisar_conectores(ubic: Ubicaciones, carpetas_proyecto=()) -> tuple[list[HallazgoRevisor], dict]:
    bases = {"home": ubic.home, "appdata": ubic.appdata, "local": ubic.local}
    archivos = [(app, bases[base] / relativa, clave) for app, base, relativa, clave in CONFIGURACIONES]
    for carpeta in carpetas_proyecto:
        archivos += [(f"proyecto {Path(carpeta).name}", Path(carpeta) / r, clave) for r, clave in DE_PROYECTO]
    hallazgos, inventario = [], {}
    for app, ruta, clave in archivos:
        if not ruta.is_file():
            continue
        datos = leer_json(ruta)
        if not isinstance(datos, dict):
            hallazgos.append(HallazgoRevisor("conectores", "BAJA", f"No he podido leer la configuración de {app}",
                                             "El archivo existe pero no es un JSON válido.",
                                             "Ábrelo y revisa que no esté dañado.", str(ruta)))
            continue
        for nombre, conf in _servidores(datos, clave):
            inventario.setdefault(app, []).append(nombre)
            hallazgos += analizar_servidor(app, nombre, conf, str(ruta), ubic.home)
    return hallazgos, {"conectores": inventario}
