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


def test_iban_en_minusculas():
    r = Escudo().proteger("mi cuenta es es91 2100 0418 4502 0005 1332, gracias")
    assert r.protegido == "mi cuenta es [IBAN_1], gracias"


def test_correo_con_dni_dentro_se_tapa_entero():
    r = Escudo().proteger("escríbeme a 12345678z@gmail.com o a ana.12345678Z@correo.es")
    assert r.protegido == "escríbeme a [EMAIL_1] o a [EMAIL_2]"
    assert "@" not in r.protegido


def test_tipos_espanoles_nuevos():
    casos = {
        "La empresa con CIF B-12345674 nos debe dinero": ("CIF", "B-12345674"),
        "El ayuntamiento (CIF P1234567D) paga a 60 días": ("CIF", "P1234567D"),
        "Mi número de la Seguridad Social es 28 12345678 40": ("NSS", "28 12345678 40"),
        "Nº afiliación S.S.: 28/12345678/40": ("NSS", "28/12345678/40"),
        "Mi pasaporte es PAA123456 y caduca en 2030": ("PASAPORTE", "PAA123456"),
        "Fecha de nacimiento: 12/03/1990": ("FECHA_NACIMIENTO", "12/03/1990"),
        "Nací el 3 de mayo de 1999 en Sevilla": ("FECHA_NACIMIENTO", "3 de mayo de 1999"),
        "Fecha nac.: 05/11/1985 (como en los formularios)": ("FECHA_NACIMIENTO", "05/11/1985"),
        "Fecha de nac. 21/12/1985": ("FECHA_NACIMIENTO", "21/12/1985"),
    }
    for texto, (tipo, dato) in casos.items():
        r = Escudo().proteger(texto)
        assert dato not in r.protegido and f"[{tipo}_1]" in r.protegido, texto


def test_tipos_nuevos_no_tapan_lo_que_solo_se_parece():
    textos = [
        "CIF B-12345675 con el control mal",  # no cuadra el control
        "P12345674: las entidades públicas llevan letra",  # P con número no es un CIF
        "NSS: 28 12345678 41",  # control mal
        "El pedido 281234567840 ya ha salido",  # 12 cifras sin decir qué son
        "La referencia PAA123456 del almacén",  # sin la palabra pasaporte
        "La reunión es el 12/03/2026",  # una fecha cualquiera
        "Fecha de nacimiento: 45/13/1990",  # día y mes imposibles
        "La fecha nacional del examen es el 12/06/2026",  # «nac» dentro de otra palabra
    ]
    for t in textos:
        assert Escudo().proteger(t).protegido == t, t


def test_columnas_de_una_tabla_con_la_cabecera_lejos_del_dato():
    # En un Excel o un CSV la palabra «Seguridad Social» está en la cabecera, no al lado del número
    from guardian.escudo.detectores import detectar_en_columnas
    tabla = ("Empleado\tNº afiliación S.S.\tFecha de nacimiento\tContraseña\n"
             "Ana Ruiz\t50/12345678/76\t03/04/1990\tVerano2024!\n"
             "Luis Gil\t28/87654321/17\t21/12/1985\tPerro_77\n"
             "\n"
             "Total\t2\n")
    hallazgos = detectar_en_columnas(tabla)
    assert [(h.tipo, h.valor) for h in hallazgos] == [
        ("NSS", "50/12345678/76"), ("FECHA_NACIMIENTO", "03/04/1990"), ("CONTRASENA", "Verano2024!"),
        ("NSS", "28/87654321/17"), ("FECHA_NACIMIENTO", "21/12/1985"), ("CONTRASENA", "Perro_77")]
    assert all(tabla[h.inicio:h.fin] == h.valor for h in hallazgos)
    protegido = Escudo().proteger(tabla).protegido
    assert "50/12345678/76" not in protegido and "Verano2024!" not in protegido
    for cabecera in ("Fecha nac.", "F. nac.", "Fecha de nac."):  # las cabeceras abreviadas también cuentan
        corta = f"Empleado;{cabecera}\nAna Ruiz;03/04/1990\n"
        assert [(h.tipo, h.valor) for h in detectar_en_columnas(corta)] == [("FECHA_NACIMIENTO", "03/04/1990")], cabecera


def test_columnas_no_se_inventan_datos():
    from guardian.escudo.detectores import detectar_en_columnas
    # el número no cuadra con su control (no es un NSS) y «palabra clave» no es una contraseña
    assert detectar_en_columnas("Nº S.S.;Importe\n50/12345678/99;30\n") == []
    assert detectar_en_columnas("Producto;Palabra clave\nZapatillas;running\n") == []


def test_contrasena_dentro_de_una_cadena_de_conexion():
    texto = "Me falla esto: postgres://rrhh:Pg_rrhh_77x@10.20.4.16:5432/nominas ¿por qué?"
    tipos = {(h.tipo, h.valor) for h in Escudo().detectar(texto)[0]}
    assert ("CONTRASENA", "Pg_rrhh_77x") in tipos and ("IP", "10.20.4.16") in tipos
    # la palabra «password» de los ejemplos de la documentación no es una contraseña
    assert "CONTRASENA" not in {h.tipo for h in Escudo().detectar("https://usuario:password@example.com")[0]}
