"""Comprobaciones matemáticas que confirman si un dato es real.

Una expresión regular solo mira la FORMA ("8 números y una letra").
Estos validadores miran si el dato CUADRA, igual que hacen los bancos
o Hacienda. Así evitamos tapar cosas que solo se parecen a un dato
(un número de pedido, un código de producto...).
"""

import ipaddress

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def solo_alfanumericos(texto: str) -> str:
    """Quita espacios, guiones y puntos: '1234 5678-Z' -> '12345678Z'."""
    return "".join(c for c in texto if c.isalnum()).upper()


def dni_valido(dni: str) -> bool:
    """La letra del DNI es el resto de dividir el número entre 23."""
    dni = solo_alfanumericos(dni)
    if len(dni) != 9 or not dni[:8].isdigit():
        return False
    return LETRAS_DNI[int(dni[:8]) % 23] == dni[8]


def nie_valido(nie: str) -> bool:
    """El NIE es como el DNI, pero la X, Y o Z del principio vale 0, 1 o 2."""
    nie = solo_alfanumericos(nie)
    if len(nie) != 9 or nie[0] not in "XYZ" or not nie[1:8].isdigit():
        return False
    numero = str("XYZ".index(nie[0])) + nie[1:8]
    return LETRAS_DNI[int(numero) % 23] == nie[8]


def luhn_valido(numero: str) -> bool:
    """Algoritmo de Luhn: el último dígito de una tarjeta es de control.

    Se duplica uno de cada dos dígitos empezando por la derecha
    (sin contar el último), se suman todos y el total debe acabar en 0.
    """
    digitos = [int(c) for c in numero if c.isdigit()]
    if not 13 <= len(digitos) <= 19:
        return False
    if len(set(digitos)) == 1:  # 0000 0000 0000 0000 no es una tarjeta
        return False
    total = 0
    for posicion, digito in enumerate(reversed(digitos)):
        if posicion % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        total += digito
    return total % 10 == 0


# Longitud del IBAN en algunos países (ES = 24)
LONGITUD_IBAN = {
    "ES": 24, "DE": 22, "FR": 27, "IT": 27, "PT": 25, "GB": 22,
    "NL": 18, "BE": 16, "AD": 24, "IE": 22, "CH": 21, "AT": 20,
}


def iban_valido(iban: str) -> bool:
    """Norma ISO 13616: se mueve el principio al final, las letras se
    convierten en números (A=10, B=11...) y el resto entre 97 debe ser 1."""
    iban = solo_alfanumericos(iban)
    pais = iban[:2]
    if not pais.isalpha() or not iban[2:4].isdigit():
        return False
    if pais in LONGITUD_IBAN and len(iban) != LONGITUD_IBAN[pais]:
        return False
    if not 15 <= len(iban) <= 34:
        return False
    reordenado = iban[4:] + iban[:4]
    como_numero = "".join(str(int(c, 36)) for c in reordenado)
    return int(como_numero) % 97 == 1


def ip_valida(ip: str) -> bool:
    """Una IPv4 tiene 4 números del 0 al 255. Ignoramos las de ejemplo obvias."""
    try:
        direccion = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return not (direccion.is_unspecified or str(direccion) == "255.255.255.255")
