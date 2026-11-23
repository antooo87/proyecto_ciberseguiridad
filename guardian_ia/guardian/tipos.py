"""Nombres que entiende cualquiera para cada tipo de dato: [TELEFONO_1] es un "teléfono", [IBAN_1] una "cuenta
bancaria". Se usan en los avisos, en los informes y en los gráficos, para no enseñar "FECHA_NACIMIENTO" a nadie.
"""

# tipo -> (singular, plural)
NOMBRES = {
    "PERSONA": ("nombre de persona", "nombres de personas"),
    "DIRECCION": ("dirección postal", "direcciones postales"),
    "CONTRASENA": ("contraseña", "contraseñas"),
    "CLAVE_PRIVADA": ("clave privada", "claves privadas"),
    "JWT": ("token de sesión", "tokens de sesión"),
    "CLAVE_API": ("clave de API", "claves de API"),
    "DNI": ("DNI", "DNI"),
    "NIE": ("NIE", "NIE"),
    "CIF": ("CIF de empresa", "CIF de empresa"),
    "NSS": ("número de la Seguridad Social", "números de la Seguridad Social"),
    "PASAPORTE": ("pasaporte", "pasaportes"),
    "FECHA_NACIMIENTO": ("fecha de nacimiento", "fechas de nacimiento"),
    "IBAN": ("cuenta bancaria (IBAN)", "cuentas bancarias (IBAN)"),
    "TARJETA": ("tarjeta bancaria", "tarjetas bancarias"),
    "EMAIL": ("correo electrónico", "correos electrónicos"),
    "TELEFONO": ("teléfono", "teléfonos"),
    "IP": ("dirección IP", "direcciones IP"),
    "MATRICULA": ("matrícula", "matrículas"),
}


def nombre(tipo: str, cuantos: int = 1) -> str:
    """'TELEFONO' -> 'teléfono' (o 'teléfonos' si son varios). Un tipo desconocido se enseña tal cual."""
    singular, plural = NOMBRES.get(tipo, (tipo, tipo))
    return singular if cuantos == 1 else plural


def contar(cuenta: dict[str, int]) -> str:
    """{'DNI': 1, 'TELEFONO': 2} -> '1 DNI y 2 teléfonos'."""
    partes = [f"{n} {nombre(tipo, n)}" for tipo, n in cuenta.items() if n]
    if not partes:
        return "ningún dato sensible"
    return partes[0] if len(partes) == 1 else f"{', '.join(partes[:-1])} y {partes[-1]}"
