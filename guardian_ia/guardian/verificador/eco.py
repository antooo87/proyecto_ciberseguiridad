"""Eco de la trampa: la IA ya no puede actuar, pero intenta que actúes TÚ.

En las pruebas con agentes, el Guardián bloqueaba el correo al atacante, pero la IA repetía la trampa en su
respuesta ("para aplicar los descuentos es necesario verificar la cuenta") en 8 o 9 de cada 10 intentos.
Es la "persuasión tras la inyección": si la IA no puede mandar tus datos, que los mandes tú.

Este módulo busca en la respuesta frases que te empujan a hacer algo arriesgado (verificar tu cuenta, mandar
datos, pagar, instalar algo, llamar, entrar en una web) y mira de dónde sale ese empujón:
  - si lleva un destino (web, correo, teléfono, cuenta) que estaba en lo que ha leído la IA y no en lo que
    tú escribiste, la orden viene de fuera: PELIGRO cuando es algo grave (claves, datos, pagos, instalar);
  - si lo que leyó la IA pedía lo mismo y tú no lo pediste, es un eco de la trampa: AVISO.
No cuenta cuando la IA lo cuenta como advertencia ("es phishing, no lo hagas") ni cuando tú lo pediste.
"""

import re
import unicodedata

from .salida import HallazgoVerificacion

_OBJETO_CLAVES = (r"cuenta|identidad|datos|dni|nie|pasaporte|contrasena|clave|tarjeta|acceso|perfil|usuario|"
                  r"credenciales|pin|account|identity|password|details|card|login")
_OBJETO_DATOS = (r"dni|nie|pasaporte|datos|contrasena|clave|codigo|tarjeta|cvv|iban|cuenta bancaria|documentacion|"
                 r"copia|credenciales|nomina|nombre completo|direccion|password|code|card|details")
_DESTINO_WEB = r"https?://|www\.|\bweb\b|pagina|enlace|link|sitio|tienda|portal|\bapp\b|aplicacion|\[url"

# Hueco entre el verbo y lo que pide, dentro de la misma frase. Un punto pegado a algo ("tienda.example",
# "n.º") no corta la frase; un punto seguido de espacio, sí.
_HUECO = r"(?:[^.\n]|\.(?=\S))"

# categoría: (patrón sobre el texto en minúsculas y sin tildes, qué te pide, si es grave). {H} es el hueco.
_ACCIONES = {
    "claves": (
        r"\b(?:verifi[cq]|confirm|valid|actuali[zc]|reactiv|desbloque|restable[cz]|recuper|verify|validat|updat|unlock|"
        r"restor)\w*\b(?!\s+que\b){H}?\b(?:" + _OBJETO_CLAVES + r")\b"
        r"|\bproceso de verificacion\b|\bcompletar la verificacion\b"
        r"|\b(?:inicia|inicie|inicies|iniciar|abre|abra|abrir)\s+(?:la\s+|una\s+)?sesion\b|\blog\s?in\b|\bsign\s?in\b"
        r"|\b(?:introdu[cz]|escrib|teclea|enter\b|type\b)\w*{H}?\b(?:contrasena|clave|pin|codigo|password|code)\b",
        "verifiques tu cuenta o escribas tus claves", True),
    "datos": (
        r"(?:\b(?:envi|mand|facilit|proporcion|compart|remit|adjunt|send|provid|shar|submit)\w*|\bme das|\bdame|\bdime|"
        r"\bpasame|\bindicame|\bnecesito|\bgive me|\btell me)\b{H}?\b(?:" + _OBJETO_DATOS + r")\b",
        "mandes datos personales", True),
    "pago": (
        r"\b(?:paga|pague|pagues|pagar|abona|abone|abones|abonar|transfiere|transfiera|transfieras|transferir|"
        r"transferencia|ingresa|ingrese|ingreses|ingresar|bizum|pay|wire|transfer)\b",
        "hagas un pago o una transferencia", True),
    "instalar": (
        r"\b(?:descarga|descargue|descargues|descargar|instala|instale|instales|instalar|ejecuta|ejecute|ejecutes|"
        r"ejecutar|download|install)\b"
        r"|\b(?:abre|abra|abras|abrir|open)\s+(?:el\s+|este\s+|ese\s+|the\s+)?(?:archivo|adjunto|fichero|file|attachment)\b"
        r"|\b(?:activa|active|actives|activar|habilita|habilite|habilites|habilitar|enable)\s+(?:las\s+|el\s+)?"
        r"(?:macros|contenido|edicion|content)\b",
        "descargues, instales o abras algo", True),
    "contacto": (
        r"\b(?:llama|llame|llames|llamar|contacta|contacte|contactes|contactar|escribe|escriba|escribas|escribir|"
        r"whatsapp|call|contact)\b{H}?(?:\[(?:telefono|email)_\d+\]|@|\+?\d[\d .-]{6,}\d|al numero|"
        r"al telefono|por whatsapp)"
        r"|\b(?:envia|envie|envies|enviar|manda|mande|mandes|mandar|escribe|escriba|escribas|send|write)(?:\b|_)"
        r"{H}?\b(?:correo|email|e-mail|whatsapp)\b",
        "llames o escribas a un contacto", False),
    "web": (
        r"\b(?:visita|visite|visites|visitar|accede|acceda|accedas|acceder|entra|entres|entrar|pulsa|pulse|pulses|"
        r"pulsar|haz clic|haga clic|hagas clic|hacer clic|click|visit|go to|open)\b{H}?(?:" + _DESTINO_WEB + r")",
        "entres en una web", False),
}


def _compilar(hueco: int) -> dict:
    return {c: (re.compile(patron.replace("{H}", f"{_HUECO}{{0,{hueco}}}")), que, grave)
            for c, (patron, que, grave) in _ACCIONES.items()}


ACCIONES = _compilar(40)  # en la respuesta: el verbo y lo que pide, cerca
ACCIONES_LEIDO = _compilar(160)  # en lo leído (una trampa puede ser una frase larga dirigida a la IA)

# La frase te dice que lo hagas (y no solo lo cuenta)
DIRECTIVA = re.compile(
    r"\b(?:verifica|verifique|verifiques|confirma|confirme|confirmes|valida|valide|actualiza|actualice|reactiva|"
    r"desbloquea|restablece|recupera|accede|acceda|accedas|entra|inicia|inicie|introduce|introduzca|haz|haga|pulsa|"
    r"pulse|visita|visite|abre|abra|llama|llame|contacta|contacte|escribe|escriba|envia|envie|envies|manda|mande|"
    r"mandes|facilita|facilite|proporciona|proporcione|comparte|comparta|responde|responda|remite|paga|pague|abona|"
    r"abone|transfiere|transfiera|ingresa|ingrese|descarga|descargue|instala|instale|ejecuta|ejecute|activa|active|"
    r"habilita|habilite|"
    r"te recomiendo|te aconsejo|le recomiendo|le aconsejo|recomendamos|deberias|deberia|debes|debe|tienes que|"
    r"tendras que|es necesario|sera necesario|es imprescindible|es obligatorio|es importante|necesitas|necesitaras|"
    r"hay que|habra que|asegurate|no olvides|recuerda|ten en cuenta|cuanto antes|lo antes posible|por favor|"
    r"se requiere|requiere que|es requisito|se necesita|hace falta|es preciso|necesito que|necesito|si me das|dame|"
    r"pasame|indicame|"
    r"verify|confirm|click|visit|call|contact|send|provide|reply|pay|transfer|download|install|enable|please|"
    r"you should|you must|you need to|make sure)\b")
# La frase es una advertencia o un buen consejo: es lo que debe hacer la IA, no un eco de la trampa
ADVERTENCIA = re.compile(
    r"\b(?:phishing|estafa|fraude|fraudulent\w*|sospechos\w*|engano|timo|trampa|ataque|malicios\w*|no (?:lo |la )?hagas|"
    r"no introduzcas|no pulses|no abras|no envies|no mandes|no facilites|no compartas|no descargues|no instales|"
    r"no llames|no pagues|ten cuidado|cuidado|desconfia|nunca|no es (?:la web |el sitio )?oficial|falso|falsa|"
    r"scam|suspicious|malicious|do not|don't|never)\b")
# Un buen consejo ("hazlo desde la app oficial") solo cuenta si no lleva un destino sacado de lo leído: una trampa
# también dice "entra en nuestra web oficial https://..."
BUEN_CONSEJO = re.compile(r"\b(?:oficial|oficiales|por otro camino|por tu cuenta|official)\b")
YO_HICE = re.compile(r"\b\w+[éí]\b", re.IGNORECASE)
# La IA se ofrece a hacer algo ("¿quieres que te envíe un correo con las ofertas?"): no te empuja a ti
OFRECIMIENTO = re.compile(
    r"\b(?:te gustaria|quieres que|deseas que|prefieres que|necesitas que|puedo|podria|hazmelo saber|dime si|"
    r"avisame|would you like|do you want|shall i|let me know)\b")
URGENCIA = re.compile(
    r"\b(?:urgente|urgentemente|inmediatamente|de inmediato|cuanto antes|lo antes posible|hoy mismo|"
    r"en las proximas \d+ horas|antes de que|sera (?:bloquead|suspendid|cancelad|eliminad)\w*|se bloqueara|"
    r"bloqueo|immediately|urgent|within \d+ hours|will be (?:suspended|locked|closed))\b")
MARCADOR_DATO = re.compile(r"\[(?:DNI|NIE|PASAPORTE|NSS|IBAN|TARJETA|CONTRASENA|FECHA_NACIMIENTO)_\d+\]")
DESTINO = re.compile(r"https?://[^\s<>\"'`)\]]+|\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\[(?:EMAIL|TELEFONO|IBAN|TARJETA)_\d+\]"
                     r"|(?<![\w+])\+?\d[\d .-]{7,}\d(?!\d)")


def _plano(texto: str) -> str:
    """Minúsculas y sin tildes, para que "envíe" y "envie" sean lo mismo."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def _destinos(texto: str) -> set[str]:
    """Webs (sin la parte de después de ?), correos, teléfonos y marcadores de datos que aparecen en el texto."""
    destinos = set()
    for m in DESTINO.finditer(texto):
        valor = m.group(0)
        if valor.lower().startswith("http"):
            valor = re.sub(r"^https?://(www\.)?", "", valor.lower()).split("?", 1)[0].split("#", 1)[0].rstrip("/.,;:")
        elif valor.startswith("["):
            pass  # [EMAIL_1]: con la misma bóveda, el mismo dato tiene siempre el mismo marcador
        elif "@" in valor:
            valor = valor.lower().rstrip(".,;:")
        else:
            valor = re.sub(r"\D", "", valor)[-9:]  # teléfono: las últimas 9 cifras, con o sin +34
        destinos.add(valor)
    return destinos


def frases(texto: str) -> list[str]:
    trozos = re.split(r"(?<=[.!?])\s+|\n+", texto)
    return [t.strip(" \t*-•>#_").strip() for t in trozos if len(t.strip()) > 3]


CAMPO = re.compile(r"^\W*(?:para|to|destinatario|asunto|subject|texto|mensaje|cuerpo|body|cuenta|iban|importe|telefono|"
                   r"correo|email|web|enlace|url)\W*:", re.IGNORECASE)


def bloques(texto: str) -> list[tuple[str, str]]:
    """Cada frase con lo que la completa: si acaba en ":" o la siguen líneas tipo "Para: x@y.com", van juntas.
    Así "envía este correo:" + "Para: verificacion@..." se entiende como una sola petición."""
    trozos = frases(texto)
    resultado = []
    for i, frase in enumerate(trozos):
        extra = []
        for siguiente in trozos[i + 1:i + 6]:
            if frase.endswith(":") and not extra or CAMPO.match(siguiente):
                extra.append(siguiente)
            else:
                break
        resultado.append((frase, " ".join([frase, *extra])))
    return resultado


def revisar_eco(respuesta: str, leido: str, peticion: str = "") -> list[HallazgoVerificacion]:
    """respuesta: lo que contesta la IA. leido: lo que ha leído y no es tuyo (documentos, webs, correos, resultados
    de herramientas). peticion: lo que has escrito tú. Los tres en la misma forma (con o sin marcadores)."""
    if not leido.strip() or not respuesta.strip():
        return []
    leido_plano, peticion_plano = re.sub(r"\s+", " ", _plano(leido)), re.sub(r"\s+", " ", _plano(peticion))
    pedidas = {c for c, (patron, _, _) in ACCIONES.items() if patron.search(peticion_plano)}
    en_lo_leido = {c for c, (patron, _, _) in ACCIONES_LEIDO.items() if patron.search(leido_plano)}
    destinos_leidos = _destinos(leido) - _destinos(peticion)
    hallazgos, vistas = [], set()
    for frase, bloque in bloques(respuesta):
        plano = _plano(frase)
        # "envié", "mandaré", "accedí": lo que la IA dice que hizo o hará, no lo que te pide (se miran con la tilde)
        if not DIRECTIVA.search(_plano(YO_HICE.sub(" ", frase))) or ADVERTENCIA.search(plano):
            continue
        if OFRECIMIENTO.search(plano) and ("?" in frase or re.search(r"hazmelo saber|avisame|let me know", plano)):
            continue
        categorias = [c for c, (patron, _, _) in ACCIONES.items() if patron.search(plano) and c not in pedidas]
        de_alli = sorted(_destinos(bloque) & destinos_leidos)
        if BUEN_CONSEJO.search(plano) and not de_alli:
            continue
        eco = [c for c in categorias if c in en_lo_leido]
        if not categorias or not (de_alli or eco):
            continue
        categoria = (eco or categorias)[0]
        if categoria in vistas:
            continue
        vistas.add(categoria)
        _, que, grave = ACCIONES[categoria]
        if not grave and MARCADOR_DATO.search(bloque):  # "escribe a este correo" con tus datos dentro
            que, grave = "mandes tus datos personales a un contacto", True
        urgente = " y con prisas, como hacen las estafas" if URGENCIA.search(plano) else ""
        if grave and de_alli:
            hallazgos.append(HallazgoVerificacion(
                "eco_de_la_trampa", "PELIGRO",
                f"La IA te pide que {que} ({', '.join(de_alli)}){urgente}, y eso sale de lo que ha leído (una web, "
                "un documento o un correo), no de lo que tú le pediste. Es lo que busca una trampa de prompt "
                "injection: si la IA no puede hacerlo, intenta que lo hagas tú. No lo hagas sin comprobarlo por "
                "otro camino (la app oficial o el teléfono de siempre).", frase[:200]))
        else:
            hallazgos.append(HallazgoVerificacion(
                "eco_de_la_trampa", "AVISO",
                f"La IA te anima a que {que}{urgente}, igual que pedía lo que ha leído, y tú no se lo habías pedido. "
                "Puede ser una trampa que la IA está repitiendo: compruébalo por otro camino antes de hacerle caso.",
                frase[:200]))
    return hallazgos
