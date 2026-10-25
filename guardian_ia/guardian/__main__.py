"""Programa de terminal del Guardián.

Uso (desde la carpeta del proyecto, con el entorno virtual activado):
    python -m guardian demo                   enseña los cuatro módulos en un minuto (no necesita Ollama)
    python -m guardian estado                 comprueba que la IA está lista
    python -m guardian chat                   chat protegido con la IA
    python -m guardian chat --ia              ... y además usa la IA local para detectar nombres, direcciones,
                                              contraseñas escritas a mano y ataques en documentos
    python -m guardian proteger "texto"       enseña qué vería la IA (no necesita Ollama)
    python -m guardian aduana documento.pdf   revisa un documento (texto, Word o PDF) en busca de prompt injection
    python -m guardian verificar "respuesta"  revisa una respuesta de cualquier IA (ChatGPT, Gemini...)
    python -m guardian revisar                revisa la IA instalada en tu PC (añade --demo para un PC de prueba)
    python -m guardian proxy                  pone el Guardián delante de cualquier programa que use la IA
    python -m guardian evaluar                mide el escudo y la aduana con los textos de prueba
"""

import argparse
import json
import os
import sys
import tempfile

from . import __version__, config
from .terminal import (
    AMARILLO,
    AZUL,
    COLOR_GRAVEDAD,
    FIN,
    GRIS,
    NEGRITA,
    ROJO,
    VERDE,
    imprimir_informe,
    imprimir_lectura,
    imprimir_verificacion,
    resumen,
)


def _cliente_local(modelo=None):
    from .ia import ClienteIA
    return ClienteIA(modelo or config.MODELO_DETECTOR)


def _crear_escudo(con_ia: bool, modelo_detector: str | None = None):
    from .escudo import Escudo
    if not con_ia:
        return Escudo()
    from .escudo.detector_ia import DetectorIA
    return Escudo(detector_ia=DetectorIA(_cliente_local(modelo_detector)))


def _crear_aduana(con_ia: bool, modelo_detector: str | None = None):
    from .aduana import Aduana
    if not con_ia:
        return Aduana()
    from .aduana.juez_ia import JuezIA
    return Aduana(juez=JuezIA(_cliente_local(modelo_detector)))


def _crear_verificador(respaldo: bool, comprobar_enlaces: bool, modelo_detector: str | None = None):
    from .verificador import JuezRespaldo, Verificador
    juez = JuezRespaldo(_cliente_local(modelo_detector)) if respaldo else None
    return Verificador(juez, comprobar_enlaces)


def cmd_estado(args):
    from .ia import crear_cliente
    ia = crear_cliente(args.proveedor, args.modelo, args.url)
    estado = ia.estado()
    print(f"{VERDE if estado['ok'] else ROJO}IA que responde: {estado['detalle']}{FIN}")
    if estado.get("modelos"):
        print(f"{GRIS}Modelos disponibles: {', '.join(estado['modelos'])}{FIN}")
    if not ia.es_local:
        detector = _cliente_local().estado()
        print(f"{VERDE if detector['ok'] else AMARILLO}Detector local: {detector['detalle']}{FIN}")
    print(f"{GRIS}Ollama local en {config.OLLAMA_HOST}{FIN}")
    return 0 if estado["ok"] else 1


def cmd_proteger(args):
    escudo = _crear_escudo(args.ia)
    texto = args.texto if args.texto else sys.stdin.read()
    resultado = escudo.proteger(texto)
    for aviso in resultado.avisos:
        print(f"{AMARILLO}! {aviso}{FIN}")
    print(f"{NEGRITA}Lo que vería la IA:{FIN}\n{resultado.protegido}\n")
    print(f"{GRIS}Tapados: {resumen(resultado.resumen())}{FIN}")


def _leer(ruta):
    """Lee texto, Word o PDF. Devuelve None (y lo explica) si no se puede."""
    from .aduana import ErrorLectura, leer
    try:
        return leer(ruta)
    except (OSError, ErrorLectura) as e:
        print(f"{ROJO}No puedo leer {ruta}: {e}{FIN}")
        return None


def cmd_aduana(args):
    lectura = _leer(args.archivo)
    if lectura is None:
        return 1
    imprimir_lectura(lectura)
    informe = _crear_aduana(args.ia).analizar(lectura)
    imprimir_informe(informe)
    return 2 if informe.peligroso else 0


def cmd_verificar(args):
    from .aduana import leer_documento
    respuesta = leer_documento(args.archivo) if args.archivo else (args.texto or sys.stdin.read())
    lectura = _leer(args.documento) if args.documento else None
    documento = lectura.visible if lectura else None
    verificador = _crear_verificador(bool(documento), args.comprobar_enlaces)
    informe = verificador.revisar(respuesta, contexto=documento or "", documento=documento)
    color = {"OK": VERDE, "AVISO": AMARILLO, "PELIGRO": ROJO}[informe.nivel]
    print(f"{NEGRITA}Resultado: {color}{informe.nivel}{FIN}")
    imprimir_verificacion(informe, todo=True)
    if informe.nivel == "OK" and not informe.hallazgos:
        print(f"{GRIS}No he encontrado comandos peligrosos, enlaces falsos ni intentos de sacar datos.{FIN}")
    return 2 if informe.nivel == "PELIGRO" else 0


def cmd_chat(args):
    from .ia import ErrorIA, crear_cliente
    from .nucleo import Guardian

    try:
        ia = crear_cliente(args.proveedor, args.modelo, args.url)
    except ErrorIA as e:
        print(f"{ROJO}{e}{FIN}")
        return 1
    estado = ia.estado()
    if not estado["ok"]:
        print(f"{ROJO}{estado['detalle']}{FIN}")
        return 1
    guardian = Guardian(ia, escudo=_crear_escudo(args.ia, args.modelo_detector),
                        aduana=_crear_aduana(args.ia, args.modelo_detector),
                        verificador=_crear_verificador(args.respaldo, args.comprobar_enlaces, args.modelo_detector))
    donde = "en tu PC" if ia.es_local else f"FUERA de tu PC ({ia.host}), solo recibe datos tapados"
    print(f"{NEGRITA}Guardián IA {__version__}{FIN} · modelo {ia.modelo} {donde} · "
          f"detección con IA: {'sí' if args.ia else 'no (solo reglas)'}")
    print(f"{GRIS}Comandos: /doc RUTA (adjuntar documento) · /nueva · /ver (mostrar u ocultar lo que ve la IA) · /salir{FIN}\n")
    ver = True
    documento = None
    while True:
        try:
            mensaje = input(f"{AZUL}Tú > {FIN}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not mensaje:
            continue
        if mensaje in ("/salir", "/exit"):
            break
        if mensaje == "/nueva":
            guardian.nueva_conversacion()
            print(f"{GRIS}Conversación nueva: la bóveda de datos se ha vaciado.{FIN}")
            continue
        if mensaje == "/ver":
            ver = not ver
            continue
        if mensaje.startswith("/doc"):
            documento = _leer(mensaje[4:].strip().strip('"'))
            if documento:
                imprimir_lectura(documento)
                print(f"{GRIS}Documento adjuntado ({len(documento.visible)} caracteres visibles). "
                      f"Se enviará con tu próxima pregunta.{FIN}")
            continue

        try:
            r = guardian.preguntar(mensaje, documento)
        except ErrorIA as e:
            print(f"{ROJO}{e}{FIN}")
            continue
        documento = None
        if r.aduana:
            imprimir_informe(r.aduana)
        if r.bloqueado:
            print(f"{ROJO}{r.respuesta}{FIN}\n")
            continue
        for aviso in r.avisos:
            print(f"{AMARILLO}! {aviso}{FIN}")
        if ver:
            print(f"{GRIS}🛡  La IA ha visto: {r.mensaje_protegido[:500]}{'…' if len(r.mensaje_protegido) > 500 else ''}")
            print(f"   Tapados: {resumen(r.escudo.resumen())}{FIN}")
        print(f"{VERDE}IA > {FIN}{r.respuesta}")
        if r.verificacion and r.verificacion.hallazgos:
            imprimir_verificacion(r.verificacion)
        print(f"{GRIS}({r.segundos:.1f} s){FIN}\n")
    return 0


def cmd_revisar(args):
    from .revisor import Revisor, Ubicaciones, crear_pc_de_prueba
    if args.demo:
        try:
            raiz = crear_pc_de_prueba(tempfile.mkdtemp(prefix="pc_de_prueba_"))
        except OSError as e:  # p. ej. el antivirus borra el modelo con código escondido que se crea a propósito
            print(f"{ROJO}No he podido crear el PC de prueba: {e}. Si ha sido el antivirus, es normal: lleva a "
                  f"propósito un modelo con código escondido.{FIN}")
            return 1
        print(f"{GRIS}PC de prueba creado en {raiz} (todo falso e inofensivo){FIN}\n",
              file=sys.stderr if args.json else sys.stdout)
        ubic = Ubicaciones.simuladas(raiz)
    elif args.raiz:
        ubic = Ubicaciones.simuladas(args.raiz)
    else:
        ubic = Ubicaciones.del_sistema()
    informe = Revisor(ubic, args.carpeta or [], comprobar_red=not args.sin_red).revisar()
    if args.informe:
        with open(args.informe, "w", encoding="utf-8") as f:
            f.write(informe.a_markdown())
    if args.json:
        print(json.dumps(informe.a_dict(), ensure_ascii=False, indent=2))
        return 0
    nota = informe.nota
    color = VERDE if nota >= 80 else AMARILLO if nota >= 50 else ROJO
    print(f"{NEGRITA}Salud de la IA de tu PC: {color}{nota}/100{FIN}  "
          + " · ".join(f"{COLOR_GRAVEDAD[g]}{n} {g.lower()}{FIN}" for g, n in informe.cuenta().items() if n))
    r = informe.resumen
    print(f"{GRIS}Revisado: {r.get('extensiones_revisadas', 0)} extensiones "
          f"({', '.join(r.get('navegadores', [])) or 'sin navegadores'}), "
          f"{sum(len(v) for v in r.get('conectores', {}).values())} conectores MCP, "
          f"{sum(r.get('archivos_de_modelo', {}).values())} archivos de modelo, "
          f"{len(r.get('modelos_ollama', []))} modelos de Ollama. ({informe.segundos:.1f} s){FIN}\n")
    for h in informe.hallazgos:
        color = COLOR_GRAVEDAD[h.gravedad]
        print(f"{color}● {h.gravedad}{FIN} {NEGRITA}{h.titulo}{FIN}")
        print(f"  {h.detalle}")
        print(f"  {VERDE}→ {h.recomendacion}{FIN}")
        if h.ruta:
            print(f"  {GRIS}{h.ruta}{FIN}")
        print()
    if not informe.hallazgos:
        print(f"{VERDE}No he encontrado nada raro. ¡Bien!{FIN}")
    if args.informe:
        print(f"{GRIS}Informe guardado en {args.informe}{FIN}")
    return 0


def cmd_proxy(args):
    from .proxy import ProxyGuardian, ServidorGuardian, preguntar_en_consola
    proveedor = (args.proveedor or config.PROVEEDOR).lower()
    if proveedor == "ollama-cloud":
        url, clave_ia = args.url or "https://ollama.com/v1", os.environ.get("OLLAMA_API_KEY")
        if not clave_ia:
            print(f"{ROJO}Para usar Ollama en la nube guarda tu clave en OLLAMA_API_KEY.{FIN}")
            return 1
    elif proveedor == "openai":
        url, clave_ia = args.url or config.URL_OPENAI, os.environ.get("GUARDIAN_API_KEY")
    else:
        url, clave_ia = args.url or f"{config.OLLAMA_HOST}/v1", None
    if args.leer_sospechosos and args.permitir_acciones_tras_sospecha:
        print(f"{ROJO}--leer-sospechosos solo es seguro si las acciones siguen bloqueadas: quita "
              f"--permitir-acciones-tras-sospecha.{FIN}")
        return 1
    proxy = ProxyGuardian(url, clave_ia, args.modelo, escudo=_crear_escudo(args.ia, args.modelo_detector),
                          aduana=_crear_aduana(args.ia, args.modelo_detector),
                          bloquear_tras_sospecha=not args.permitir_acciones_tras_sospecha,
                          herramientas_bloqueadas=args.bloquear_herramienta or (), sin_pensar=args.sin_pensar,
                          marcar_datos=args.marcar_datos, seguir_tras_bloqueo=not args.parar_tras_bloqueo,
                          confirmar=preguntar_en_consola if args.confirmar is not None else None,
                          herramientas_a_confirmar=args.confirmar or (), leer_sospechosos=args.leer_sospechosos)
    try:
        servidor = ServidorGuardian(proxy, args.puerto, args.clave)
    except OSError as e:
        print(f"{ROJO}No puedo abrir el puerto {args.puerto}: {e}{FIN}")
        return 1
    print(f"{NEGRITA}Guardián IA {__version__} en modo proxy{FIN}")
    print(f"  Escucha en:  {VERDE}http://127.0.0.1:{args.puerto}/v1{FIN}   (solo este PC)")
    print(f"  Reenvía a:   {url}" + (f"  · modelo forzado: {args.modelo}" if args.modelo else ""))
    print(f"  Detección con IA local: {'sí' if args.ia else 'no (solo reglas)'} · "
          f"bloquear acciones tras leer algo sospechoso: {'no' if args.permitir_acciones_tras_sospecha else 'sí'}")
    if args.confirmar is not None:
        extra = f" y siempre por: {', '.join(args.confirmar)}" if args.confirmar else ""
        print(f"  Te preguntaré en esta ventana antes de dejar pasar una acción dudosa{extra}")
    if args.leer_sospechosos:
        print("  Lo sospechoso que lea un agente le llega a la IA sin las partes ocultas, pero sin poder hacer acciones")
    if args.parar_tras_bloqueo:
        print("  Tras bloquear una acción, la respuesta se queda en el aviso (la IA no sigue)")
    if args.marcar_datos:
        print(f"  Resultados de herramientas señalados para la IA (spotlighting): {args.marcar_datos}")
    if args.clave:
        print("  Clave: los programas tienen que mandar 'Authorization: Bearer <tu clave>' (en OpenAI es la api_key)")
    print(f"{GRIS}En tu programa de IA pon como dirección (base URL) la de arriba. Ctrl+C para parar.{FIN}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nProxy parado.")
    finally:
        servidor.server_close()
    return 0


def cmd_demo(args):
    from .demo import ejecutar
    return ejecutar(_crear_escudo(args.ia, args.modelo_detector), _crear_aduana(args.ia, args.modelo_detector),
                    con_ia=args.ia, pausa=args.pausa)


def cmd_evaluar(args):
    from .evaluacion import evaluar_todo
    return evaluar_todo(con_ia=args.ia, modelo=args.modelo_detector, limite=args.limite, conjunto=args.conjunto)


def main(argv=None):
    # Si la salida va a un archivo o a una tubería en Windows (cp1252), los símbolos (●, 🛑...) no caben:
    # mejor un "?" que un error.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure") and (flujo.encoding or "").lower().replace("-", "") != "utf8":
            flujo.reconfigure(errors="replace")
    p = argparse.ArgumentParser(prog="python -m guardian", description="Guardián IA: usa la IA sin regalarle tus datos")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="comando", required=True)

    def opciones_ia(s):
        s.add_argument("--proveedor", default=None, choices=["ollama", "ollama-cloud", "openai"],
                       help="dónde está la IA que responde (por defecto ollama, en tu PC)")
        s.add_argument("--modelo", default=None)
        s.add_argument("--url", default=None, help="dirección del servidor de IA si no es la de siempre")

    s = sub.add_parser("demo", help="enseña los cuatro módulos en un minuto con ejemplos preparados")
    s.add_argument("--ia", action="store_true", help="usar también la IA local en el escudo y la aduana")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--pausa", action="store_true", help="esperar a que pulses Enter entre módulo y módulo")
    s.set_defaults(func=cmd_demo)

    s = sub.add_parser("estado", help="comprueba la IA y el modelo")
    opciones_ia(s)
    s.set_defaults(func=cmd_estado)

    s = sub.add_parser("chat", help="chat protegido con la IA")
    opciones_ia(s)
    s.add_argument("--ia", action="store_true", help="usar también la IA local para detectar")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--respaldo", action="store_true", help="comprobar si las respuestas salen del documento adjunto")
    s.add_argument("--comprobar-enlaces", action="store_true", help="abrir los enlaces nuevos para ver si existen")
    s.set_defaults(func=cmd_chat)

    s = sub.add_parser("proteger", help="muestra qué vería la IA")
    s.add_argument("texto", nargs="?")
    s.add_argument("--ia", action="store_true")
    s.set_defaults(func=cmd_proteger)

    s = sub.add_parser("aduana", help="revisa un documento (texto, Word o PDF) contra prompt injection")
    s.add_argument("archivo")
    s.add_argument("--ia", action="store_true", help="pedir también la opinión del juez IA")
    s.set_defaults(func=cmd_aduana)

    s = sub.add_parser("verificar", help="revisa una respuesta de cualquier IA")
    s.add_argument("texto", nargs="?")
    s.add_argument("--archivo", help="leer la respuesta de un archivo")
    s.add_argument("--documento", help="documento en el que debería basarse la respuesta (usa la IA local)")
    s.add_argument("--comprobar-enlaces", action="store_true", help="abrir los enlaces para ver si existen")
    s.set_defaults(func=cmd_verificar)

    s = sub.add_parser("revisar", help="revisa la IA instalada en tu PC")
    s.add_argument("--demo", action="store_true", help="crear y revisar un PC de prueba lleno de problemas")
    s.add_argument("--raiz", help="revisar una carpeta como si fuera un PC (para pruebas)")
    s.add_argument("--carpeta", action="append", help="carpeta extra con modelos o proyectos (se puede repetir)")
    s.add_argument("--sin-red", action="store_true", help="no comprobar los puertos de red")
    s.add_argument("--json", action="store_true", help="sacar el resultado en JSON")
    s.add_argument("--informe", help="guardar el informe en un archivo .md")
    s.set_defaults(func=cmd_revisar)

    s = sub.add_parser("proxy", help="pone el Guardián delante de cualquier programa que use la IA (API tipo OpenAI)")
    opciones_ia(s)
    s.add_argument("--puerto", type=int, default=8787)
    s.add_argument("--clave", default=os.environ.get("GUARDIAN_CLAVE_PROXY"),
                   help="clave que deben mandar los programas (por defecto, la variable GUARDIAN_CLAVE_PROXY)")
    s.add_argument("--ia", action="store_true", help="usar también la IA local para detectar")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--bloquear-herramienta", action="append", help="nombre de una herramienta que nunca se deja usar")
    s.add_argument("--permitir-acciones-tras-sospecha", action="store_true",
                   help="no bloquear las acciones que pide la IA después de leer algo sospechoso")
    s.add_argument("--sin-pensar", action="store_true",
                   help="pedir al modelo que no 'piense' en voz alta (reasoning_effort=none): mucho más rápido")
    s.add_argument("--confirmar", nargs="*", metavar="HERRAMIENTA",
                   help="preguntarte en esta ventana antes de dejar pasar una acción dudosa (a un destino que no has "
                        "escrito tú) en vez de bloquearla; con nombres de herramientas, preguntar siempre por esas")
    s.add_argument("--leer-sospechosos", action="store_true",
                   help="dejar que la IA lea (desinfectado) un resultado de herramienta con riesgo ALTO para poder "
                        "contestar, en vez de bloquearlo entero; las acciones siguen bloqueadas")
    s.add_argument("--parar-tras-bloqueo", action="store_true",
                   help="tras bloquear todas las acciones de una respuesta, devolver solo el aviso (sin pedirle a la "
                        "IA que conteste sin ellas)")
    s.add_argument("--marcar-datos", choices=["delimitar", "marcas"],
                   help="spotlighting: señalar a la IA lo que viene de herramientas, entre etiquetas con un código "
                        "al azar (delimitar) o con una marca entre cada palabra (marcas)")
    s.set_defaults(func=cmd_proxy)

    s = sub.add_parser("evaluar", help="mide el Guardián con los textos de prueba")
    s.add_argument("--ia", action="store_true", help="incluir la detección con IA (necesita Ollama; tarda)")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--limite", type=int, default=None, help="usar solo los N primeros textos")
    s.add_argument("--conjunto", choices=["todos", "datos", "ciega"], default="todos")
    s.set_defaults(func=cmd_evaluar)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
