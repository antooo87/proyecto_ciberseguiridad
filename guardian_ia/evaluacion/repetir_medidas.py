"""Repite las medidas del Guardián en tu PC (por ejemplo, en el portátil con gráfica) y lo resume todo.

    python evaluacion/repetir_medidas.py                  sin IA: pruebas, escudo y aduana con reglas (1 minuto)
    python evaluacion/repetir_medidas.py --ia             + escudo y aduana con el modelo local de Ollama
    python evaluacion/repetir_medidas.py --agente         + ataque al agente, sin y con Guardián
    python evaluacion/repetir_medidas.py --ia --agente --modelo qwen3.5:9b --veces 10

Todo va a una carpeta nueva, evaluacion/medidas_AAAA-MM-DD_HHMM/, con un resumen.md que dice en qué PC se ha
medido (procesador, gráfica, sistema), cuánto ha tardado cada paso y los resultados. No toca los resultados
guardados del proyecto: así se pueden comparar las medidas de la nube (CPU) con las de tu portátil (GPU).

El ataque al agente arranca él solo el proxy del Guardián en un puerto libre (y lo para al acabar) y repite
cinco configuraciones: trampa directa sin y con Guardián, trampa suave sin Guardián y con "leer sin poder
actuar", y sin trampa con Guardián (para ver que no estorba).
"""

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "evaluacion"))

# nombre del registro: (trampa, opciones del proxy o None si va directo a Ollama)
CONFIGURACIONES_AGENTE = {
    "directo": ("directa", None),
    "reglas": ("directa", []),
    "suave_directo": ("suave", None),
    "suave_reglasleer": ("suave", ["--leer-sospechosos"]),
    "ninguna_reglas": ("ninguna", []),
}


def ejecutar(orden: list[str], registro: Path, entorno: dict | None = None) -> tuple[int, float]:
    """Lanza un paso, guarda todo lo que escribe en un archivo y devuelve (código, segundos)."""
    print(f"  $ {' '.join(orden[1:]) if orden[0] == sys.executable else ' '.join(orden)}", flush=True)
    inicio = time.perf_counter()
    with open(registro, "w", encoding="utf-8", errors="replace") as f:
        codigo = subprocess.call(orden, cwd=RAIZ, stdout=f, stderr=subprocess.STDOUT,
                                 env={**os.environ, "PYTHONUTF8": "1", "NO_COLOR": "1", **(entorno or {})})
    return codigo, round(time.perf_counter() - inicio, 1)


def que_pc() -> list[str]:
    """Procesador, gráfica y sistema, para saber dónde se ha medido."""
    datos = [f"Sistema: {platform.system()} {platform.release()} ({platform.machine()}), "
             f"Python {platform.python_version()}"]
    procesador = ""
    if Path("/proc/cpuinfo").exists():  # Linux
        nombres = [linea.split(":", 1)[1].strip() for linea in Path("/proc/cpuinfo").read_text().splitlines()
                   if linea.startswith("model name")]
        procesador = nombres[0] if nombres else ""
    elif os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as clave:
                procesador = winreg.QueryValueEx(clave, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    datos.append(f"Procesador: {procesador or platform.processor() or 'desconocido'} ({os.cpu_count()} hilos)")
    try:
        grafica = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                  "--format=csv,noheader"], capture_output=True, text=True, timeout=20)
        datos.append(f"Gráfica: {grafica.stdout.strip() or 'ninguna NVIDIA'}")
    except (OSError, subprocess.SubprocessError):
        datos.append("Gráfica: ninguna NVIDIA (o nvidia-smi no está instalado)")
    return datos


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar(url: str, segundos: int = 30) -> bool:
    import httpx
    for _ in range(segundos * 2):
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    return False


def resumen_evaluacion(ruta: Path) -> list[str]:
    if not ruta.exists():
        return [f"(no se ha generado {ruta.name})"]
    res = json.loads(ruta.read_text(encoding="utf-8"))
    lineas = ["| Conjunto | Datos encontrados (recall) | Fuga del escudo | Ataques detectados | Falsas alarmas |",
              "| --- | --- | --- | --- | --- |"]
    for clave, nombre in (("datos", "Desarrollo"), ("ciega", "Prueba ciega")):
        if clave in res:
            e, a = res[clave]["escudo"]["global"], res[clave]["aduana"]
            lineas.append(f"| {nombre} | {100 * e['recall']:.1f} % | {100 * e['tasa_fuga']:.1f} % | "
                          f"{100 * a['deteccion']:.0f} % | {100 * a['falsas_alarmas']:.0f} % |")
    return lineas + ["", f"Tiempo de la evaluación: {res.get('segundos', '?')} s."]


def agente(carpeta: Path, modelo: str, veces: int, temperatura: float, pasos: list) -> None:
    from guardian import config
    logs = carpeta / "agente"
    logs.mkdir()
    prefijo = modelo.split(":")[-1].replace("/", "_")
    for nombre, (trampa, opciones) in CONFIGURACIONES_AGENTE.items():
        orden = [sys.executable, "ejemplos/agente_demo.py", "--modelo", modelo, "--trampa", trampa,
                 "--veces", str(veces), "--temperatura", str(temperatura)]
        proxy = None
        if opciones is None:
            orden.append("--directo")
        else:
            puerto = puerto_libre()
            proxy = subprocess.Popen(
                [sys.executable, "-m", "guardian", "proxy", "--puerto", str(puerto), "--modelo", modelo, *opciones],
                cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={**os.environ, "GUARDIAN_REGISTRO": str(carpeta / "registro"), "GUARDIAN_CLAVE_PROXY": ""})
            if not esperar(f"http://127.0.0.1:{puerto}/salud"):
                proxy.kill()
                pasos.append((f"Agente {nombre}", 1, 0, "el proxy no ha arrancado"))
                continue
            orden += ["--url", f"http://127.0.0.1:{puerto}/v1"]
        try:
            codigo, segundos = ejecutar(orden, logs / f"{prefijo}_{nombre}.log",
                                        {"OLLAMA_HOST": config.OLLAMA_HOST})
        finally:
            if proxy:
                proxy.terminate()
                proxy.wait(timeout=20)
        pasos.append((f"Agente: {nombre}", codigo, segundos, f"agente/{prefijo}_{nombre}.log"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Repite las medidas del Guardián y las resume")
    p.add_argument("--ia", action="store_true", help="medir también el escudo y la aduana con el modelo local")
    p.add_argument("--agente", action="store_true", help="repetir el ataque al agente (necesita Ollama)")
    p.add_argument("--modelo", default=None, help="modelo de Ollama (por defecto el de la configuración)")
    p.add_argument("--veces", type=int, default=10, help="intentos por configuración en el ataque al agente")
    p.add_argument("--temperatura", type=float, default=0.7)
    p.add_argument("--sin-pruebas", action="store_true", help="no pasar las pruebas automáticas")
    args = p.parse_args(argv)

    from guardian import __version__, config
    modelo = args.modelo or config.MODELO
    carpeta = RAIZ / "evaluacion" / f"medidas_{datetime.now():%Y-%m-%d_%H%M}"
    carpeta.mkdir(parents=True, exist_ok=True)
    print(f"Guardando en {carpeta.relative_to(RAIZ)}")
    pasos = []  # (paso, código, segundos, detalle)

    if not args.sin_pruebas:
        codigo, segundos = ejecutar([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                                    carpeta / "pruebas.txt")
        ultima = (carpeta / "pruebas.txt").read_text(encoding="utf-8").strip().splitlines()[-1:] or ["?"]
        pasos.append(("Pruebas automáticas", codigo, segundos, ultima[0]))
    codigo, segundos = ejecutar([sys.executable, "-m", "guardian", "evaluar", "--salida", str(carpeta)],
                                carpeta / "evaluar_reglas.txt")
    pasos.append(("Escudo y aduana, solo reglas", codigo, segundos, "resultados_reglas.md"))
    if args.ia:
        codigo, segundos = ejecutar([sys.executable, "-m", "guardian", "evaluar", "--ia", "--modelo-detector",
                                     modelo, "--salida", str(carpeta)], carpeta / "evaluar_ia.txt")
        pasos.append((f"Escudo y aduana con IA ({modelo})", codigo, segundos, "resultados_ia_*.md"))
    if args.agente:
        agente(carpeta, modelo, args.veces, args.temperatura, pasos)
        codigo, segundos = ejecutar([sys.executable, "evaluacion/medir_eco.py", str(carpeta / "agente"),
                                     "--salida", str(carpeta / "eco_resultados.md")], carpeta / "medir_eco.txt")
        pasos.append(("Eco de la trampa en esas respuestas", codigo, segundos, "eco_resultados.md"))

    # Resumen
    lineas = [f"# Medidas del Guardián IA {__version__} · {datetime.now():%d/%m/%Y %H:%M}", "", *que_pc(),
              f"Modelo: {modelo}" + ("" if args.ia or args.agente else " (no usado: solo reglas)"), "",
              "## Pasos", "", "| Paso | Resultado | Tiempo | Detalle |", "| --- | --- | --- | --- |"]
    lineas += [f"| {paso} | {'✅' if codigo == 0 else '❌ código ' + str(codigo)} | {segundos} s | {detalle} |"
               for paso, codigo, segundos, detalle in pasos]
    lineas += ["", "## Escudo y aduana, solo reglas", "", *resumen_evaluacion(carpeta / "resultados_reglas.json")]
    if args.ia:
        nombre = "resultados_ia_" + modelo.replace(":", "_").replace("/", "_") + ".json"
        lineas += ["", f"## Escudo y aduana con IA ({modelo})", "", *resumen_evaluacion(carpeta / nombre)]
    if args.agente:
        from resumir_agente import tabla
        texto = tabla(carpeta / "agente").replace("10 intentos por configuración", f"{args.veces} intentos por "
                                                  "configuración").replace("`evaluacion/agente/`", "`agente/`")
        lineas += ["", texto.replace("# Ataque", "## Ataque", 1).replace("\n## ", "\n### ").replace(
            "### Ataque", "## Ataque", 1)]
        eco = carpeta / "eco_resultados.md"
        if eco.exists():
            tabla_eco = eco.read_text(encoding="utf-8").split("\n## Frases marcadas")[0].split("\n", 1)[1]
            lineas += ["", "## Eco de la trampa", tabla_eco]
    (carpeta / "resumen.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    print(f"\nResumen en {(carpeta / 'resumen.md').relative_to(RAIZ)}")
    return 0 if all(codigo == 0 for _, codigo, _, _ in pasos) else 1


if __name__ == "__main__":
    sys.exit(main())
