"""Servicio local para la extensión del navegador (`python -m guardian servicio`).

La extensión del navegador no puede ejecutar Python, así que le pide el trabajo
a este pequeño servidor que corre en tu PC:

  extensión (en chatgpt.com, claude.ai, gemini...)  ->  http://127.0.0.1:8788  ->  escudo, aduana, verificador
                                                     <-  texto ya tapado

    POST /v1/guardian/proteger   {"texto": ...}  -> tapa los datos (y pasa la aduana si es un texto largo)
    POST /v1/guardian/restaurar  {"texto": ...}  -> vuelve a poner tus datos (nunca dentro de enlaces)
                                                    y revisa la respuesta con el verificador
    POST /v1/guardian/mejorar    {"texto": ...}  -> dos versiones mejores de tu pregunta (ya con los datos tapados)
    POST /v1/guardian/nueva                      -> vacía la bóveda
    GET  /v1/guardian/actividad                  -> lo que ha hecho esta semana (del registro, sin datos)
    GET  /salud                                  -> ¿está encendido?

La bóveda (qué dato hay detrás de cada [DNI_1]) vive solo en la memoria de este
proceso: es la misma para todas las pestañas, así el mismo DNI tiene siempre el
mismo marcador, y desaparece al cerrar el servicio.

Seguridad: solo escucha en 127.0.0.1, comprueba la cabecera Host (DNS rebinding),
rechaza a las páginas web (cabecera Origin que no es de una extensión) y exige una
clave. La clave se crea al azar la primera vez y se guarda en tu carpeta de
usuario (~/.guardian/servicio.json) para pegarla una sola vez en la extensión.
"""

import json
import os
import secrets
import stat
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from . import __version__
from .actividad import leer_registro
from .aduana import Aduana
from .escudo import Boveda, Escudo
from .mejorador import Mejorador
from .registro import Registro
from .terminal import resumen
from .verificador import Verificador, neutralizar_imagenes

PUERTO = 8788
MAX_CUERPO = 1 * 2**20  # 1 MB: lo que se pega en un chat
LARGO_DOCUMENTO = 400  # a partir de aquí, lo pegado se trata como un documento y pasa por la aduana
MIN_PEGADO = 80  # lo pegado más largo que esto se recuerda para buscar ecos de trampas en la respuesta
MAX_PEGADOS = 5
HOSTS_LOCALES = {"127.0.0.1", "localhost", "::1"}
ORIGENES_EXTENSION = ("chrome-extension://", "moz-extension://", "safari-web-extension://")
ARCHIVO_CLAVE = Path.home() / ".guardian" / "servicio.json"


def clave_guardada(archivo: Path = ARCHIVO_CLAVE) -> str:
    """Lee la clave del servicio o crea una nueva (32 caracteres al azar) y la guarda solo para tu usuario."""
    try:
        clave = json.loads(archivo.read_text(encoding="utf-8")).get("clave", "")
        if len(clave) >= 16:
            return clave
    except (OSError, ValueError):
        pass
    clave = secrets.token_urlsafe(24)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps({"clave": clave}), encoding="utf-8")
    try:
        os.chmod(archivo, stat.S_IRUSR | stat.S_IWUSR)  # en Windows solo quita el "solo lectura"
    except OSError:
        pass
    return clave


class ServicioGuardian:
    """La lógica, separada del servidor HTTP para poder probarla sin red."""

    def __init__(self, escudo: Optional[Escudo] = None, aduana: Optional[Aduana] = None,
                 verificador: Optional[Verificador] = None, registro: Optional[Registro] = None,
                 cliente_mejorador=None):
        self.escudo = escudo or Escudo()
        self.aduana = aduana or Aduana()
        self.verificador = verificador or Verificador()
        self.registro = registro or Registro()
        self.mejorador = Mejorador(self.escudo, cliente_mejorador, self.aduana)
        self.boveda = Boveda()
        self.pegados: deque[str] = deque(maxlen=MAX_PEGADOS)  # lo último que has pegado, ya tapado
        self._cerrojo = threading.Lock()  # varias pestañas a la vez: la bóveda se toca de una en una

    def proteger(self, texto: str, pegado: bool = False) -> dict:
        """pegado=True: lo has pegado (un correo, un documento...). Se recuerda, ya tapado, para ver luego si la
        respuesta de la IA repite lo que pedía ese texto (el "eco" de una trampa)."""
        informe_aduana, desinfectado = None, texto
        if len(texto) >= LARGO_DOCUMENTO:
            informe = self.aduana.analizar(texto)
            if informe.nivel != "NINGUNO":
                informe_aduana = {
                    "nivel": informe.nivel, "puntuacion": informe.puntuacion,
                    "motivos": list(dict.fromkeys(h.explicacion for h in informe.hallazgos))[:6]}
                desinfectado = Aduana.desinfectar(texto)
        with self._cerrojo:
            resultado = self.escudo.proteger(desinfectado, self.boveda)
            if pegado and len(texto) >= MIN_PEGADO:
                self.pegados.append(resultado.protegido)
        datos = resultado.resumen()
        self.registro.apuntar("extension_proteger", datos_tapados=datos,
                              riesgo_documento=informe_aduana["nivel"] if informe_aduana else None)
        return {"protegido": resultado.protegido, "datos": datos, "resumen": resumen(datos) if datos else "",
                "avisos": resultado.avisos, "aduana": informe_aduana}

    def restaurar(self, texto: str) -> dict:
        with self._cerrojo:
            verificacion = self.verificador.revisar(texto, boveda=self.boveda, leido="\n\n".join(self.pegados))
            restaurado = neutralizar_imagenes(self.escudo.restaurar(texto, self.boveda))
        self.registro.apuntar("extension_restaurar", verificacion=verificacion.nivel,
                              avisos_respuesta=verificacion.resumen())
        return {"texto": restaurado, "nivel": verificacion.nivel,
                "hallazgos": [{"gravedad": h.gravedad, "explicacion": h.explicacion, "fragmento": h.fragmento}
                              for h in verificacion.hallazgos if h.gravedad != "INFO"]}

    def mejorar(self, texto: str) -> dict:
        """Dos versiones mejores de la pregunta, con los datos tapados con la misma bóveda que el resto de la
        conversación (el mismo DNI es siempre [DNI_1])."""
        mejora = self.mejorador.mejorar(texto, self.boveda, self._cerrojo)
        self.registro.apuntar("extension_mejorar", nota=mejora.nota, con_ia=mejora.con_ia)
        return mejora.a_dict()

    def nueva(self) -> dict:
        with self._cerrojo:
            self.boveda = Boveda()
            self.pegados.clear()
        return {"ok": True}

    def actividad(self, dias: int = 7) -> dict:
        """Resumen del registro para el panel de la extensión (solo cuántos y de qué tipo, nunca los datos)."""
        resumen_registro = leer_registro(self.registro.carpeta, dias).a_dict()
        resumen_registro["ultimos"] = resumen_registro["ultimos"][:5]
        return resumen_registro


class _Manejador(BaseHTTPRequestHandler):
    server_version = "GuardianIA"
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):  # sin datos: ruta, código y cuántos datos de cada tipo
        if getattr(self.server, "silencioso", False):
            return
        hecho = getattr(self, "_resumen", "")
        linea = f"[servicio] {self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}"
        print(f"{linea} · {hecho}" if hecho else linea, flush=True)

    def _json(self, codigo: int, datos: dict) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        if codigo >= 400:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        self.wfile.write(cuerpo)

    def _permitido(self) -> bool:
        host = (self.headers.get("Host") or "").strip()
        nombre = host[1:host.index("]")] if host.startswith("[") and "]" in host else host.rsplit(":", 1)[0]
        if nombre.lower() not in HOSTS_LOCALES:
            self._json(403, {"error": "Host no permitido: el servicio solo atiende a este PC."})
            return False
        origen = self.headers.get("Origin")
        if origen and not origen.startswith(ORIGENES_EXTENSION):
            self._json(403, {"error": "Las páginas web no pueden usar el Guardián: solo la extensión."})
            return False
        if not secrets.compare_digest(self.headers.get("Authorization", ""), f"Bearer {self.server.clave}"):
            self._json(401, {"error": "Falta la clave del servicio o no es correcta. Cópiala en las opciones "
                                      "de la extensión."})
            return False
        return True

    def do_OPTIONS(self):  # sin CORS: la extensión llama desde su propio contexto, no hace falta
        self._json(405, {"error": "No permitido"})

    def do_GET(self):
        self._resumen = ""
        ruta = urlparse(self.path).path.rstrip("/")
        if ruta not in ("", "/salud", "/v1/guardian/actividad"):
            self._json(404, {"error": "No existe"})
            return
        if not self._permitido():
            return
        if ruta == "/v1/guardian/actividad":
            self._resumen = "actividad de la semana"
            self._json(200, self.server.servicio.actividad())
            return
        self._json(200, {"ok": True, "guardian": True, "version": __version__,
                         "ia_local": self.server.servicio.escudo.detector_ia is not None})

    def do_POST(self):
        self._resumen = ""
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = -1
        if not 0 <= largo <= MAX_CUERPO:
            self._json(413, {"error": "Demasiado texto de una vez."})
            return
        crudo = self.rfile.read(largo) if largo else b""
        if not self._permitido():
            return
        ruta = urlparse(self.path).path.rstrip("/")
        try:
            cuerpo = json.loads(crudo or b"{}")
            if not isinstance(cuerpo, dict):
                raise ValueError("no es un objeto JSON")
            texto = cuerpo.get("texto")
            if ruta != "/v1/guardian/nueva" and not isinstance(texto, str):
                raise ValueError("falta 'texto'")
        except ValueError as e:
            self._json(400, {"error": f"JSON no válido: {e}"})
            return
        servicio = self.server.servicio
        if ruta == "/v1/guardian/proteger":
            respuesta = servicio.proteger(texto, pegado=cuerpo.get("pegado") is True)
            partes = [f"tapados: {respuesta['resumen']}" if respuesta["datos"] else "nada que tapar"]
            if respuesta["aduana"]:
                partes.append(f"texto pegado con riesgo {respuesta['aduana']['nivel']}")
            self._resumen = " · ".join(partes)
        elif ruta == "/v1/guardian/restaurar":
            respuesta = servicio.restaurar(texto)
            self._resumen = f"respuesta revisada: {respuesta['nivel']}"
        elif ruta == "/v1/guardian/mejorar":
            respuesta = servicio.mejorar(texto)
            self._resumen = f"pregunta mejorada: nota {respuesta['nota']}/100"
        elif ruta == "/v1/guardian/nueva":
            respuesta = servicio.nueva()
            self._resumen = "bóveda vaciada"
        else:
            self._json(404, {"error": f"No existe {ruta}"})
            return
        self._json(200, respuesta)


class ServidorServicio(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, servicio: ServicioGuardian, puerto: int = PUERTO, clave: Optional[str] = None,
                 silencioso: bool = False):
        super().__init__(("127.0.0.1", puerto), _Manejador)  # nunca 0.0.0.0: solo este PC
        self.servicio, self.clave, self.silencioso = servicio, clave or clave_guardada(), silencioso
        self.arranque = time.time()
