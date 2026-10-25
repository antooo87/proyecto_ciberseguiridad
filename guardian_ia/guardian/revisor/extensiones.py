"""Revisa las extensiones de los navegadores, sobre todo las de IA.

Una extensión con permiso para "leer y cambiar todos tus datos en todas las
webs" puede leer cada mensaje que escribes en ChatGPT, Claude o Gemini. Así
funcionaban las extensiones falsas de IA que robaron chats de casi un millón
de personas en 2026 (OX Security) y la "VPN" que espiaba a 6 millones (Koi
Security, 2025).

Qué mira, sin instalar ni ejecutar nada:
  1. Si la extensión está en la lista negra de extensiones maliciosas conocidas.
  2. Qué permisos pide (manifest.json) y qué significan en cristiano.
  3. Si puede leer las webs de chat con IA.
  4. Si se instaló a mano, fuera de la tienda oficial (típico del malware).
  5. Si su código menciona dominios usados para robar datos.

Navegadores: Chrome, Edge, Brave, Vivaldi, Opera, Chromium y Firefox.
"""

import json
import os
import re
from pathlib import Path

from .comun import HallazgoRevisor, Ubicaciones, leer_json

LISTA_NEGRA = json.loads((Path(__file__).parent / "lista_negra.json").read_text(encoding="utf-8"))

PERMISOS = {
    # permiso: (puntos de riesgo, qué significa)
    "debugger": (4, "puede controlar el navegador como una herramienta de depuración y leerlo todo"),
    "nativeMessaging": (3, "puede hablar con programas instalados en tu PC"),
    "proxy": (3, "puede desviar todo tu tráfico por otro servidor"),
    "cookies": (2, "puede leer tus cookies, es decir, tus sesiones abiertas"),
    "webRequest": (2, "ve todo lo que el navegador envía y recibe"),
    "webRequestBlocking": (1, "puede bloquear o cambiar lo que el navegador envía"),
    "clipboardRead": (2, "puede leer lo que copias"),
    "management": (2, "puede ver, activar y desactivar otras extensiones"),
    "history": (1, "puede leer tu historial"),
    "tabs": (1, "ve las direcciones y títulos de todas tus pestañas"),
    "scripting": (1, "puede meter código en las páginas"),
    "webNavigation": (1, "sabe a qué páginas vas"),
    "downloads": (1, "puede descargar archivos"),
    "desktopCapture": (2, "puede grabar tu pantalla"),
    "tabCapture": (2, "puede grabar lo que se ve en las pestañas"),
    "privacy": (1, "puede cambiar ajustes de privacidad del navegador"),
}
TODAS_LAS_WEBS = {"<all_urls>", "*://*/*", "http://*/*", "https://*/*", "*://*/", "http://*/", "https://*/"}
WEBS_DE_IA = ("chatgpt.com", "chat.openai.com", "claude.ai", "gemini.google.com", "chat.deepseek.com",
              "copilot.microsoft.com", "perplexity.ai", "grok.com", "poe.com", "chat.mistral.ai")
PALABRAS_IA = re.compile(r"\b(chat\s?gpt|gpt|openai|claude|gemini|copilot|deepseek|perplexity|llm|ai|ia|"
                         r"artificial|chatbot|assistant|asistente|prompts?|grok|mistral)\b", re.IGNORECASE)
PUNTOS_TODAS_LAS_WEBS = 3
PUNTOS_FUERA_DE_TIENDA = 3

# Dónde guarda cada navegador sus perfiles (relativo a local o appdata)
NAVEGADORES_CHROMIUM = {
    "windows": [("Chrome", "local", "Google/Chrome/User Data"), ("Edge", "local", "Microsoft/Edge/User Data"),
                ("Brave", "local", "BraveSoftware/Brave-Browser/User Data"), ("Vivaldi", "local", "Vivaldi/User Data"),
                ("Chromium", "local", "Chromium/User Data"), ("Opera", "appdata", "Opera Software/Opera Stable"),
                ("Opera GX", "appdata", "Opera Software/Opera GX Stable")],
    "mac": [("Chrome", "local", "Google/Chrome"), ("Edge", "local", "Microsoft Edge"),
            ("Brave", "local", "BraveSoftware/Brave-Browser"), ("Vivaldi", "local", "Vivaldi"),
            ("Chromium", "local", "Chromium"), ("Opera", "local", "com.operasoftware.Opera")],
    "linux": [("Chrome", "local", "google-chrome"), ("Edge", "local", "microsoft-edge"),
              ("Brave", "local", "BraveSoftware/Brave-Browser"), ("Vivaldi", "local", "vivaldi"),
              ("Chromium", "local", "chromium"), ("Opera", "local", "opera")],
}
FIREFOX = {"windows": ("appdata", "Mozilla/Firefox/Profiles"), "mac": ("local", "Firefox/Profiles"),
           "linux": ("home", ".mozilla/firefox")}
MAX_BYTES_CODIGO = 5_000_000  # se lee como mucho esto del código de cada extensión


def _base(ubic: Ubicaciones, donde: str) -> Path:
    return {"local": ubic.local, "appdata": ubic.appdata, "home": ubic.home}[donde]


def _traducir(texto: str, carpeta: Path, manifest: dict) -> str:
    """Los nombres tipo __MSG_appName__ se buscan en _locales/<idioma>/messages.json."""
    if not isinstance(texto, str) or not texto.startswith("__MSG_"):
        return texto or ""
    clave = texto[6:-2].lower()
    for idioma in (manifest.get("default_locale"), "es", "en", "en_US"):
        if not idioma:
            continue
        mensajes = leer_json(carpeta / "_locales" / idioma / "messages.json") or {}
        for k, v in mensajes.items():
            if k.lower() == clave and isinstance(v, dict):
                return v.get("message", texto)
    return texto


def _webs(manifest: dict) -> set[str]:
    webs = set()
    for campo in ("permissions", "host_permissions", "optional_host_permissions"):
        webs |= {p for p in manifest.get(campo, []) if isinstance(p, str) and ("/" in p or p == "<all_urls>")}
    for script in manifest.get("content_scripts", []):
        webs |= set(script.get("matches", []))
    return webs


def _dominios_espia(carpeta: Path) -> list[str]:
    """¿El código de la extensión menciona dominios de la lista negra?"""
    encontrados, leidos = set(), 0
    for raiz, _, archivos in os.walk(carpeta):
        for nombre in archivos:
            if not nombre.endswith((".js", ".json", ".html", ".mjs")):
                continue
            ruta = Path(raiz) / nombre
            try:
                contenido = ruta.read_bytes()[:MAX_BYTES_CODIGO - leidos].decode("utf-8", errors="ignore")
            except OSError:
                continue
            leidos += len(contenido)
            encontrados |= {d for d in LISTA_NEGRA["dominios"] if d in contenido}
            if leidos >= MAX_BYTES_CODIGO:
                return sorted(encontrados)
    return sorted(encontrados)


def analizar_extension(id_ext: str, nombre: str, descripcion: str, permisos: set[str], webs: set[str],
                       fuera_de_tienda: bool, navegador: str, ruta: str, carpeta_codigo: Path | None = None):
    """Decide la gravedad de una extensión. Devuelve un HallazgoRevisor o None si no es relevante."""
    if id_ext in LISTA_NEGRA["extensiones"]:
        mala = LISTA_NEGRA["extensiones"][id_ext]
        return HallazgoRevisor(
            "extensiones", "CRITICA", f"Extensión maliciosa conocida en {navegador}: {nombre or mala['nombre']}",
            f"{mala['motivo']} Fuente: {mala['fuente']}.",
            "Quítala ya desde la página de extensiones del navegador y cambia las contraseñas de las webs "
            "que usaste con ella. Revisa qué compartiste con la IA mientras estaba instalada.", ruta)

    puntos, explicaciones = 0, []
    for permiso in sorted(permisos):
        if permiso in PERMISOS:
            puntos += PERMISOS[permiso][0]
            explicaciones.append(PERMISOS[permiso][1])
    todas = bool(webs & TODAS_LAS_WEBS) or any(w.startswith(("*://*/", "http://*/", "https://*/")) for w in webs)
    if todas:
        puntos += PUNTOS_TODAS_LAS_WEBS
        explicaciones.insert(0, "puede leer y cambiar todo lo que ves y escribes en TODAS las webs")
    lee_chats_ia = todas or any(dominio in w for w in webs for dominio in WEBS_DE_IA)
    if fuera_de_tienda:
        puntos += PUNTOS_FUERA_DE_TIENDA
        explicaciones.append("se instaló a mano, fuera de la tienda oficial, así que nadie la ha revisado")
    es_ia = bool(PALABRAS_IA.search(f"{nombre} {descripcion}"))
    espias = _dominios_espia(carpeta_codigo) if carpeta_codigo else []

    if espias:
        gravedad = "CRITICA"
        explicaciones.insert(0, f"se conecta desde su código a {', '.join(espias)}, un dominio usado para robar "
                                "chats con IA")
    elif puntos >= 6 or (es_ia and lee_chats_ia and puntos >= 3):
        gravedad = "ALTA"
    elif puntos >= 3:
        gravedad = "MEDIA"
    elif es_ia:
        gravedad = "INFO"
    else:
        return None

    if espias:
        titulo = f"Extensión que manda datos a un dominio espía ({navegador}): {nombre}"
    elif es_ia and lee_chats_ia and gravedad != "INFO":
        titulo = f"Extensión de IA que puede leer tus chats con la IA ({navegador}): {nombre}"
    elif es_ia:
        titulo = f"Extensión de IA ({navegador}): {nombre}"
    else:
        titulo = f"Extensión con permisos muy amplios ({navegador}): {nombre}"
    detalle = ("Esta extensión " + "; ".join(explicaciones) + ".") if explicaciones else "No pide permisos peligrosos."
    recomendacion = ("Si no la usas, quítala. Si la usas, comprueba quién la publica, cuántas reseñas tiene y si de "
                     "verdad necesita esos permisos. Mejor aún: limita su acceso a 'al hacer clic' en los ajustes "
                     "de la extensión." if gravedad != "INFO" else "Nada grave. Revisa de vez en cuando sus permisos.")
    return HallazgoRevisor("extensiones", gravedad, titulo, detalle, recomendacion, ruta)


def _chromium(ubic: Ubicaciones):
    for navegador, donde, relativo in NAVEGADORES_CHROMIUM[ubic.sistema]:
        datos = _base(ubic, donde) / relativo
        if not datos.is_dir():
            continue
        # Perfiles: Default, Profile 1, Profile 2... (Opera guarda las extensiones en la raíz)
        perfiles = [p for p in datos.iterdir() if p.is_dir() and (p / "Extensions").is_dir()]
        if (datos / "Extensions").is_dir():
            perfiles.append(datos)
        for perfil in perfiles:
            ajustes = {}
            for archivo in ("Secure Preferences", "Preferences"):
                prefs = leer_json(perfil / archivo) or {}
                ajustes.update(prefs.get("extensions", {}).get("settings", {}))
            for carpeta_ext in (perfil / "Extensions").iterdir():
                versiones = sorted(v for v in carpeta_ext.iterdir() if (v / "manifest.json").is_file()) \
                    if carpeta_ext.is_dir() else []
                if not versiones:
                    continue
                version = versiones[-1]
                manifest = leer_json(version / "manifest.json") or {}
                ajuste = ajustes.get(carpeta_ext.name, {})
                # location 4 = descomprimida a mano; from_webstore False = no viene de la tienda
                fuera = ajuste.get("location") == 4 or ajuste.get("from_webstore") is False
                permisos = {p for p in manifest.get("permissions", []) + manifest.get("optional_permissions", [])
                            if isinstance(p, str)}
                yield (carpeta_ext.name, _traducir(manifest.get("name", ""), version, manifest),
                       _traducir(manifest.get("description", ""), version, manifest), permisos, _webs(manifest),
                       fuera, f"{navegador} ({perfil.name})", str(version), version)


def _firefox(ubic: Ubicaciones):
    donde, relativo = FIREFOX[ubic.sistema]
    carpeta = _base(ubic, donde) / relativo
    if not carpeta.is_dir():
        return
    for perfil in carpeta.iterdir():
        datos = leer_json(perfil / "extensions.json") if perfil.is_dir() else None
        for addon in (datos or {}).get("addons", []):
            if addon.get("type") != "extension" or str(addon.get("location", "")).startswith(("app-system", "app-builtin")):
                continue
            permisos_usuario = addon.get("userPermissions") or {}
            permisos = set(permisos_usuario.get("permissions", []))
            webs = set(permisos_usuario.get("origins", []))
            locale = addon.get("defaultLocale") or {}
            firma = addon.get("signedState")
            fuera = isinstance(firma, int) and firma <= 0  # sin firmar: no viene de la tienda de Mozilla
            yield (addon.get("id", ""), locale.get("name", addon.get("id", "")), locale.get("description", ""),
                   permisos, webs, fuera, f"Firefox ({perfil.name})", str(perfil / "extensions.json"), None)


def revisar_extensiones(ubic: Ubicaciones) -> tuple[list[HallazgoRevisor], dict]:
    hallazgos, resumen = [], {"extensiones_revisadas": 0, "navegadores": set()}
    for datos in [*_chromium(ubic), *_firefox(ubic)]:
        resumen["extensiones_revisadas"] += 1
        resumen["navegadores"].add(datos[6].split(" (")[0])
        h = analizar_extension(*datos[:8], carpeta_codigo=datos[8])
        if h:
            hallazgos.append(h)
    resumen["navegadores"] = sorted(resumen["navegadores"])
    return hallazgos, resumen
