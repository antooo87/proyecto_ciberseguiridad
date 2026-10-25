"""Revisa la RESPUESTA de la IA antes de enseñártela (OWASP LLM05: manejo inseguro de la salida).

Una IA engañada por un documento, o que simplemente se equivoca, puede:
  - darte un comando que borra tu disco o descarga un virus para que lo pegues
    en PowerShell (la técnica "ClickFix", muy usada en 2025);
  - meter tus datos en un enlace o en una imagen para sacarlos fuera;
  - mandarte a una web que imita a tu banco o un enlace acortado;
  - pedirte la contraseña o el código SMS;
  - inventarse un DNI, un IBAN o una clave que tú no le diste.
"""

import re
from dataclasses import dataclass

from ..aduana.aduana import mensajes_en_etiquetas
from ..escudo import DetectorRegex, Escudo
from ..escudo.escudo import MARCADOR

COMANDOS = [
    # (nombre, patrón, gravedad, explicación)
    ("descarga_y_ejecuta", r"(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b"
     r"|\b(iwr|irm|invoke-webrequest|invoke-restmethod)\b[^\n]*\|\s*(iex|invoke-expression)\b"
     r"|\biex\s*\(?\s*\(?\s*new-object\s+(system\.)?net\.webclient\)?\s*\.\s*downloadstring"
     r"|\b(mshta|rundll32|regsvr32)\b[^\n]*https?://|\bcertutil\b[^\n]*-urlcache|\bbitsadmin\b[^\n]*/transfer"
     r"|\bmsiexec\b[^\n]*/i\s*https?://",
     "PELIGRO", "descarga un programa de Internet y lo ejecuta sin que lo veas: es como se instalan muchos virus"),
    ("comando_ofuscado", r"\bpowershell(\.exe)?\b[^\n]*\s-(e|ec|enc|encodedcommand)\s+[A-Za-z0-9+/=]{16,}",
     "PELIGRO", "ejecuta un comando escondido en base64 para que no se vea lo que hace"),
    ("borra_todo", r"\brm\s+-(rf|fr|r\s+-f|f\s+-r)\s+(--no-preserve-root\s+)?(/|~|\*|\$HOME)(\s|$)"
     r"|\b(rd|rmdir)\s+/s\s+/q\s+[a-z]:\\?(\s|$)|\bdel\s+(/[a-z]\s+)*/s\b[^\n]*[a-z]:\\\*?"
     r"|\bformat\s+[a-z]:|\bmkfs(\.\w+)?\s+/dev/|\bdd\s+if=[^\n]*of=/dev/(sd|nvme|hd)"
     r"|remove-item\b[^\n]*-recurse[^\n]*(c:\\|~|\$home)|:\(\)\s*\{\s*:\|:&\s*\};:",
     "PELIGRO", "borra o destruye discos o carpetas enteras"),
    ("desactiva_seguridad", r"set-mppreference\b[^\n]*-disable\w*\s+\$?true|add-mppreference\b[^\n]*-exclusion"
     r"|netsh\s+advfirewall\s+set\s+\w+\s+state\s+off|\bsc\s+(stop|config)\s+windefend|\bsetenforce\s+0"
     r"|\bufw\s+disable|\bchmod\s+(-R\s+)?777\s+/(\s|$)",
     "PELIGRO", "desactiva el antivirus, el cortafuegos u otra protección del sistema"),
    ("roba_credenciales", r"\bmimikatz\b|reg\s+save\s+hklm\\(sam|system|security)|\.ssh/id_(rsa|ed25519)\b[^\n]*(curl|nc|scp)"
     r"|(curl|wget|invoke-webrequest)\b[^\n]*(\.ssh|\.aws/credentials|login data|cookies)",
     "PELIGRO", "copia contraseñas, claves o cookies del sistema y puede mandarlas fuera"),
    ("persistencia", r"reg\s+add\s+[^\n]*\\currentversion\\run\b|\bschtasks\s+/create\b|\bcrontab\s+-[^l\s]*\s"
     r"|new-scheduledtask|\bstartup\\\b",
     "AVISO", "hace que un programa se arranque solo cada vez que enciendes el PC"),
    ("superusuario", r"\bsudo\s+(su|-i|-s)\b|\bset-executionpolicy\s+(unrestricted|bypass)\b",
     "AVISO", "quita protecciones o da permisos de administrador a todo lo que venga después"),
]
COMANDOS = [(n, re.compile(p, re.IGNORECASE), g, e) for n, p, g, e in COMANDOS]

PIDE_SECRETOS = re.compile(
    r"\b(dame|dime|env[ií]ame|escr[ií]beme|introduce|fac[ií]litame|comp[aá]rteme|p[aá]same|confirma|indica|"
    r"give me|send me|enter|provide|share)\s+(tu|tus|la|el|your)\s+(\w+\s+)?"
    r"(contrase[ñn]a|clave|pin|c[oó]digo (de verificaci[oó]n|sms|de seguridad)|cvv|cvc|n[uú]mero de (la )?tarjeta|"
    r"credenciales|password|verification code|card number|seed phrase|frase semilla)", re.IGNORECASE)
IMAGEN_MD = re.compile(r"!\[[^\]]*\]\(\s*<?(https?://[^)\s>]+)>?[^)]*\)|<img\b[^>]*\bsrc\s*=\s*[\"']?(https?://[^\"'\s>]+)",
                       re.IGNORECASE)
TIPOS_SECRETOS = {"DNI", "NIE", "IBAN", "TARJETA", "CLAVE_API", "JWT", "CLAVE_PRIVADA", "CONTRASENA"}
DETECTOR = DetectorRegex()


@dataclass
class HallazgoVerificacion:
    tipo: str
    gravedad: str  # PELIGRO, AVISO, INFO
    explicacion: str
    fragmento: str = ""


def revisar_salida(respuesta: str, boveda=None) -> list[HallazgoVerificacion]:
    h = []
    for nombre, patron, gravedad, explicacion in COMANDOS:
        for m in patron.finditer(respuesta):
            h.append(HallazgoVerificacion(nombre, gravedad, f"La respuesta trae un comando que {explicacion}. "
                                          "No lo copies en la terminal sin entenderlo.", m.group(0)[:160]))
    robados = Escudo.marcadores_en_enlaces(respuesta)
    if robados:
        h.append(HallazgoVerificacion(
            "exfiltracion", "PELIGRO",
            f"La IA ha metido tus datos ({', '.join(sorted(set(robados)))}) dentro de un enlace o una imagen. "
            "Si se restaurasen, viajarían a esa web en cuanto se mostrara: es la técnica para robar datos con "
            "prompt injection. El Guardián NO los ha restaurado ahí.", ", ".join(sorted(set(robados)))))
    for m in IMAGEN_MD.finditer(respuesta):
        url = m.group(1) or m.group(2)
        if "?" in url or "=" in url:
            h.append(HallazgoVerificacion(
                "imagen_con_datos", "AVISO", "La respuesta incluye una imagen de otra web con datos en la "
                "dirección: al mostrarla, tu navegador le enviaría esos datos. Se ha bloqueado.", url[:160]))
    for _, oculto in mensajes_en_etiquetas(respuesta):
        h.append(HallazgoVerificacion(
            "texto_invisible", "AVISO", "La respuesta trae un mensaje escrito con letras invisibles (etiquetas "
            "Unicode): tú no lo ves, pero si lo copias, otra IA o programa sí lo leería. Suele ser señal de que la IA "
            "ha sido manipulada.", oculto[:160]))
    for m in PIDE_SECRETOS.finditer(respuesta):
        h.append(HallazgoVerificacion(
            "pide_secretos", "AVISO", "La IA te pide un dato secreto. Ningún servicio legítimo te lo pide por "
            "un chat: puede venir de un documento con prompt injection.", m.group(0)))
    if boveda is not None:
        inventados = sorted({m.group(0) for m in MARCADOR.finditer(respuesta)
                             if boveda.valor_de(f"[{m.group(1).upper()}]") is None})
        if inventados:
            h.append(HallazgoVerificacion(
                "marcador_inventado", "INFO", f"La IA ha usado marcadores que no existen ({', '.join(inventados)}): "
                "se dejan tal cual porque no corresponden a ningún dato tuyo.", ", ".join(inventados)))
    for dato in DETECTOR.detectar(respuesta):
        if dato.tipo in TIPOS_SECRETOS and not MARCADOR.search(dato.valor):
            h.append(HallazgoVerificacion(
                "dato_sensible_nuevo", "AVISO", f"La IA ha escrito un {dato.tipo} que tú no le diste (los tuyos "
                "le llegan tapados). Puede ser inventado o venir de sus datos de entrenamiento: no lo uses "
                "sin comprobarlo.", dato.valor))
    return h


def neutralizar_imagenes(texto: str) -> str:
    """Cambia las imágenes de webs externas por un aviso, para que el navegador no las cargue solo."""
    def cambiar(m):
        url = m.group(1) or m.group(2)
        dominio = re.sub(r"^https?://([^/?#]+).*$", r"\1", url)
        return f"[imagen bloqueada por el Guardián: {dominio}]"
    return IMAGEN_MD.sub(cambiar, texto)
