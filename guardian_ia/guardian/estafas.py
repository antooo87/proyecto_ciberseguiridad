"""¿Es una estafa? Analiza un SMS, un correo o un WhatsApp sospechoso y te dice qué hacer.

La mayoría de los engaños que llegan a la gente no son "hackeos" de película: son mensajes que te meten prisa,
se hacen pasar por tu banco, Correos o tu hijo, y te piden un dato, un código o un pago. Este módulo busca esas
pistas, te explica cada una con palabras sencillas (para que aprendas a verlas tú) y te da los pasos a seguir,
también si ya has picado (primeros auxilios).

    python -m guardian estafa "Correos: su paquete está retenido, pague 1,99 € en https://correos-envios.top"

Todo se hace en tu PC y sin IA: son reglas, así que funciona siempre y explica por qué avisa. Los enlaces se
revisan con el verificador (dominios que imitan a una marca, letras de otros alfabetos, acortadores, IP...).
No sustituye al sentido común: si dudas, pregunta por otro camino (llama al número de siempre).
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .verificador.enlaces import MARCAS, URL, revisar_enlaces
from .verificador.salida import COMANDOS


def plano(texto: str) -> str:
    """Minúsculas y sin tildes, letra a letra (las posiciones no cambian, así se puede citar el original)."""
    return "".join(unicodedata.normalize("NFD", c)[0] for c in texto).lower()


@dataclass
class Senal:
    tipo: str
    explicacion: str  # por qué es sospechoso, para que aprendas a verlo
    fragmento: str
    peso: int


@dataclass
class InformeEstafa:
    nivel: str  # BAJO, MEDIO o ALTO
    puntuacion: int
    tipo: Optional[str]  # "SMS falso de paquetería (smishing)"...
    senales: list[Senal] = field(default_factory=list)
    que_hacer: list[str] = field(default_factory=list)
    si_ya_lo_hiciste: list[str] = field(default_factory=list)

    @property
    def veredicto(self) -> str:
        return {"ALTO": "Casi seguro que es una estafa", "MEDIO": "Sospechoso: compruébalo por otro camino",
                "BAJO": "No veo señales claras de estafa"}[self.nivel]

    def a_dict(self) -> dict:
        return {**asdict(self), "veredicto": self.veredicto}


# (tipo, patrón sobre el texto en minúsculas y sin tildes, peso, explicación)
_SENALES = [
    ("urgencia", r"\b(?:en las proximas \d+ ?h(?:oras)?|en (?:un plazo de )?\d+ ?(?:h|horas)\b|inmediatamente|urgente|"
     r"ultimo aviso|hoy mismo|cuanto antes|de lo contrario|antes de que sea tarde)", 2,
     "Te mete prisa. Las estafas quieren que actúes sin pensar; un banco o una empresa de verdad te da tiempo."),
    ("amenaza", r"\b(?:sera (?:bloquead|suspendid|cancelad|desactivad|eliminad)\w*|(?:bloqueo|suspension|cancelacion) de "
     r"(?:su|tu) (?:cuenta|tarjeta|linea)|multa|sancion|embargo|recargo|acciones legales|perdera)", 2,
     "Te asusta con bloqueos, multas o cargos para que hagas lo que piden sin comprobarlo."),
    ("pide_datos", r"\b(?:verifi(?:que|ca|car)|confirm(?:e|a|ar)|actualic(?:e|a)|actualizar|valid(?:e|a|ar)|"
     r"introduc(?:e|ir|zca)|facilit(?:e|a|ar))\b[^.\n]{0,40}\b(?:datos|cuenta|identidad|tarjeta|pin|cvv|codigo|"
     r"contrasena|clave|usuario|acceso|informacion)", 3,
     "Te pide confirmar datos, la tarjeta o claves. Tu banco ya tiene tus datos: nunca te los pide por un mensaje."),
    ("pide_codigo", r"\b(?:pasame|dime|enviame|reenviame|mandame|dame|facilitanos|indicanos|facilite|indique|"
     r"proporcione|comparte|dicte|dictame|leeme)\b[^.\n]{0,40}\bcodigo|\bcodigo\b[^.\n]{0,60}\b(?:me lo (?:pasas|das|"
     r"envias|reenvias|mandas|dices)|por error)", 5,
     "Te pide un código que te ha llegado por SMS. Ese código es la llave de tu cuenta: quien lo tiene entra como si "
     "fuera tú. Las webs y apps de verdad te dicen «no lo compartas con nadie»."),
    ("pago_pequeno", r"\b(?:tasas?|gastos de (?:envio|gestion)|pago pendiente|abon(?:e|ar)|pag(?:ue|ar))\b[^.\n]{0,40}"
     r"\b\d{1,2}[.,]\d{2} ?(?:€|eur)|\b\d{1,2}[.,]\d{2} ?(?:€|eur)\b[^.\n]{0,40}\b(?:tasa|envio|aduana|entrega|paquete)",
     3, "Te pide pagar una cantidad pequeña (1,99 €, 2,99 €...). Es el gancho: lo que quieren es tu tarjeta, no los "
        "dos euros."),
    ("paquete", r"\b(?:paquete|envio|entrega|pedido)\b[^.\n]{0,60}\b(?:retenid|pendiente|no (?:ha podido|se ha podido)|"
     r"en espera|fallid|direccion incompleta|reprogramar)", 2,
     "Habla de un paquete retenido o sin entregar: es el engaño por SMS más repetido (smishing)."),
    ("premio", r"\b(?:ha(?:s)? (?:sido seleccionad|ganado)|ganador|sorteo|premio|regalo|reembolso|devolucion de \d|"
     r"tienes? derecho a (?:una )?devolucion|cheque regalo)", 2,
     "Promete un premio, un regalo o una devolución que no esperabas. Si suena demasiado bien, suele ser mentira."),
    ("familiar", r"\b(?:mama|papa|mami|papi|abuela|abuelo)\b[^\n]{0,80}\b(?:nuevo numero|numero nuevo|se me ha "
     r"(?:roto|caido|mojado|perdido)|movil (?:roto|nuevo)|guarda (?:este|mi) numero)|\b(?:este es mi nuevo numero|"
     r"he cambiado de numero|guarda este numero)", 5,
     "Alguien dice ser tu hijo, tu hija u otro familiar con un número nuevo. Es la estafa del «hijo en apuros»: "
     "después pide dinero urgente."),
    ("pide_dinero", r"\b(?:hazme|haz|hacerme|hacer|necesito (?:que me hagas )?|enviame|enviarme|mandame|mandarme|"
     r"pasame|pasarme|prestame|prestarme|dejame|dejarme)\s+(?:un\s+|una\s+)?(?:bizum|transferencia|ingreso|dinero)|"
     r"\bpuedes? (?:pagar|hacer)(?:me)? (?:tu )?(?:una|esta|la) (?:factura|transferencia)", 4,
     "Te pide dinero (un Bizum o una transferencia) por mensaje. Antes de pagar, llama a esa persona al número de "
     "siempre."),
    ("bizum_inverso", r"\b(?:acepta|aceptar|aprueba|aprobar|confirma|confirmar)\w*\b[^.\n]{0,60}\bpara (?:recibir|"
     r"cobrar)|\bpara (?:recibir|cobrar)\b[^.\n]{0,60}\b(?:acepta|aprueba|confirma)\w*", 7,
     "Te pide aceptar algo «para recibir el dinero». Es el Bizum inverso: si aceptas una solicitud, eres TÚ quien "
     "paga. Para recibir dinero no hay que aceptar nada."),
    ("solicitud_bizum", r"\bsolicitud de (?:bizum|pago|dinero)\b", 2,
     "Habla de una solicitud de Bizum o de pago: aceptarla significa que pagas tú."),
    ("llama_numero", r"\b(?:llame|llama|llamenos|contacte|contacta)\b[^.\n]{0,80}(?:\+?\d[\d .-]{7,}\d)", 2,
     "Te pide llamar a un número que viene en el mismo mensaje. Busca tú el teléfono oficial (en su web o detrás de "
     "tu tarjeta)."),
    ("aviso_virus", r"\b(?:(?:su|tu) (?:ordenador|equipo|pc|dispositivo|movil) (?:esta|ha sido) (?:infectad|bloquead|"
     r"comprometid|hackead)\w*|virus detectado|soporte tecnico de (?:microsoft|windows|apple))", 3,
     "Dice que tu ordenador tiene virus o está bloqueado. Microsoft, Apple o tu compañía nunca te avisan así: es "
     "para asustarte."),
    ("acceso_remoto", r"\b(?:anydesk|teamviewer|acceso remoto|ultraviewer|rustdesk|quick ?support|asistencia rapida)\b",
     4, "Te pide instalar un programa de acceso remoto (AnyDesk, TeamViewer...). Con él, un desconocido maneja tu PC y "
        "tu banca online."),
    ("sextorsion", r"\b(?:he grabado|tu (?:camara|webcam)|video (?:tuyo|comprometedor|intimo)|contenido intimo|paginas "
     r"(?:para|de) adultos)\b|\b(?:bitcoin|btc|monedero|wallet)\b[^.\n]{0,80}\b(?:\d+ ?horas|pagar|envia|transferi)", 5,
     "Es un chantaje: dicen tener un vídeo tuyo y piden criptomonedas. Es un correo masivo: no tienen nada."),
    ("inversion", r"\b(?:rentabilidad (?:garantizada|asegurada)|duplica(?:r)? tu dinero|ganancias? (?:garantizad|diari)\w*|"
     r"invierte (?:solo|desde)|plataforma de inversion|broker)\b", 3,
     "Promete ganar dinero fácil invirtiendo. Nadie garantiza ganancias: las falsas inversiones son de las estafas "
     "que más dinero roban."),
    ("empleo_falso", r"\b(?:trabajo|empleo) (?:desde casa|online|a tiempo parcial)\b|\bganar? (?:hasta )?\d+ ?(?:€|euros) "
     r"(?:al dia|diarios|por (?:hora|tarea))|\b(?:dar me gusta|valorar (?:productos|hoteles)|tareas sencillas)\b", 3,
     "Una oferta de trabajo fácil y muy bien pagada por mensaje. Suele acabar pidiéndote dinero «para desbloquear» "
     "lo que has ganado."),
    ("pasa_a_whatsapp", r"\b(?:escribenos|escribeme|contactanos|contacta(?:nos)?|hablanos|hablame|agreganos|anademe|"
     r"sigamos|continuamos)\b[^.\n]{0,40}\b(?:whatsapp|telegram|signal)\b", 2,
     "Te pide seguir la conversación por WhatsApp o Telegram, donde no hay filtros ni nadie que lo vigile: así "
     "trabajan las falsas ofertas de empleo y de inversión."),
    ("cambio_cuenta", r"\b(?:hemos cambiado (?:de|nuestra) (?:cuenta|entidad|banco)|nuev[ao]s? (?:cuenta|iban|numero de "
     r"cuenta|datos bancarios)|a partir de ahora (?:los pagos|las transferencias|ingrese|ingresa)|(?:actualizar?|"
     r"modificar?) (?:los|nuestros) datos bancarios)", 5,
     "Dice que ha cambiado de cuenta bancaria y que pagues en otra. Es el fraude del «cambio de IBAN» (o «del CEO»): "
     "confírmalo por teléfono."),
    ("secreto", r"\b(?:confidencial|no se lo (?:digas|comentes)|entre tu y yo|con discrecion|no lo comentes)\b", 2,
     "Te pide que no lo cuentes. Los estafadores no quieren que nadie te avise del engaño."),
    ("clickfix", r"\b(?:windows|win)\s*\+\s*r\b[^\n]{0,120}\b(?:ctrl|control)\s*\+\s*v\b|\b(?:ctrl|control)\s*\+\s*v\b"
     r"[^\n]{0,120}\b(?:windows|win)\s*\+\s*r\b", 7,
     "Te pide pulsar Windows+R y pegar algo (Ctrl+V) para «demostrar que eres humano». Es el truco ClickFix: lo que "
     "pegas es un virus que se ha copiado solo."),
    ("pega_algo", r"\b(?:windows|win)\s*\+\s*r\b|\b(?:pega|pegue|pulsa|pulse)\b[^.\n]{0,30}\b(?:ctrl|control)\s*\+\s*v\b|"
     r"\bverific(?:a|ar|ue) que (?:eres|es) (?:humano|una persona)", 4,
     "Te pide abrir Ejecutar (Windows+R), pegar algo o «verificar que eres humano» de una forma rara. Ninguna web de "
     "verdad te pide pegar nada en tu PC."),
    ("adjunto_peligroso", r"\b[\w-]+\.(?:zip|rar|7z|exe|scr|iso|img|lnk|js|vbs|hta|msi|bat|cmd)\b|\bhabilit(?:e|a|ar) "
     r"(?:el contenido|las macros|la edicion)", 3,
     "Trae o menciona un archivo que puede instalarte un virus (.zip, .exe, .iso...) o te pide activar las macros."),
    ("saludo_generico", r"^\W*(?:estimad[oa] (?:cliente|usuari[oa])|querid[oa] (?:cliente|usuari[oa])|apreciad[oa] "
     r"cliente)", 1, "Empieza con «Estimado cliente»: es un mensaje masivo, no sabe ni cómo te llamas."),
]
SENALES = [(t, re.compile(p, re.MULTILINE), peso, e) for t, p, peso, e in _SENALES]

# Marcas que más se suplantan en España: nombre en el texto -> clave en MARCAS (dominios oficiales)
MARCAS_TEXTO = {
    "correos": "correos", "amazon": "amazon", "bbva": "bbva", "santander": "santander", "caixabank": "caixabank",
    "la caixa": "caixabank", "paypal": "paypal", "netflix": "netflix", "microsoft": "microsoft", "apple": "apple",
    "icloud": "apple", "whatsapp": "whatsapp", "instagram": "instagram", "facebook": "facebook",
    "agencia tributaria": "agenciatributaria", "hacienda": "agenciatributaria", "dgt": "dgt",
    "trafico": "dgt", "seguridad social": "seguridadsocial", "dhl": "dhl", "seur": "seur", "mrw": "mrw",
    "sabadell": "sabadell", "unicaja": "unicaja", "bizum": "bizum", "ing direct": "ing", "openbank": "openbank",
    "iberdrola": "iberdrola", "endesa": "endesa", "movistar": "movistar", "vodafone": "vodafone", "orange": "orange",
}
OFICIALES_EXTRA = {  # las que no están en el verificador
    "dgt": ("dgt.es", "dgt.gob.es"), "seguridadsocial": ("seg-social.es", "seg-social.gob.es"),
    "dhl": ("dhl.com", "dhl.es"), "seur": ("seur.com",), "mrw": ("mrw.es",), "sabadell": ("bancsabadell.com",),
    "unicaja": ("unicajabanco.es",), "bizum": ("bizum.es",), "ing": ("ing.es",), "openbank": ("openbank.es",),
    "iberdrola": ("iberdrola.es", "iberdrola.com"), "endesa": ("endesa.com", "endesa.es"),
    "movistar": ("movistar.es", "telefonica.es"), "vodafone": ("vodafone.es",), "orange": ("orange.es",),
}
BANCOS = {"bbva", "santander", "caixabank", "sabadell", "unicaja", "ing", "openbank", "paypal", "bizum"}
_MARCA = re.compile(r"\b(" + "|".join(sorted(map(re.escape, MARCAS_TEXTO), key=len, reverse=True)) + r")\b")
PESO_ENLACE = {"dominio_malicioso": 6, "imita_marca": 5, "dominio_disfrazado": 5, "enlace_a_ip": 3, "acortador": 2}
EXPLICACION_ENLACE = {
    "acortador": "El enlace está acortado: no se ve adónde lleva. Las estafas lo usan para esconder la web falsa.",
    "enlace_a_ip": "El enlace va a una dirección con números (una IP) en vez de a una web con nombre: las webs de "
                   "verdad no hacen eso.",
}

# Qué tipo de estafa es, de la más concreta a la más general: (tipo, señales que la delatan, marcas)
TIPOS = [
    ("ClickFix: te piden pegar un comando", {"clickfix", "pega_algo", "comando_peligroso"}, None),
    ("Sextorsión: chantaje con un vídeo que no existe", {"sextorsion"}, None),
    ("La estafa del «hijo en apuros»", {"familiar"}, None),
    ("Robo de tu cuenta: te piden un código", {"pide_codigo"}, None),
    ("Fraude del cambio de cuenta bancaria (o «del CEO»)", {"cambio_cuenta"}, None),
    ("Correo con un archivo peligroso (virus)", {"adjunto_ejecutable"}, None),
    ("Falso soporte técnico", {"aviso_virus", "acceso_remoto"}, None),
    ("Bizum inverso: si aceptas, pagas tú", {"bizum_inverso", "solicitud_bizum"}, None),
    ("Falsa inversión", {"inversion"}, None),
    ("Falsa oferta de trabajo", {"empleo_falso"}, None),
    ("Te llevan a WhatsApp o Telegram para engañarte con calma", {"pasa_a_whatsapp"}, None),
    ("SMS o correo falso de paquetería (smishing)", {"paquete", "pago_pequeno"}, None),
    ("Suplantación de tu banco (phishing)", {"pide_datos", "amenaza", "enlace_no_oficial", "imita_marca",
                                              "remitente_falso", "enlace_enganoso"}, BANCOS),
    ("Falsa devolución o multa de Hacienda", {"premio", "amenaza", "pide_datos", "enlace_no_oficial",
                                              "remitente_falso", "enlace_enganoso"}, {"agenciatributaria"}),
    ("Falsa multa de la DGT", {"amenaza", "pide_datos", "enlace_no_oficial", "pago_pequeno", "remitente_falso"},
     {"dgt"}),
    ("Falso premio o sorteo", {"premio"}, None),
    ("Correo con texto escondido para engañar a la IA que te lo resume", {"texto_oculto"}, None),
    ("Phishing: se hacen pasar por una empresa para quitarte datos", {"pide_datos", "enlace_no_oficial", "imita_marca",
                                                                      "remitente_falso", "enlace_enganoso"}, None),
    ("Te piden dinero por mensaje", {"pide_dinero"}, None),
]

AYUDA = ("Si tienes dudas o ya has picado, te ayudan gratis en el 017 de INCIBE (Tu Ayuda en Ciberseguridad). "
         "Guarda el mensaje (una captura) por si quieres denunciar en la Policía Nacional o la Guardia Civil.")
QUE_HACER = {
    "ClickFix: te piden pegar un comando": [
        "No pegues nada en Ejecutar (Windows+R), PowerShell ni la terminal: ninguna web de verdad te lo pide para "
        "«comprobar que eres humano».", "Cierra esa página."],
    "Sextorsión: chantaje con un vídeo que no existe": [
        "No pagues y no contestes: es un correo enviado a miles de personas y no tienen ningún vídeo.",
        "Si te dicen una contraseña tuya de verdad, sale de una filtración antigua: cámbiala donde la uses."],
    "La estafa del «hijo en apuros»": [
        "No pagues nada todavía: llama a tu hijo o familiar al número de siempre.",
        "Si no contesta, pregunta algo que solo esa persona sepa. Los estafadores no saben responder."],
    "Robo de tu cuenta: te piden un código": [
        "No des nunca ese código, ni aunque te lo pida un amigo: es la llave de tu cuenta.",
        "Activa la verificación en dos pasos (en WhatsApp: Ajustes > Cuenta > Verificación en dos pasos)."],
    "Fraude del cambio de cuenta bancaria (o «del CEO»)": [
        "No pagues a la cuenta nueva hasta confirmarlo llamando al proveedor o a tu jefe al teléfono de siempre, no "
        "al del correo.", "Un cambio de cuenta nunca se acepta solo por correo: avisa a quien lleve los pagos."],
    "Correo con un archivo peligroso (virus)": [
        "No abras el adjunto: borra el correo. Si esperabas una factura, pídesela al proveedor por otro camino.",
        "Si ya lo has abierto, desconecta el PC de Internet y avisa a sistemas (o pásale un antivirus)."],
    "Correo con texto escondido para engañar a la IA que te lo resume": [
        "No hagas caso de avisos que solo salen en el resumen de la IA: ni Google, ni Microsoft, ni tu banco te "
        "avisan así.", "Borra el correo o márcalo como spam; si es del trabajo, reenvíalo a sistemas."],
    "Falso soporte técnico": [
        "Cuelga o cierra el aviso: Microsoft, Apple o tu compañía no te llaman para decirte que tienes virus.",
        "No instales AnyDesk, TeamViewer ni nada que te pidan, y no le des acceso a tu PC a nadie."],
    "Bizum inverso: si aceptas, pagas tú": [
        "No aceptes la solicitud: para recibir un Bizum no hay que aceptar nada.", "Si es una venta, pide que te lo "
        "envíen ellos desde su app."],
    "Falsa inversión": [
        "No metas dinero ni des tus datos. Comprueba en la CNMV si la empresa está autorizada.",
        "Desconfía de anuncios con famosos y de «asesores» que te escriben por WhatsApp o Telegram."],
    "Te llevan a WhatsApp o Telegram para engañarte con calma": [
        "No sigas la conversación por WhatsApp o Telegram con alguien que no conoces.",
        "Si es una empresa de verdad, búscala tú y escríbele por su web oficial."],
    "Falsa oferta de trabajo": [
        "No pagues nada para «desbloquear» ganancias ni des tus datos bancarios.",
        "Un trabajo de verdad no se consigue dando «me gusta» por WhatsApp o Telegram."],
    "SMS o correo falso de paquetería (smishing)": [
        "No pinches en el enlace. Si esperas un paquete, mira el seguimiento en la web o la app oficial de la "
        "empresa, escribiendo tú la dirección.", "Correos y las empresas de mensajería no te piden la tarjeta por SMS."],
    "Suplantación de tu banco (phishing)": [
        "No pinches en el enlace ni llames al número del mensaje. Entra en la app de tu banco o llama al teléfono "
        "que viene detrás de tu tarjeta.", "Tu banco nunca te pide claves, códigos ni la tarjeta por SMS o correo."],
    "Falsa devolución o multa de Hacienda": [
        "Hacienda no avisa de devoluciones ni multas con enlaces por SMS o correo. Mira tu situación en la sede "
        "electrónica oficial (agenciatributaria.gob.es), escribiendo tú la dirección."],
    "Falsa multa de la DGT": [
        "La DGT no manda multas por SMS con enlaces para pagar. Consulta tus multas en la web oficial (dgt.es), "
        "escribiendo tú la dirección."],
    "Falso premio o sorteo": [
        "No des datos ni pagues «gastos de envío» por un premio que no has pedido."],
    "Phishing: se hacen pasar por una empresa para quitarte datos": [
        "No pinches en el enlace ni des datos. Si quieres comprobarlo, entra tú en la web o la app oficial."],
    "Te piden dinero por mensaje": [
        "Antes de pagar, llama a esa persona al número de siempre para comprobar que es ella."],
}
GENERALES = ["No pinches en los enlaces ni contestes. Si quieres comprobar algo, entra tú en la web o la app "
             "oficial, escribiendo la dirección a mano.",
             "Si dudas, pregunta por otro camino: llama a la empresa o a la persona al teléfono de siempre."]

# Primeros auxilios: lo que hay que hacer YA si has picado
YA_PASO = [
    ("tarjeta", r"\b(?:he (?:metido|puesto|dado|introducido|escrito)|meti|puse|di)\b[^.\n]{0,40}\b(?:tarjeta|cvv|"
     r"numero de la tarjeta|datos bancarios)",
     "Llama YA a tu banco (el teléfono está detrás de tu tarjeta o en su app) para bloquear la tarjeta, y revisa los "
     "movimientos de los últimos días."),
    ("contrasena", r"\b(?:he (?:metido|puesto|dado|introducido|escrito)|meti|puse|di)\b[^.\n]{0,40}\b(?:contrasena|"
     r"clave|usuario|password)",
     "Cambia esa contraseña ahora (y en todas las webs donde uses la misma) y activa la verificación en dos pasos."),
    ("codigo", r"\b(?:he (?:dado|pasado|enviado|reenviado)|di|pase|envie)\b[^.\n]{0,40}\bcodigo",
     "Si era de WhatsApp o de tu banco, entra ya en la app (o llama al banco): pueden estar usando tu cuenta. En "
     "WhatsApp, vuelve a registrarte con tu número para echarles y activa la verificación en dos pasos."),
    ("pago", r"\b(?:he (?:pagado|hecho (?:un|una) (?:bizum|transferencia|ingreso)|enviado (?:dinero|un bizum)|"
     r"transferido)|pague|hice un bizum)\b",
     "Llama a tu banco cuanto antes para intentar parar o recuperar el pago, y denuncia con las capturas."),
    ("instalado", r"\b(?:he (?:instalado|descargado|abierto el archivo|ejecutado)|les? he dado acceso|instale|"
     r"descargue)\b|\b(?:anydesk|teamviewer)\b[^.\n]{0,40}\b(?:instalad|abiert)",
     "Desconecta el PC de Internet, desinstala el programa que te hicieron instalar, pásale un antivirus y cambia tus "
     "contraseñas desde otro dispositivo."),
    ("pegado", r"\b(?:he pegado|pegue|he ejecutado|ejecute)\b[^.\n]{0,40}\b(?:comando|powershell|terminal|ejecutar)",
     "Desconecta el PC de Internet ya y pide ayuda (017): lo que pegaste puede haber instalado un programa que roba "
     "contraseñas. Cambia tus contraseñas desde otro dispositivo."),
    ("pinchado", r"\b(?:he (?:pinchado|hecho clic|clicado|abierto el enlace|entrado en el enlace)|pinche|clique)\b",
     "Solo con pinchar no suele pasar nada grave si no metiste datos ni descargaste nada. Cierra la página y, si "
     "metiste algún dato, sigue los otros consejos."),
]
YA_PASO = [(t, re.compile(p), consejo) for t, p, consejo in YA_PASO]


def _oficiales(clave: str) -> tuple[str, ...]:
    return MARCAS.get(clave) or OFICIALES_EXTRA.get(clave, ())


def _enlaces_no_oficiales(texto: str, marcas: set[str]) -> list[Senal]:
    """El mensaje dice ser de una marca pero el enlace no va a su web oficial."""
    senales = []
    for url in sorted({u.rstrip(".,;:!?") for u in URL.findall(texto)}):
        host = (urlparse(url).hostname or "").lower()
        for marca in marcas:
            oficiales = _oficiales(marca)
            if oficiales and not any(host == o or host.endswith("." + o) for o in oficiales):
                nombre = next((n for n, c in MARCAS_TEXTO.items() if c == marca), marca)
                senales.append(Senal("enlace_no_oficial", f"Dice ser de {nombre.title() if len(nombre) > 4 else nombre.upper()} "
                                     f"pero el enlace no va a su web oficial ({', '.join(oficiales)}): lleva a "
                                     f"{host}.", url, 4))
                break
    return senales


def primeros_auxilios(texto: str) -> list[str]:
    """Si cuentas que ya has picado ("he metido la tarjeta"), qué hacer ya, en orden."""
    p = plano(texto)
    return [consejo for _tipo, patron, consejo in YA_PASO if patron.search(p)]


def analizar(texto: str, extra: Sequence[Senal] = ()) -> InformeEstafa:
    """`extra`: pistas que no salen del texto (las del correo entero: remitente, enlaces, adjuntos...)."""
    p = plano(texto)
    senales: list[Senal] = list(extra)
    for tipo, patron, peso, explicacion in SENALES:
        m = patron.search(p)
        if m:
            senales.append(Senal(tipo, explicacion, texto[m.start():m.end()].strip(), peso))
    for _nombre, patron, _gravedad, explicacion in COMANDOS:
        m = patron.search(texto)
        if m:
            senales.append(Senal("comando_peligroso", f"Trae un comando que {explicacion}. No lo pegues nunca.",
                                 m.group(0)[:160], 5))
            break
    marcas = {MARCAS_TEXTO[m.group(1)] for m in _MARCA.finditer(p)}
    vistos = set()
    for h in revisar_enlaces(texto):
        if h.tipo in PESO_ENLACE and (h.tipo, h.fragmento) not in vistos:
            vistos.add((h.tipo, h.fragmento))
            senales.append(Senal(h.tipo, EXPLICACION_ENLACE.get(h.tipo, h.explicacion), h.fragmento,
                                 PESO_ENLACE[h.tipo]))
    imitados = {s.fragmento for s in senales if s.tipo in ("imita_marca", "dominio_malicioso", "dominio_disfrazado")}
    senales += [s for s in _enlaces_no_oficiales(texto, marcas) if s.fragmento not in imitados]

    puntuacion = sum(s.peso for s in senales)
    nivel = "ALTO" if puntuacion >= 7 else "MEDIO" if puntuacion >= 3 else "BAJO"
    tipos_vistos = {s.tipo for s in senales}
    tipo = None
    if nivel != "BAJO":
        for nombre, delatoras, de_marcas in TIPOS:
            if tipos_vistos & delatoras and (de_marcas is None or marcas & de_marcas):
                tipo = nombre
                break
    que_hacer = (QUE_HACER.get(tipo, []) + GENERALES[:1] + [AYUDA]) if nivel != "BAJO" else [
        "Aun así, si te pide datos, dinero o prisa, compruébalo por otro camino antes de hacer nada."]
    return InformeEstafa(nivel, puntuacion, tipo, sorted(senales, key=lambda s: -s.peso), que_hacer,
                         primeros_auxilios(texto))


# ------------------------------------------------------------------ correos enteros (.eml)
_PARECE_WEB = re.compile(r"^(?:https?://)?(?:www\.)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?:[/:?#]\S*)?$", re.IGNORECASE)


def _base(host: str) -> str:
    partes = host.lower().strip(".").split(".")
    if len(partes) >= 3 and partes[-2] in ("gob", "com", "org", "co", "gov", "edu"):
        return ".".join(partes[-3:])
    return ".".join(partes[-2:])


def senales_del_correo(correo) -> list[Senal]:
    """Pistas que solo se ven en el correo entero: quién lo manda de verdad, adónde llevan los enlaces, qué esconde
    y qué adjunta. `correo` es un guardian.correo.Correo."""
    from .correo import adjunto_peligroso

    senales: list[Senal] = []
    for m in _MARCA.finditer(plano(correo.nombre)):
        oficiales = _oficiales(MARCAS_TEXTO[m.group(1)])
        dominio = correo.dominio
        if oficiales and dominio and not any(dominio == o or dominio.endswith("." + o) for o in oficiales):
            senales.append(Senal(
                "remitente_falso", f"Dice ser «{correo.nombre}», pero escribe desde {dominio}, que no es su dominio "
                f"oficial ({', '.join(oficiales)}). Cualquiera puede poner el nombre que quiera en «De»: lo que "
                "cuenta es lo que va detrás de la @.", correo.de, 5))
            break
    if correo.responder_a and correo.dominio_respuesta and correo.dominio_respuesta != correo.dominio:
        senales.append(Senal(
            "responder_a_otro", f"Si contestas, tu respuesta no irá a {correo.dominio or 'quien dice ser'} sino a "
            f"{correo.dominio_respuesta}: es el truco del fraude del CEO para que el jefe de verdad no se entere.",
            correo.responder_a, 3))
    for texto, destino in correo.enlaces:
        visto, real = _PARECE_WEB.match(texto.strip()), (urlparse(destino).hostname or "").lower()
        if visto and real and _base(visto.group(1)) != _base(real):
            senales.append(Senal(
                "enlace_enganoso", f"El enlace dice «{texto.strip()[:60]}», pero en realidad lleva a {real}. Es la "
                "trampa más clásica: pasa el ratón por encima (sin pinchar) y mira la dirección de verdad.",
                destino, 5))
            break
    escondido = next((o for o in correo.ocultos if len(re.findall(r"\w+", o)) >= 4), None)
    if escondido:
        senales.append(Senal(
            "texto_oculto", "El correo esconde texto que tú no ves (letra de tamaño 0, blanca o invisible). Se usa "
            "para engañar a la IA que te resume el correo (pasó con Gemini en Gmail en 2025) o para colarse en los "
            "filtros de spam.", " ".join(escondido.split())[:160], 5))
    for nombre in correo.adjuntos:
        motivo = adjunto_peligroso(nombre)
        if motivo:
            senales.append(Senal("adjunto_ejecutable", motivo, nombre, 5))
            break
    return senales


def analizar_correo(datos: bytes):
    """Analiza un correo guardado (.eml). Devuelve (informe, correo)."""
    from .correo import leer_correo

    correo = leer_correo(datos)
    return analizar(correo.como_texto(), senales_del_correo(correo)), correo


EXTENSIONES_MENSAJES = {".eml", ".txt", ".msg"}


@dataclass
class MensajeRevisado:
    archivo: str
    informe: Optional[InformeEstafa]
    de: str = ""
    asunto: str = ""
    error: Optional[str] = None

    def a_dict(self) -> dict:
        return {"archivo": self.archivo, "de": self.de, "asunto": self.asunto, "error": self.error,
                **({"nivel": self.informe.nivel, "puntuacion": self.informe.puntuacion, "tipo": self.informe.tipo,
                    "pistas": [s.tipo for s in self.informe.senales]} if self.informe else {})}


def revisar_mensaje(datos: bytes, nombre: str) -> MensajeRevisado:
    """Un correo (.eml) o un mensaje en texto (.txt) guardado en un archivo."""
    if nombre.lower().endswith(".msg"):
        return MensajeRevisado(nombre, None, error="Los .msg de Outlook no se leen todavía: guárdalo como .eml "
                                                   "(Archivo > Guardar como) o copia el texto.")
    if nombre.lower().endswith(".eml"):
        informe, correo = analizar_correo(datos)
        return MensajeRevisado(nombre, informe, correo.de, correo.asunto)
    texto = datos.decode("utf-8", errors="replace")
    return MensajeRevisado(nombre, analizar(texto), asunto=texto.strip().splitlines()[0][:80] if texto.strip() else "")


def revisar_bandeja(carpeta: str) -> list[MensajeRevisado]:
    """Todos los correos (.eml) y mensajes (.txt) de una carpeta, del más peligroso al menos."""
    raiz = Path(carpeta)
    if not raiz.is_dir():
        raise NotADirectoryError(f"{carpeta} no es una carpeta")
    resultados = []
    for ruta in sorted(raiz.rglob("*")):
        if ruta.is_file() and ruta.suffix.lower() in EXTENSIONES_MENSAJES and ruta.stat().st_size <= 25 * 2**20:
            resultados.append(revisar_mensaje(ruta.read_bytes(), str(ruta.relative_to(raiz))))
    return ordenar(resultados)


def ordenar(revisados: list[MensajeRevisado]) -> list[MensajeRevisado]:
    """Del más peligroso al menos (y los que no se han podido leer, al final)."""
    orden = {"ALTO": 0, "MEDIO": 1, "BAJO": 2}
    return sorted(revisados, key=lambda r: (orden.get(r.informe.nivel, 3) if r.informe else 4,
                                            -(r.informe.puntuacion if r.informe else 0), r.archivo))
