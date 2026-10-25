from guardian.escudo import Boveda, Escudo
from guardian.escudo.detector_ia import DetectorIA
from tests.falsa_ia import IAFalsa

TEXTO = ("Soy Ana, DNI 12345678Z, email ana@gmail.com, móvil +34 612 345 678, "
         "IBAN ES91 2100 0418 4502 0005 1332, tarjeta 4111 1111 1111 1111, "
         "servidor 192.168.1.20, coche 1234 BCD, contraseña: Verano2024! y clave AKIAIOSFODNN7EXAMPLE")


def test_tapa_todos_los_tipos():
    r = Escudo().proteger(TEXTO)
    for dato in ["12345678Z", "ana@gmail.com", "612 345 678", "ES91", "4111", "192.168",
                 "1234 BCD", "Verano2024", "AKIA"]:
        assert dato not in r.protegido, dato
    assert set(r.resumen()) == {"DNI", "EMAIL", "TELEFONO", "IBAN", "TARJETA", "IP",
                                "MATRICULA", "CONTRASENA", "CLAVE_API"}


def test_no_tapa_trampas():
    textos = ["DNI falso 12345678A", "pedido 1234 5678 9012 3456", "versión 3.14.0",
              "La clave es practicar.", "ISBN 978-84-376-0494-7", "CP 28013"]
    for t in textos:
        assert Escudo().proteger(t).protegido == t, t


def test_restaurar_devuelve_el_original():
    boveda = Boveda()
    escudo = Escudo()
    r = escudo.proteger(TEXTO, boveda)
    assert escudo.restaurar(r.protegido, boveda) == TEXTO


def test_mismo_dato_mismo_marcador():
    boveda = Boveda()
    escudo = Escudo()
    a = escudo.proteger("mi DNI es 12345678Z", boveda).protegido
    b = escudo.proteger("repito: 12345678-Z", boveda).protegido
    assert "[DNI_1]" in a and "[DNI_1]" in b
    assert len(boveda) == 1


def test_restaurar_tolera_cambios_de_la_ia():
    boveda = Boveda()
    Escudo().proteger("mi DNI es 12345678Z", boveda)
    assert Escudo.restaurar("Tu DNI [ dni_1 ] es correcto", boveda) == "Tu DNI 12345678Z es correcto"
    assert Escudo.restaurar("[DNI_9] no existe", boveda) == "[DNI_9] no existe"


def test_detector_ia_tapa_nombres_y_descarta_inventos():
    ia = IAFalsa([{"personas": ["Ana López", "Pedro Inventado"], "direcciones": [], "contrasenas": []}])
    r = Escudo(detector_ia=DetectorIA(ia)).proteger("Hola, soy Ana López y mi DNI es 12345678Z")
    assert r.protegido == "Hola, soy [PERSONA_1] y mi DNI es [DNI_1]"


def test_si_la_ia_falla_siguen_las_reglas():
    from guardian.ia import ErrorIA
    ia = IAFalsa(error=ErrorIA("apagada"))
    r = Escudo(detector_ia=DetectorIA(ia)).proteger("DNI 12345678Z")
    assert r.protegido == "DNI [DNI_1]"
    assert r.avisos
