"""Colores y forma de enseñar los resultados en la terminal (los usan el programa y la demostración)."""

import os
import sys

# Colores para la terminal. Sin colores si la salida va a un archivo (así el registro no se llena de códigos
# raros) o si existe la variable NO_COLOR (https://no-color.org).
CON_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ
if CON_COLOR and os.name == "nt":
    os.system("")  # en Windows hay que activarlos
VERDE, AMARILLO, ROJO, AZUL, GRIS, NEGRITA, FIN = (
    "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[90m", "\033[1m", "\033[0m") if CON_COLOR else ("",) * 7
COLOR_NIVEL = {"NINGUNO": VERDE, "BAJO": VERDE, "MEDIO": AMARILLO, "ALTO": ROJO}
COLOR_GRAVEDAD = {"CRITICA": ROJO, "ALTA": ROJO, "PELIGRO": ROJO, "MEDIA": AMARILLO, "AVISO": AMARILLO,
                  "BAJA": AZUL, "INFO": GRIS}


def resumen(cuenta: dict[str, int]) -> str:
    if not cuenta:
        return "ningún dato sensible"
    return ", ".join(f"{n} {tipo}" for tipo, n in cuenta.items())


def imprimir_informe(informe):
    """Informe de la aduana."""
    for aviso in informe.avisos:
        print(f"{AMARILLO}! {aviso}{FIN}")
    color = COLOR_NIVEL[informe.nivel]
    print(f"{NEGRITA}Riesgo: {color}{informe.nivel}{FIN} (puntuación {informe.puntuacion})")
    for h in informe.hallazgos:
        print(f"  {color}●{FIN} línea {h.linea}: {h.explicacion}")
        print(f"    {GRIS}«{h.fragmento}»{FIN}")


def imprimir_verificacion(informe, todo=False):
    """Informe del verificador de respuestas."""
    for aviso in informe.avisos:
        print(f"{AMARILLO}! {aviso}{FIN}")
    if informe.respaldo and informe.respaldo["total"]:
        r = informe.respaldo
        print(f"{GRIS}Respaldo en el documento: {len(r['respaldadas'])} de {r['total']} frases respaldadas, "
              f"{len(r['contradichas'])} contradichas, {len(r['sin_respaldo'])} sin respaldo.{FIN}")
    for h in informe.hallazgos:
        if h.gravedad == "INFO" and not todo:
            continue
        color = COLOR_GRAVEDAD[h.gravedad]
        print(f"  {color}▲ {h.gravedad}{FIN} {h.explicacion}")
        if h.fragmento:
            print(f"    {GRIS}«{h.fragmento[:160]}»{FIN}")


def imprimir_lectura(lectura):
    """Lo que la aduana ha encontrado escondido en un Word o un PDF."""
    if lectura.formato == "texto":
        return
    print(f"{GRIS}Documento {lectura.formato}: {len(lectura.texto)} caracteres en total, "
          f"{len(lectura.visible)} visibles.{FIN}")
    for o in lectura.ocultos:
        color = AMARILLO if o.truco else GRIS
        print(f"  {color}◌ {o.motivo} ({o.lugar}):{FIN} {GRIS}«{o.texto[:140]}»{FIN}")
