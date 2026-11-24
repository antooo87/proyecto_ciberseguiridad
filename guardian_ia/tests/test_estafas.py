"""«¿Es una estafa?» y el juego «¿Lo detectas?»."""

import pytest

from guardian.__main__ import main
from guardian.escuela import MENSAJES, corregir, mezclados
from guardian.estafas import analizar, plano, primeros_auxilios
from guardian.mejorador import Mejorador


@pytest.mark.parametrize("texto, tipo", [
    ("Correos: Su paquete está retenido por tasas de aduana. Abone 1,99 € en las próximas 24 horas en "
     "https://correos-envios.top/pago o será devuelto.", "paquetería"),
    ("Hola mamá, se me ha caído el móvil y este es mi nuevo número. ¿Puedes hacerme un Bizum de 480 €? Es urgente.",
     "hijo en apuros"),
    ("Hola! Te he enviado un código de 6 dígitos por error, ¿me lo pasas porfa? Es urgente.", "código"),
    ("Estimado cliente: hemos detectado un acceso inusual a su banca BBVA. Verifique su identidad en "
     "https://bbva-seguridad-clientes.com/acceso antes de 24h o su cuenta será bloqueada.", "banco"),
    ("AGENCIA TRIBUTARIA: tiene derecho a una devolución de 324,50 €. Confirme sus datos bancarios en "
     "https://bit.ly/aeat-devolucion", "Hacienda"),
    ("Hemos cambiado de banco y a partir de ahora los pagos van al nuevo IBAN. Haz hoy mismo la transferencia de "
     "18.400 €. Es confidencial.", "cambio de cuenta"),
    ("Para demostrar que no eres un robot pulsa Windows + R, pulsa Ctrl + V y Enter.", "ClickFix"),
    ("He grabado un vídeo tuyo con tu webcam. Envía 1200 € en Bitcoin a este monedero en 48 horas.", "Sextorsión"),
    ("ALERTA: su ordenador ha sido bloqueado por un virus detectado. Llame al soporte técnico de Microsoft al "
     "900 000 000 e instale AnyDesk.", "soporte"),
    ("Te he enviado una solicitud de Bizum de 150 € por el sofá. Acéptala para recibir el dinero.", "Bizum inverso"),
])
def test_reconoce_las_estafas_mas_comunes(texto, tipo):
    informe = analizar(texto)
    assert informe.nivel == "ALTO", [s.tipo for s in informe.senales]
    assert tipo.lower() in informe.tipo.lower()
    assert informe.que_hacer and any("017" in paso for paso in informe.que_hacer)
    assert all(s.explicacion and s.fragmento for s in informe.senales)


@pytest.mark.parametrize("texto", [
    "Tu código de verificación de Google es 482913. No lo compartas con nadie.",
    "BBVA: Compra de 45,00 EUR en MERCADONA con tu tarjeta ...1234. Si no la reconoces, llama al 900 102 801.",
    "Tu paquete de Amazon llegará mañana entre las 9 y las 14h.",
    "Es urgente que revisemos el informe antes de la reunión del lunes con el cliente.",
    "Te mando una solicitud de Bizum por lo de la cena, son 23 €.",
    "Tu pedido de Amazon ha sido enviado. Síguelo en https://www.amazon.es/gp/your-account/order-history",
])
def test_no_ve_estafas_en_mensajes_normales(texto):
    assert analizar(texto).nivel == "BAJO"


def test_el_enlace_que_no_es_de_la_marca_se_explica():
    informe = analizar("DGT: tiene una multa pendiente de 50 €. Pague en https://dgt-multas.example/pago o tendrá "
                       "un recargo.")
    assert informe.tipo == "Falsa multa de la DGT"
    pista = next(s for s in informe.senales if s.tipo == "enlace_no_oficial")
    assert "dgt.es" in pista.explicacion and "dgt-multas.example" in pista.explicacion


def test_primeros_auxilios_si_ya_has_picado():
    pasos = primeros_auxilios("he pinchado en el enlace del SMS y he metido mi tarjeta y la contraseña del banco")
    assert any("bloquear la tarjeta" in p for p in pasos)
    assert any("Cambia esa contraseña" in p for p in pasos)
    assert primeros_auxilios("¿qué es el phishing?") == []


def test_plano_no_cambia_las_posiciones():
    texto = "Último AVISO: verifíque su cuenta"
    assert len(plano(texto)) == len(texto) and plano(texto).startswith("ultimo aviso")


def test_el_mejorador_avisa_y_da_primeros_auxilios():
    mejora = Mejorador().mejorar("he pinchado en un enlace de un SMS de Correos y he metido mi tarjeta, ¿qué hago?")
    assert mejora.urgente and "bloquear la tarjeta" in mejora.urgente[0]
    pegado = Mejorador().mejorar("¿Esto es verdad? Correos: su paquete está retenido, abone 1,99 € en las próximas "
                                 "24 horas en https://correos-envios.top/pago")
    assert pegado.estafa and "paquetería" in pegado.estafa


def test_el_juego_esta_bien_etiquetado():
    """Cada mensaje del juego lo clasifica bien el propio Guardián. Ojo: se escribieron a la vez que las reglas,
    así que esto comprueba que el juego es coherente, no mide cómo de bien detecta estafas nuevas."""
    assert sum(m.es_estafa for m in MENSAJES) >= 8 and sum(not m.es_estafa for m in MENSAJES) >= 4
    for mensaje in MENSAJES:
        acierto, informe = corregir(mensaje, mensaje.es_estafa)
        assert acierto and (informe.nivel != "BAJO") == mensaje.es_estafa, mensaje.texto[:50]


def test_mezclados_con_semilla_es_reproducible():
    assert mezclados(5, semilla=1) == mezclados(5, semilla=1) and len(mezclados(5, semilla=1)) == 5


def test_terminal_estafa_y_aprende(capsys, monkeypatch):
    assert main(["estafa", "Correos: su paquete está retenido, abone 1,99 € en las próximas 24 horas en "
                           "https://correos-envios.top/pago"]) == 2  # código 2: casi seguro una estafa
    salida = capsys.readouterr().out
    assert "Casi seguro que es una estafa" in salida and "Qué hacer" in salida
    respuestas = iter(["e", "q"])
    monkeypatch.setattr("builtins.input", lambda _texto: next(respuestas))
    assert main(["aprende", "--cuantos", "3"]) == 0
    assert "Has acertado" in capsys.readouterr().out
