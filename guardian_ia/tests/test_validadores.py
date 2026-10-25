from guardian.escudo import validadores as v


def test_dni():
    assert v.dni_valido("12345678Z")
    assert v.dni_valido("12345678-z")
    assert not v.dni_valido("12345678A")  # letra equivocada
    assert not v.dni_valido("1234567Z")


def test_nie():
    assert v.nie_valido("X1234567L")
    assert not v.nie_valido("X1234567A")


def test_luhn():
    assert v.luhn_valido("4111 1111 1111 1111")
    assert v.luhn_valido("3782 822463 10005")  # American Express
    assert not v.luhn_valido("4111 1111 1111 1112")
    assert not v.luhn_valido("0000 0000 0000 0000")


def test_iban():
    assert v.iban_valido("ES91 2100 0418 4502 0005 1332")
    assert not v.iban_valido("ES92 2100 0418 4502 0005 1332")
    assert not v.iban_valido("ES91 2100 0418")


def test_ip():
    assert v.ip_valida("192.168.1.1")
    assert not v.ip_valida("300.1.1.1")
