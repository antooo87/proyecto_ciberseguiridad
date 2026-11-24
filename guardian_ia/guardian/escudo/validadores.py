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


LETRAS_CONTROL_CIF = "JABCDEFGHI"


def cif_valido(cif: str) -> bool:
    """CIF (NIF de empresas, asociaciones...): letra + 7 números + un control que puede ser número o letra.

    Se suman los números de las posiciones pares; los de las impares se multiplican por 2 y se suman sus cifras
    (7 -> 14 -> 1+4 = 5). El control es lo que le falta al total para llegar a la siguiente decena.
    Las sociedades anónimas y limitadas (A, B...) llevan número; las entidades públicas (P, Q, S...), letra.
    """
    cif = solo_alfanumericos(cif)
    if len(cif) != 9 or cif[0] not in "ABCDEFGHJNPQRSUVW" or not cif[1:8].isdigit():
        return False
    numeros = [int(c) for c in cif[1:8]]
    total = sum(numeros[1::2]) + sum(sum(divmod(n * 2, 10)) for n in numeros[0::2])
    control = (10 - total % 10) % 10
    letra, numero = LETRAS_CONTROL_CIF[control], str(control)
    if cif[0] in "NPQRSW":
        return cif[8] == letra
    if cif[0] in "ABEH":
        return cif[8] == numero
    return cif[8] in (letra, numero)


def nss_valido(nss: str) -> bool:
    """Número de la Seguridad Social: 2 cifras de provincia + 8 de número + 2 de control.

    El control es el resto de dividir entre 97 la provincia seguida del número. Con números antiguos
    (menores de 10 millones) el cero de delante no cuenta, así que se aceptan las dos formas.
    """
    cifras = "".join(c for c in nss if c.isdigit())
    if len(cifras) != 12:
        return False
    provincia, numero, control = int(cifras[:2]), int(cifras[2:10]), int(cifras[10:])
    if not 1 <= provincia <= 53:
        return False
    posibles = {int(cifras[:10]) % 97}
    if numero < 10**7:
        posibles.add((provincia * 10**7 + numero) % 97)
    return control in posibles


def fecha_valida(fecha: str) -> bool:
    """Una fecha con números (12/03/1990) tiene que tener día de 1 a 31 y mes de 1 a 12."""
    partes = [p for p in fecha.replace(".", "/").replace("-", "/").split("/") if p]
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        return True  # "3 de mayo de 1999": ya la ha filtrado la expresión regular
    dia, mes = int(partes[0]), int(partes[1])
    return 1 <= dia <= 31 and 1 <= mes <= 12


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
