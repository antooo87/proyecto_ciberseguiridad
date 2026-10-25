"""Revisa los enlaces y las referencias que da la IA.

Los modelos de lenguaje se inventan enlaces y artículos con mucha facilidad:
la dirección "suena" bien pero no existe. Y si un documento les ha metido una
orden, pueden recomendarte una web falsa que imita a tu banco.

Sin conexión (siempre):
  - dominios que imitan a marcas conocidas (bbva-seguridad.com no es BBVA),
  - letras raras para imitar otro dominio (punycode, xn--),
  - enlaces a una IP, acortadores que esconden el destino,
  - dominios de la lista negra.
Con conexión (solo si lo activas, porque al comprobar un enlace la web sabe que
alguien lo ha mirado):
  - si el dominio existe (DNS),
  - si la página existe (código 404 = inventada),
  - si un DOI de un artículo científico existe en doi.org.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

from ..revisor.extensiones import LISTA_NEGRA
from .salida import HallazgoVerificacion

URL = re.compile(r"https?://[^\s<>\"'`)\]]+", re.IGNORECASE)
DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+[A-Za-z0-9]")
ACORTADORES = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "is.gd", "ow.ly", "rebrand.ly", "shorturl.at",
               "tiny.cc", "rb.gy", "t.ly", "s.id"}
MARCAS = {  # marca: dominios oficiales
    "paypal": ("paypal.com", "paypal.es", "paypal.me"), "bbva": ("bbva.es", "bbva.com"),
    "santander": ("bancosantander.es", "santander.com", "santander.es"), "caixabank": ("caixabank.es", "caixabank.com"),
    "openai": ("openai.com",), "chatgpt": ("chatgpt.com", "openai.com"),
    "microsoft": ("microsoft.com", "live.com", "microsoftonline.com", "office.com", "azure.com", "windows.net"),
    "google": ("google.com", "google.es", "googleusercontent.com", "googleapis.com", "gstatic.com", "youtube.com"),
    "apple": ("apple.com", "icloud.com"), "amazon": ("amazon.es", "amazon.com", "amazonaws.com"),
    "netflix": ("netflix.com",), "agenciatributaria": ("agenciatributaria.gob.es", "agenciatributaria.es"),
    "correos": ("correos.es", "correos.com"), "anthropic": ("anthropic.com", "claude.ai"),
    "github": ("github.com", "githubusercontent.com", "github.io"), "binance": ("binance.com",),
    "whatsapp": ("whatsapp.com", "whatsapp.net"), "instagram": ("instagram.com",), "facebook": ("facebook.com", "fb.com"),
}


def _distancia(a: str, b: str) -> int:
    """Cuántas letras hay que cambiar, quitar o poner para pasar de a a b (Levenshtein)."""
    fila = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        anterior, fila[0] = fila[0], i
        for j, cb in enumerate(b, 1):
            anterior, fila[j] = fila[j], min(fila[j] + 1, fila[j - 1] + 1, anterior + (ca != cb))
    return fila[-1]


def imita_a(host: str) -> str | None:
    """Devuelve la marca que el dominio intenta imitar, o None."""
    base = _dominio_base(host)
    trozos = re.split(r"[.-]", host.lower())
    etiqueta = base.split(".")[0]
    for marca, oficiales in MARCAS.items():
        if base in oficiales or any(host.endswith("." + o) for o in oficiales):
            return None
        pegado = "".join(trozos[:-1])
        if marca in trozos or (len(marca) >= 8 and marca in pegado) or (len(marca) >= 5 and _distancia(etiqueta, marca) == 1):
            return marca
    return None


def _dominio_base(host: str) -> str:
    partes = host.lower().strip(".").split(".")
    if len(partes) >= 3 and partes[-2] in ("gob", "com", "org", "co", "gov", "edu"):
        return ".".join(partes[-3:])
    return ".".join(partes[-2:])


def revisar_enlaces(respuesta: str, contexto: str = "", comprobar: bool = False,
                    espera: float = 4.0) -> list[HallazgoVerificacion]:
    """`contexto` es lo que mandó el usuario: los enlaces que ya estaban ahí no son invento de la IA."""
    h = []
    urls = sorted({u.rstrip(".,;:!?") for u in URL.findall(respuesta)})
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            continue
        base = _dominio_base(host)
        nuevo = url not in contexto
        if base in LISTA_NEGRA["dominios"] or host in LISTA_NEGRA["dominios"]:
            h.append(HallazgoVerificacion("dominio_malicioso", "PELIGRO",
                                          f"{host} es un dominio malicioso conocido: {LISTA_NEGRA['dominios'].get(base) or ''}",
                                          url))
            continue
        if "xn--" in host:
            h.append(HallazgoVerificacion("dominio_disfrazado", "PELIGRO",
                                          f"{host} usa letras de otros alfabetos para parecerse a otra web "
                                          "(ataque homógrafo).", url))
        try:
            ipaddress.ip_address(host)
            h.append(HallazgoVerificacion("enlace_a_ip", "AVISO", "El enlace va a una dirección IP en vez de a una "
                                          "web con nombre: es raro en webs legítimas.", url))
        except ValueError:
            pass
        if base in ACORTADORES:
            h.append(HallazgoVerificacion("acortador", "AVISO", "Es un enlace acortado: no se ve adónde lleva.", url))
        marca = imita_a(host)
        if marca:
            h.append(HallazgoVerificacion(
                "imita_marca", "PELIGRO", f"El enlace parece de {marca.upper()} pero NO es su web oficial "
                f"({', '.join(MARCAS[marca])}). Es la técnica típica del phishing.", url))
        if comprobar and nuevo:
            h += _comprobar_url(url, host, espera)
    if comprobar:
        for doi in sorted(set(DOI.findall(respuesta))):
            if doi not in contexto:
                h += _comprobar_doi(doi, espera)
    return h


def _comprobar_url(url: str, host: str, espera: float) -> list[HallazgoVerificacion]:
    try:
        socket.getaddrinfo(host, 443)
    except socket.gaierror:
        return [HallazgoVerificacion("dominio_inexistente", "AVISO", f"El dominio {host} no existe: la IA se ha "
                                     "inventado este enlace.", url)]
    try:
        r = httpx.head(url, follow_redirects=True, timeout=espera)
        if r.status_code in (405, 403):  # algunas webs no aceptan HEAD
            r = httpx.get(url, follow_redirects=True, timeout=espera)
    except httpx.HTTPError:
        return [HallazgoVerificacion("enlace_no_responde", "INFO", "No he podido abrir el enlace para comprobarlo.", url)]
    if r.status_code == 404 or r.status_code == 410:
        return [HallazgoVerificacion("pagina_inexistente", "AVISO", "La web existe pero esa página no (error 404): "
                                     "probablemente la IA se ha inventado la dirección.", url)]
    return []


def _comprobar_doi(doi: str, espera: float) -> list[HallazgoVerificacion]:
    try:
        r = httpx.get(f"https://doi.org/api/handles/{doi}", timeout=espera)
    except httpx.HTTPError:
        return []
    if r.status_code == 404 or (r.status_code == 200 and r.json().get("responseCode") == 100):
        return [HallazgoVerificacion("doi_inexistente", "AVISO", f"El artículo con DOI {doi} no existe en doi.org: "
                                     "la referencia es inventada.", doi)]
    return []
