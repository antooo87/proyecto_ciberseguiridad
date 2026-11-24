"""Programa de terminal del Guardián.

Uso (desde la carpeta del proyecto, con el entorno virtual activado):
    python -m guardian demo                   enseña los cuatro módulos en un minuto (no necesita Ollama)
    python -m guardian estado                 comprueba que la IA está lista
    python -m guardian chat                   chat protegido con la IA
    python -m guardian chat --ia              ... y además usa la IA local para detectar nombres, direcciones,
                                              contraseñas escritas a mano y ataques en documentos
    python -m guardian proteger "texto"       enseña qué vería la IA (no necesita Ollama)
    python -m guardian mejorar "pregunta"     te propone dos versiones mejores de tu pregunta para un chatbot
    python -m guardian estafa "mensaje"       ¿es una estafa este SMS, correo o WhatsApp? Y qué hacer
    python -m guardian aprende                juego: ¿lo detectas? Aprende a ver las estafas antes de picar
    python -m guardian aduana documento.pdf   revisa un documento (texto, Word, PowerPoint, Excel o PDF) en busca de
                                              prompt injection
    python -m guardian verificar "respuesta"  revisa una respuesta de cualquier IA (ChatGPT, Gemini...)
    python -m guardian revisar                revisa la IA instalada en tu PC (añade --demo para un PC de prueba)
    python -m guardian proxy                  pone el Guardián delante de cualquier programa que use la IA
    python -m guardian informe                lo que ha hecho el Guardián estos días (sin enseñar ningún dato)
    python -m guardian web                    abre la web (solo en este PC)
    python -m guardian app                    todo en uno: la web en su propia ventana y el servicio de la extensión
    python -m guardian evaluar                mide el escudo y la aduana con los textos de prueba
"""

import argparse
import json
import os
import re
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


def cmd_doctor(args):
    from .doctor import AVISO, FALLO, OK, revisar
    comprobaciones = revisar(comprobar_ollama=not args.sin_ollama)
    marca = {OK: f"{VERDE}✓", AVISO: f"{AMARILLO}!", FALLO: f"{ROJO}✗"}
    print(f"{NEGRITA}Guardián IA {__version__} · comprobando que todo está listo{FIN}\n")
    for c in comprobaciones:
        print(f"{marca[c.estado]} {c.nombre}{FIN}: {c.detalle}")
        if c.arreglo and c.estado != OK:
            print(f"    {VERDE}→ {c.arreglo}{FIN}")
    fallos = sum(c.estado == FALLO for c in comprobaciones)
    avisos = sum(c.estado == AVISO for c in comprobaciones)
    print()
    if fallos:
        print(f"{ROJO}Hay {fallos} cosa(s) que arreglar antes de usar el Guardián.{FIN}")
    elif avisos:
        print(f"{AMARILLO}Funciona, con {avisos} aviso(s).{FIN} Prueba: python -m guardian demo")
    else:
        print(f"{VERDE}Todo listo.{FIN} Prueba: python -m guardian demo")
    return 1 if fallos else 0


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


def cmd_mejorar(args):
    from .mejorador import Mejorador
    texto = args.texto if args.texto else sys.stdin.read()
    if not texto.strip():
        print(f'{AMARILLO}Escribe tu pregunta: python -m guardian mejorar "hola, ¿me ayudas con...?"{FIN}')
        return 1
    cliente = _cliente_local(args.modelo_detector) if args.ia else None
    mejora = Mejorador(_crear_escudo(args.ia, args.modelo_detector), cliente).mejorar(texto)
    if args.json:
        print(json.dumps(mejora.a_dict(), ensure_ascii=False, indent=2))
        return 0
    color = VERDE if mejora.nota >= 80 else AMARILLO if mejora.nota >= 50 else ROJO
    print(f"{NEGRITA}Nota de tu pregunta: {color}{mejora.nota}/100{FIN}")
    for aviso in mejora.avisos:
        print(f"{AMARILLO}! {aviso}{FIN}")
    if mejora.urgente:
        print(f"{NEGRITA}{ROJO}🚑 No esperes a la respuesta de la IA:{FIN}")
        for paso in mejora.urgente:
            print(f"  {ROJO}!{FIN} {paso}")
    if mejora.estafa:
        print(f"{ROJO}🚨 {mejora.estafa}{FIN}")
    if mejora.consejos:
        print(f"{NEGRITA}Qué le falta:{FIN}")
        for consejo in mejora.consejos:
            print(f"  • {consejo}")
    for n, version in enumerate(mejora.versiones, 1):
        print(f"\n{NEGRITA}{AZUL}Opción {n} · {version.titulo}{FIN} {GRIS}({version.por_que}){FIN}")
        print(version.texto)
    hechas = ("reescritas por la IA de tu PC" if mejora.con_ia else
              "hechas con reglas; añade --ia para que las reescriba la IA de tu PC")
    print(f"\n{GRIS}Copia la que más te guste y pégala en tu chatbot ({hechas}).{FIN}")
    return 0


_FIN_DE_FRASE = re.compile(r"(?<=[.!?])\s")


def _cmd_bandeja(carpeta: str, como_json: bool) -> int:
    """Revisa todos los correos (.eml) y mensajes (.txt) de una carpeta y los ordena del más peligroso al menos."""
    from .estafas import revisar_bandeja
    try:
        revisados = revisar_bandeja(carpeta)
    except NotADirectoryError as e:
        print(f"{ROJO}{e}{FIN}")
        return 1
    if como_json:
        print(json.dumps([r.a_dict() for r in revisados], ensure_ascii=False, indent=2))
    else:
        if not revisados:
            print(f"{AMARILLO}No hay correos (.eml) ni mensajes (.txt) en {carpeta}.{FIN}")
            return 0
        icono = {"ALTO": f"{ROJO}● ESTAFA  {FIN}", "MEDIO": f"{AMARILLO}● DUDOSO  {FIN}", "BAJO": f"{VERDE}● NORMAL  {FIN}"}
        print(f"{NEGRITA}Bandeja revisada: {carpeta}{FIN}\n")
        for r in revisados:
            if r.informe is None:
                print(f"{GRIS}○ NO LEÍDO {r.archivo}: {r.error}{FIN}")
                continue
            print(f"{icono[r.informe.nivel]}{NEGRITA}{r.asunto or r.archivo}{FIN}")
            print(f"           {GRIS}{r.de or r.archivo}{FIN}")
            if r.informe.tipo:
                print(f"           Parece: {r.informe.tipo}")
            for senal in r.informe.senales[:2]:
                primera_frase = _FIN_DE_FRASE.split(senal.explicacion)[0]
                print(f"           {GRIS}· {primera_frase}{FIN}")
        altos = sum(1 for r in revisados if r.informe and r.informe.nivel == "ALTO")
        dudosos = sum(1 for r in revisados if r.informe and r.informe.nivel == "MEDIO")
        print(f"\n{NEGRITA}{len(revisados)} mensajes: {ROJO}{altos} casi seguro estafas{FIN}{NEGRITA}, "
              f"{AMARILLO}{dudosos} dudosos{FIN}{NEGRITA}, {len(revisados) - altos - dudosos} sin señales.{FIN}")
        print(f"{GRIS}Para ver las pistas de uno: python -m guardian estafa --archivo CARPETA/ARCHIVO.eml{FIN}")
    return 2 if any(r.informe and r.informe.nivel == "ALTO" for r in revisados) else 0


def cmd_estafa(args):
    from .estafas import analizar, analizar_correo
    if args.carpeta:
        return _cmd_bandeja(args.carpeta, args.json)
    correo = None
    if args.archivo and args.archivo.lower().endswith(".eml"):
        try:
            with open(args.archivo, "rb") as f:
                informe, correo = analizar_correo(f.read())
        except OSError as e:
            print(f"{ROJO}No puedo leer {args.archivo}: {e}{FIN}")
            return 1
        texto = correo.texto or correo.asunto
    elif args.archivo:
        lectura = _leer(args.archivo)
        if lectura is None:
            return 1
        texto = lectura.texto
    else:
        texto = args.texto if args.texto else sys.stdin.read()
    if not texto.strip():
        print(f'{AMARILLO}Pega el mensaje: python -m guardian estafa "Correos: su paquete está retenido..."{FIN}')
        return 1
    if correo is None:
        informe = analizar(texto)
    else:
        print(f"{GRIS}De: {correo.de}\nAsunto: {correo.asunto}{FIN}\n")
    if args.json:
        print(json.dumps(informe.a_dict(), ensure_ascii=False, indent=2))
        return 0
    color = {"ALTO": ROJO, "MEDIO": AMARILLO, "BAJO": VERDE}[informe.nivel]
    print(f"{NEGRITA}{color}{informe.veredicto}{FIN} {GRIS}(puntuación {informe.puntuacion}){FIN}")
    if informe.tipo:
        print(f"{NEGRITA}Parece: {informe.tipo}{FIN}")
    if informe.senales:
        print(f"\n{NEGRITA}Las pistas (para que aprendas a verlas):{FIN}")
        for senal in informe.senales:
            print(f"  {color}●{FIN} {senal.explicacion}")
            print(f"    {GRIS}«{senal.fragmento[:120]}»{FIN}")
    if informe.si_ya_lo_hiciste:
        print(f"\n{NEGRITA}{ROJO}Si ya lo has hecho, ahora mismo:{FIN}")
        for paso in informe.si_ya_lo_hiciste:
            print(f"  ! {paso}")
    print(f"\n{NEGRITA}Qué hacer:{FIN}")
    for paso in informe.que_hacer:
        print(f"  • {paso}")
    return 2 if informe.nivel == "ALTO" else 0


def cmd_aprende(args):
    from .escuela import corregir, mezclados
    mensajes = mezclados(args.cuantos)
    print(f"{NEGRITA}🎓 ¿Lo detectas?{FIN} Te enseño {len(mensajes)} mensajes. Para cada uno, escribe "
          f"{NEGRITA}e{FIN} si crees que es una estafa o {NEGRITA}f{FIN} si es de fiar (q para salir).\n")
    aciertos = respondidas = 0
    for n, mensaje in enumerate(mensajes, 1):
        print(f"{NEGRITA}{AZUL}{n}/{len(mensajes)} · {mensaje.canal} de {mensaje.remitente}{FIN}")
        print(f"  {mensaje.texto}\n")
        respuesta = ""
        while respuesta not in ("e", "f", "q"):
            try:
                respuesta = input("¿Estafa (e) o de fiar (f)? ").strip().lower()[:1]
            except EOFError:
                respuesta = "q"
        if respuesta == "q":
            break
        acierto, informe = corregir(mensaje, respuesta == "e")
        aciertos += acierto
        respondidas += 1
        verdad = "ERA UNA ESTAFA" if mensaje.es_estafa else "ERA DE FIAR"
        print(f"{VERDE + '✓ ¡Bien!' if acierto else ROJO + '✗ Esta vez no.'}{FIN} {NEGRITA}{verdad}{FIN}. "
              f"{mensaje.leccion}")
        for senal in informe.senales[:4]:
            print(f"  {GRIS}● {senal.explicacion}{FIN}")
        print()
    print(f"{NEGRITA}Has acertado {aciertos} de {respondidas}.{FIN} Si dudas con un mensaje de verdad: "
          f'python -m guardian estafa "el mensaje"')
    return 0


def _leer(ruta):
    """Lee texto, Word, PowerPoint, Excel o PDF. Devuelve None (y lo explica) si no se puede."""
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
    # leido: todo lo que pudo leer la IA, también lo escondido, para ver si repite lo que pedía una trampa
    informe = verificador.revisar(respuesta, contexto=documento or "", documento=documento,
                                  leido=lectura.texto if lectura else None)
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


def cmd_escanear(args):
    from .escaner import DATOS, ILEGIBLE, LIMPIO, TRAMPA, escanear
    try:
        informe = escanear(args.carpeta, _crear_escudo(args.ia, args.modelo_detector),
                           _crear_aduana(args.ia, args.modelo_detector))
    except NotADirectoryError as e:
        print(f"{ROJO}{e}{FIN}")
        return 1
    if args.informe:
        with open(args.informe, "w", encoding="utf-8") as f:
            f.write(informe.a_markdown())
    if args.json:
        print(json.dumps(informe.a_dict(), ensure_ascii=False, indent=2))
        return 2 if informe.cuenta()[TRAMPA] else 0
    color = {TRAMPA: ROJO, DATOS: AMARILLO, ILEGIBLE: GRIS, LIMPIO: VERDE}
    from .tipos import contar
    saltados = _cuantos(informe.saltados, "archivo de otro tipo", "archivos de otros tipos")
    print(f"{NEGRITA}Carpeta {informe.carpeta}{FIN}: {len(informe.archivos)} documentos revisados "
          f"{GRIS}({saltados} sin revisar, por ejemplo imágenes; {informe.segundos:.1f} s){FIN}")
    print("  " + " · ".join(f"{color[v]}{n} {v.lower()}{FIN}" for v, n in informe.cuenta().items() if n) + "\n")
    for a in informe.archivos:
        detalle = a.error or ", ".join(
            ([contar(a.datos)] if a.datos else [])
            + ([f"aduana: riesgo {a.riesgo} ({a.puntuacion})"] if a.riesgo != "NINGUNO" else [])
            + ([f"{a.ocultos} trozo(s) de texto escondido"] if a.ocultos else []))
        print(f"{color[a.veredicto]}● {a.veredicto:<17}{FIN} {a.ruta}  {GRIS}{detalle}{FIN}")
    if informe.cuenta()[TRAMPA]:
        print(f"\n{ROJO}No subas a una IA los documentos con TRAMPA:{FIN} mira cada uno con "
              f"python -m guardian aduana ARCHIVO.")
    if informe.cuenta()[DATOS]:
        print(f"{AMARILLO}Los que llevan DATOS PERSONALES, compártelos anonimizados:{FIN} "
              f"python -m guardian anonimizar ARCHIVO.")
    if args.informe:
        print(f"{GRIS}Informe guardado en {args.informe}{FIN}")
    return 2 if informe.cuenta()[TRAMPA] else 0


def cmd_anonimizar(args):
    from pathlib import Path

    from .aduana import ErrorLectura
    from .escaner import anonimizar
    try:
        texto, resultado, quitados = anonimizar(args.archivo, _crear_escudo(args.ia, args.modelo_detector))
    except (OSError, ErrorLectura) as e:
        print(f"{ROJO}No puedo leer {args.archivo}: {e}{FIN}")
        return 1
    for aviso in resultado.avisos:
        print(f"{AMARILLO}! {aviso}{FIN}")
    origen = Path(args.archivo)
    salida = Path(args.salida) if args.salida else origen.with_name(f"{origen.stem}_anonimizado.txt")
    if salida.resolve() == origen.resolve():
        print(f"{ROJO}La copia no puede sobrescribir el original.{FIN}")
        return 1
    salida.write_text(texto, encoding="utf-8")
    print(f"{NEGRITA}Copia anonimizada guardada en {salida}{FIN}")
    print(f"{GRIS}Tapados: {resumen(resultado.resumen())}"
          + (f" · quitados {quitados} trozo(s) de texto escondido" if quitados else "") + f"{FIN}")
    if not args.ia:
        print(f"{GRIS}Sin --ia, los nombres, direcciones y contraseñas escritas a mano no se tapan.{FIN}")
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


def cmd_servicio(args):
    from .servicio import ServicioGuardian, ServidorServicio
    servicio = ServicioGuardian(_crear_escudo(args.ia, args.modelo_detector),
                                _crear_aduana(args.ia, args.modelo_detector),
                                cliente_mejorador=_cliente_local(args.modelo_detector) if args.ia else None)
    try:
        servidor = ServidorServicio(servicio, args.puerto, args.clave)
    except OSError as e:
        print(f"{ROJO}No puedo abrir el puerto {args.puerto}: {e}{FIN}")
        return 1
    print(f"{NEGRITA}Guardián IA {__version__} · servicio para la extensión del navegador{FIN}")
    print(f"  Escucha en: {VERDE}http://127.0.0.1:{args.puerto}{FIN}   (solo este PC)")
    print(f"  Detección con IA local: {'sí' if args.ia else 'no (solo reglas)'}")
    if args.ocultar_clave:
        print("  Clave: la de siempre (guardada en tu carpeta de usuario, .guardian/servicio.json)")
    else:
        print(f"  Clave para la extensión: {AMARILLO}{servidor.clave}{FIN}")
        print(f"  {GRIS}Pégala una vez en las opciones de la extensión. Se guarda en .guardian/servicio.json, en tu "
              f"carpeta de usuario.{FIN}")
    print(f"{GRIS}Deja esta ventana abierta mientras uses la extensión. Ctrl+C para parar.{FIN}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServicio parado. La bóveda con tus datos se ha borrado.")
    finally:
        servidor.server_close()
    return 0


def cmd_demo(args):
    from .demo import ejecutar
    return ejecutar(_crear_escudo(args.ia, args.modelo_detector), _crear_aduana(args.ia, args.modelo_detector),
                    con_ia=args.ia, pausa=args.pausa)


def cmd_evaluar(args):
    from .evaluacion import evaluar_todo
    return evaluar_todo(con_ia=args.ia, modelo=args.modelo_detector, limite=args.limite, conjunto=args.conjunto,
                        salida=args.salida)


def _ruta_web():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent / "app_web.py"


def _orden_web(puerto: int, sin_navegador: bool) -> list[str] | None:
    """La orden para arrancar la web solo en este PC (None, y lo explica, si falta algo)."""
    app = _ruta_web()
    if not app.exists():
        print(f"{ROJO}No encuentro la web ({app}).{FIN} Viene con el código del proyecto: descárgalo de GitHub.")
        return None
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print(f"{ROJO}Falta Streamlit.{FIN} Instálalo con: pip install streamlit   (o con instalar.ps1 en Windows)")
        return None
    return [sys.executable, "-m", "streamlit", "run", str(app), "--server.address", "127.0.0.1",
            "--server.port", str(puerto), "--browser.gatherUsageStats", "false",
            "--server.headless", "true" if sin_navegador else "false"]


def cmd_web(args):
    """Abre la web (app_web.py) solo en este PC, se lance desde la carpeta que se lance."""
    import subprocess
    orden = _orden_web(args.puerto, args.sin_navegador)
    if orden is None:
        return 1
    print(f"{VERDE}Web del Guardián en http://127.0.0.1:{args.puerto}{FIN} {GRIS}(solo este PC puede abrirla; "
          f"Ctrl+C para cerrarla){FIN}", flush=True)
    try:
        return subprocess.call(orden, cwd=_ruta_web().parent)  # desde su carpeta: usa su .streamlit/config.toml
    except KeyboardInterrupt:
        return 0


def _esperar_web(url: str, segundos: float = 45) -> bool:
    """Espera a que la web conteste (sin pasar por ningún proxy: es este mismo PC)."""
    import time
    import urllib.request
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        try:
            with abridor.open(f"{url}/_stcore/health", timeout=1) as respuesta:
                if respuesta.status == 200:
                    return True
        except OSError:
            time.sleep(0.4)
    return False


def _abrir_como_app(url: str) -> str:
    """Edge o Chrome en modo aplicación (una ventana propia, sin barra de direcciones); si no, el navegador normal."""
    import shutil
    import subprocess
    import webbrowser
    from pathlib import Path
    candidatos = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidatos += [Path(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                               Path(base, "Google", "Chrome", "Application", "chrome.exe")]
    else:
        candidatos += [shutil.which(n) for n in ("microsoft-edge", "google-chrome", "chromium", "chromium-browser")]
    for navegador in candidatos:
        if navegador and Path(navegador).exists():
            subprocess.Popen([str(navegador), f"--app={url}", "--window-size=1320,900"])
            return Path(navegador).stem
    webbrowser.open(url)
    return "navegador"


def cmd_app(args):
    """Todo en uno para quien no usa la terminal (es lo que abre el acceso directo «Guardián IA»)."""
    import subprocess
    import threading

    from .servicio import ServicioGuardian, ServidorServicio
    orden = _orden_web(args.puerto, sin_navegador=True)
    if orden is None:
        return 1
    print(f"{NEGRITA}🛡️  Guardián IA {__version__}{FIN}")
    servidor = None
    try:
        servicio = ServicioGuardian(_crear_escudo(args.ia, args.modelo_detector),
                                    _crear_aduana(args.ia, args.modelo_detector),
                                    cliente_mejorador=_cliente_local(args.modelo_detector) if args.ia else None)
        servidor = ServidorServicio(servicio, args.puerto_servicio, silencioso=True)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        print(f"  {VERDE}✓{FIN} Servicio para la extensión del navegador encendido (127.0.0.1:{args.puerto_servicio})")
        print(f"    {GRIS}Clave para pegar UNA vez en las opciones de la extensión:{FIN} {AMARILLO}{servidor.clave}{FIN}")
    except OSError:
        print(f"  {GRIS}• El servicio de la extensión ya estaba encendido (o el puerto {args.puerto_servicio} está "
              f"ocupado).{FIN}")
    url = f"http://127.0.0.1:{args.puerto}"
    web = subprocess.Popen(orden, cwd=_ruta_web().parent)
    try:
        if _esperar_web(url):
            como = "" if args.sin_ventana else _abrir_como_app(url)
            print(f"  {VERDE}✓{FIN} Web abierta en {url}" + (f" ({como})" if como else "") + f" {GRIS}(solo este PC){FIN}")
        else:
            print(f"  {AMARILLO}!{FIN} La web tarda en arrancar: ábrela tú en {url}")
        print(f"{GRIS}Deja esta ventana abierta mientras uses el Guardián. Para cerrarlo todo: Ctrl+C o cierra la "
              f"ventana.{FIN}", flush=True)
        return web.wait()
    except KeyboardInterrupt:
        web.terminate()
        return 0
    finally:
        if servidor is not None:
            servidor.shutdown()
            servidor.server_close()


def _cuantos(n: int, uno: str, varios: str) -> str:
    """1 mensaje, 3 mensajes."""
    return f"{n} {uno if n == 1 else varios}"


def cmd_informe(args):
    from datetime import datetime

    from .actividad import AVISOS, leer_registro
    actividad = leer_registro(args.carpeta, args.dias)
    if args.json:
        print(json.dumps(actividad.a_dict(), ensure_ascii=False, indent=2))
        return 0
    periodo = f"los últimos {args.dias} días" if args.dias else "todo el registro"
    if not actividad.sucesos:
        print(f"Todavía no hay nada en el registro ({periodo}, carpeta {actividad.carpeta}). Se llena al usar el "
              "chat, la extensión del navegador o el proxy.")
        return 0
    donde = " · ".join(f"{d} {n}" for d, n in actividad.donde.most_common())
    print(f"{NEGRITA}Lo que ha hecho el Guardián{FIN} del {actividad.desde:%d/%m/%Y} al {actividad.hasta:%d/%m/%Y} "
          f"{GRIS}({periodo}: {_cuantos(actividad.sucesos, 'suceso', 'sucesos')} · {donde}){FIN}")
    print(f"{GRIS}Leído de {actividad.carpeta}/: el registro nunca guarda tus datos, solo cuántos y de qué tipo.{FIN}\n")

    print(f"{NEGRITA}Datos tapados antes de llegar a la IA:{FIN} {VERDE}{actividad.datos_tapados}{FIN}"
          + (f" en {_cuantos(actividad.mensajes_con_datos, 'mensaje', 'mensajes')}" if actividad.datos else ""))
    if actividad.datos:
        from .tipos import nombre
        nombres = {tipo: nombre(tipo, n) for tipo, n in actividad.datos.items()}
        ancho, maximo = max(map(len, nombres.values())), max(actividad.datos.values())
        for tipo, n in actividad.datos.most_common():
            print(f"  {nombres[tipo]:<{ancho}} {n:>5}  {AZUL}{'█' * max(1, round(24 * n / maximo))}{FIN}")

    trampas, bloqueados = actividad.documentos_con_trampa, actividad.documentos_bloqueados
    print(f"{NEGRITA}Documentos o textos pegados con trampas:{FIN} "
          + (f"{ROJO}{trampas}{FIN} ({_cuantos(bloqueados, 'bloqueado', 'bloqueados')}, "
             f"{_cuantos(trampas - bloqueados, 'desinfectado', 'desinfectados')} antes de dárselos a la IA)" if trampas
             else f"{VERDE}ninguno{FIN}"))

    r = actividad.respuestas
    if sum(r.values()):
        print(f"{NEGRITA}Respuestas de la IA revisadas:{FIN} {sum(r.values())} · {VERDE}{r['OK']} OK{FIN} · "
              f"{AMARILLO}{r['AVISO']} AVISO{FIN} · {ROJO}{r['PELIGRO']} PELIGRO{FIN}")
        for tipo, n in actividad.avisos.most_common(8):
            print(f"  {AMARILLO}▲{FIN} {n} × {AVISOS.get(tipo, tipo)}")

    if actividad.acciones_bloqueadas or actividad.resultados_bloqueados:
        acciones = ", ".join(f"{h} ×{n}" for h, n in actividad.acciones_bloqueadas.most_common())
        bloqueadas = sum(actividad.acciones_bloqueadas.values())
        print(f"{NEGRITA}Agentes:{FIN} {ROJO}{_cuantos(bloqueadas, 'acción bloqueada', 'acciones bloqueadas')}{FIN}"
              + (f" ({acciones})" if acciones else "")
              + f" · {_cuantos(actividad.resultados_bloqueados, 'resultado', 'resultados')} de herramienta con "
              "trampa que no se le dio a la IA")

    if actividad.ultimos and args.ultimos:
        print(f"\n{NEGRITA}Lo último importante:{FIN}")
        for u in actividad.ultimos[:args.ultimos]:
            fecha = datetime.fromisoformat(u["fecha"])
            print(f"  {GRIS}{fecha:%d/%m %H:%M}{FIN}  {u['donde']:<10}{ROJO if u['grave'] else ''}{u['que']}{FIN}")
    if actividad.lineas_rotas:
        print(f"\n{AMARILLO}! {actividad.lineas_rotas} líneas del registro no se han podido leer "
              f"(¿editadas a mano?).{FIN}")
    return 0


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

    s = sub.add_parser("doctor", help="comprueba Python, el entorno, las librerías y Ollama, y dice cómo arreglarlos")
    s.add_argument("--sin-ollama", action="store_true", help="no comprobar Ollama")
    s.set_defaults(func=cmd_doctor)

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

    s = sub.add_parser("mejorar", help="dos versiones mejores de tu pregunta para un chatbot (y qué le falta)")
    s.add_argument("texto", nargs="?", help="tu pregunta (si no la pones, se lee de la entrada)")
    s.add_argument("--ia", action="store_true", help="que la reescriba la IA de tu PC (Ollama)")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--json", action="store_true", help="sacar el resultado en JSON")
    s.set_defaults(func=cmd_mejorar)

    s = sub.add_parser("estafa", help="¿es una estafa este SMS, correo o WhatsApp? Las pistas y qué hacer")
    s.add_argument("texto", nargs="?", help="el mensaje (si no lo pones, se lee de la entrada)")
    s.add_argument("--archivo", help="leer el mensaje de un archivo (.eml, .txt, .html, Word, PDF...)")
    s.add_argument("--carpeta", help="revisar todos los correos (.eml) y mensajes (.txt) de una carpeta")
    s.add_argument("--json", action="store_true", help="sacar el resultado en JSON")
    s.set_defaults(func=cmd_estafa)

    s = sub.add_parser("aprende", help="juego: ¿lo detectas? Aprende a ver las estafas antes de picar")
    s.add_argument("--cuantos", type=int, default=6, help="cuántos mensajes (por defecto 6; 0 = todos)")
    s.set_defaults(func=cmd_aprende)

    s = sub.add_parser("aduana", help="revisa un documento (texto, Word, PowerPoint, Excel o PDF) contra prompt injection")
    s.add_argument("archivo")
    s.add_argument("--ia", action="store_true", help="pedir también la opinión del juez IA")
    s.set_defaults(func=cmd_aduana)

    s = sub.add_parser("verificar", help="revisa una respuesta de cualquier IA")
    s.add_argument("texto", nargs="?")
    s.add_argument("--archivo", help="leer la respuesta de un archivo")
    s.add_argument("--documento", help="documento, web o correo que leyó la IA: se mira si la respuesta repite "
                   "una trampa escondida en él y, con la IA local, si se basa en él")
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

    s = sub.add_parser("escanear", help="revisa una carpeta antes de dársela a una IA: datos personales y trampas")
    s.add_argument("carpeta")
    s.add_argument("--ia", action="store_true", help="usar también la IA local (nombres, direcciones, ataques)")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--json", action="store_true", help="sacar el resultado en JSON")
    s.add_argument("--informe", help="guardar el informe en un archivo .md")
    s.set_defaults(func=cmd_escanear)

    s = sub.add_parser("anonimizar", help="crea una copia de un documento con los datos tapados, para compartirla")
    s.add_argument("archivo")
    s.add_argument("--ia", action="store_true", help="tapar también nombres, direcciones y contraseñas (IA local)")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--salida", help="dónde guardar la copia (por defecto, NOMBRE_anonimizado.txt al lado)")
    s.set_defaults(func=cmd_anonimizar)

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

    s = sub.add_parser("servicio", help="servicio local para la extensión del navegador (ChatGPT, Claude, Gemini...)")
    s.add_argument("--puerto", type=int, default=8788)
    s.add_argument("--clave", default=os.environ.get("GUARDIAN_CLAVE_SERVICIO"),
                   help="clave propia (por defecto se crea una al azar y se guarda en ~/.guardian/servicio.json)")
    s.add_argument("--ia", action="store_true", help="usar también la IA local (nombres, direcciones, ataques)")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--ocultar-clave", action="store_true", help="no enseñar la clave (por ejemplo, en una presentación)")
    s.set_defaults(func=cmd_servicio)

    s = sub.add_parser("web", help="abre la web del Guardián en el navegador (solo en este PC)")
    s.add_argument("--puerto", type=int, default=8501)
    s.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador solo")
    s.set_defaults(func=cmd_web)

    s = sub.add_parser("app", help="todo en uno: la web en su propia ventana y el servicio para la extensión")
    s.add_argument("--puerto", type=int, default=8501, help="puerto de la web (por defecto 8501)")
    s.add_argument("--puerto-servicio", type=int, default=8788, help="puerto del servicio de la extensión")
    s.add_argument("--ia", action="store_true", help="usar también la IA local (nombres, direcciones, ataques)")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--sin-ventana", action="store_true", help="no abrir la ventana (por ejemplo, para probarlo)")
    s.set_defaults(func=cmd_app)

    s = sub.add_parser("informe", help="lo que ha hecho el Guardián estos días: datos tapados, trampas y avisos")
    s.add_argument("--dias", type=int, default=30, help="cuántos días mirar (0 = todo el registro; por defecto 30)")
    s.add_argument("--carpeta", default=None, help=f"carpeta del registro (por defecto {config.CARPETA_REGISTRO})")
    s.add_argument("--ultimos", type=int, default=10, help="cuántos sucesos recientes enseñar (0 = ninguno)")
    s.add_argument("--json", action="store_true", help="sacar el resumen en JSON")
    s.set_defaults(func=cmd_informe)

    s = sub.add_parser("evaluar", help="mide el Guardián con los textos de prueba")
    s.add_argument("--ia", action="store_true", help="incluir la detección con IA (necesita Ollama; tarda)")
    s.add_argument("--modelo-detector", default=None)
    s.add_argument("--limite", type=int, default=None, help="usar solo los N primeros textos")
    s.add_argument("--conjunto", choices=["todos", "datos", "ciega"], default="todos")
    s.add_argument("--salida", default=None, help="carpeta para los resultados (por defecto evaluacion/, sustituyendo "
                                                  "los guardados)")
    s.set_defaults(func=cmd_evaluar)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
