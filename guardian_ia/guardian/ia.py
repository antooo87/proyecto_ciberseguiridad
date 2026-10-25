"""Conexión con la IA: local (Ollama) o en la nube.

Todo pasa por aquí, así que es fácil cambiar de modelo o simular la IA en los
tests sin tener Ollama encendido.

Proveedores:
  - "ollama"        Ollama en tu PC (lo normal: nada sale del ordenador).
  - "ollama-cloud"  Modelos grandes de Ollama en sus servidores (https://ollama.com),
                    con una clave en la variable OLLAMA_API_KEY.
  - "openai"        Cualquier servidor que hable "como OpenAI": LM Studio, llama.cpp,
                    vLLM, Groq, OpenRouter, OpenAI... La clave va en GUARDIAN_API_KEY.

Regla de seguridad: las piezas que ven los datos SIN tapar (el detector del
escudo y el juez de la aduana) solo pueden usar una IA local. La IA de la nube
solo recibe la versión con marcadores. Cada cliente dice si es local con `es_local`.
"""

import ipaddress
import json
import os
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
import ollama

from . import config


class ErrorIA(Exception):
    """La IA no está disponible o ha fallado."""


def es_direccion_local(url: str) -> bool:
    host = urlparse(url if "//" in url else f"http://{url}").hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class ClienteIA:
    """Ollama, en tu PC o en ollama.com."""
    proveedor = "ollama"

    def __init__(self, modelo: Optional[str] = None, host: Optional[str] = None, api_key: Optional[str] = None):
        self.modelo = modelo or config.MODELO
        self.host = host or config.OLLAMA_HOST
        cabeceras = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._cliente = ollama.Client(host=self.host, headers=cabeceras)

    @property
    def es_local(self) -> bool:
        return es_direccion_local(self.host)

    def chat(self, mensajes: list[dict], formato: Any = None, temperatura: Optional[float] = None) -> str:
        """Manda la conversación al modelo y devuelve solo el texto de la respuesta."""
        opciones = {"temperature": temperatura} if temperatura is not None else None
        try:
            respuesta = self._cliente.chat(
                model=self.modelo, messages=mensajes, format=formato,
                options=opciones, think=False)
        except ollama.ResponseError as e:
            # Algunos modelos no admiten la opción "think": se reintenta sin ella
            if "think" not in str(e).lower():
                raise ErrorIA(f"Ollama respondió con un error: {e}") from e
            try:
                respuesta = self._cliente.chat(
                    model=self.modelo, messages=mensajes, format=formato, options=opciones)
            except Exception as e2:
                raise ErrorIA(f"Ollama respondió con un error: {e2}") from e2
        except Exception as e:  # Ollama apagado, sin red local, etc.
            raise ErrorIA(
                "No puedo hablar con Ollama. ¿Está abierto (icono de la llama junto al reloj)? "
                f"Detalle: {e}") from e
        return respuesta.message.content or ""

    def estado(self) -> dict:
        """Comprueba que Ollama responde y que el modelo está descargado."""
        try:
            modelos = [m.model for m in self._cliente.list().models]
        except Exception as e:
            return {"ok": False, "detalle": f"Ollama no responde: {e}"}
        if self.modelo not in modelos:
            return {"ok": False, "detalle": f"Falta el modelo {self.modelo}. "
                    f"Descárgalo con: ollama pull {self.modelo}", "modelos": modelos}
        donde = "en tu PC" if self.es_local else f"en {urlparse(self.host).hostname} (fuera de tu PC)"
        return {"ok": True, "detalle": f"Ollama responde {donde} y {self.modelo} está listo", "modelos": modelos}


def _estricto(esquema):
    """OpenAI exige additionalProperties=false en cada objeto del esquema."""
    if isinstance(esquema, dict):
        esquema = {k: _estricto(v) for k, v in esquema.items()}
        if esquema.get("type") == "object":
            esquema.setdefault("additionalProperties", False)
        return esquema
    if isinstance(esquema, list):
        return [_estricto(x) for x in esquema]
    return esquema


class ClienteOpenAI:
    """Cualquier API compatible con OpenAI (/v1/chat/completions)."""
    proveedor = "openai"

    def __init__(self, modelo: str, url_base: str, api_key: Optional[str] = None, extra: Optional[dict] = None,
                 espera: float = 300, transporte=None):
        self.modelo = modelo
        self.host = url_base.rstrip("/")
        self.extra = extra or {}
        cabeceras = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.Client(base_url=self.host, headers=cabeceras, timeout=espera, transport=transporte)

    @property
    def es_local(self) -> bool:
        return es_direccion_local(self.host)

    def chat(self, mensajes: list[dict], formato: Any = None, temperatura: Optional[float] = None) -> str:
        cuerpo = {"model": self.modelo, "messages": mensajes, **self.extra}
        if temperatura is not None:
            cuerpo["temperature"] = temperatura
        if formato:
            cuerpo["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "respuesta", "schema": _estricto(formato), "strict": True}}
        try:
            r = self._http.post("/chat/completions", json=cuerpo)
        except httpx.HTTPError as e:
            raise ErrorIA(f"No puedo hablar con {self.host}: {e}") from e
        if r.status_code != 200:
            raise ErrorIA(f"{self.host} respondió {r.status_code}: {r.text[:200]}")
        try:
            return r.json()["choices"][0]["message"].get("content") or ""
        except (ValueError, KeyError, IndexError) as e:
            raise ErrorIA(f"Respuesta rara de {self.host}: {r.text[:200]}") from e

    def estado(self) -> dict:
        try:
            r = self._http.get("/models")
            modelos = [m["id"] for m in r.json().get("data", [])] if r.status_code == 200 else []
        except (httpx.HTTPError, ValueError) as e:
            return {"ok": False, "detalle": f"{self.host} no responde: {e}"}
        if modelos and self.modelo not in modelos:
            return {"ok": False, "detalle": f"{self.host} no tiene el modelo {self.modelo}", "modelos": modelos}
        donde = "en tu PC" if self.es_local else "FUERA de tu PC: solo recibirá datos tapados"
        return {"ok": True, "detalle": f"{self.host} responde ({donde}) con {self.modelo}", "modelos": modelos}


def crear_cliente(proveedor: Optional[str] = None, modelo: Optional[str] = None, url: Optional[str] = None):
    """Crea el cliente de la IA de destino según la configuración (o lo que se pase)."""
    proveedor = (proveedor or config.PROVEEDOR).lower()
    if proveedor == "ollama":
        return ClienteIA(modelo, url)
    if proveedor == "ollama-cloud":
        clave = os.environ.get("OLLAMA_API_KEY")
        if not clave:
            raise ErrorIA("Para usar Ollama en la nube crea una clave en ollama.com y guárdala en OLLAMA_API_KEY.")
        return ClienteIA(modelo or config.MODELO_NUBE, url or "https://ollama.com", api_key=clave)
    if proveedor == "openai":
        extra = json.loads(os.environ["GUARDIAN_OPENAI_EXTRA"]) if os.environ.get("GUARDIAN_OPENAI_EXTRA") else None
        return ClienteOpenAI(modelo or config.MODELO, url or config.URL_OPENAI,
                             os.environ.get("GUARDIAN_API_KEY"), extra)
    raise ErrorIA(f"Proveedor desconocido: {proveedor}. Usa ollama, ollama-cloud u openai.")
