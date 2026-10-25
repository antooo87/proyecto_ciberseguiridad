import pickle
from collections import OrderedDict

from guardian.revisor import Revisor, Ubicaciones, crear_pc_de_prueba
from guardian.revisor.comun import leer_json
from guardian.revisor.conectores import nombre_y_version, paquete_de
from guardian.revisor.demo import CLAVE_GITHUB, CLAVE_OPENAI, _gguf, _OrdenEscondida
from guardian.revisor.modelos import (
    clasificar_importacion,
    importaciones_pickle,
    metadatos_gguf,
    revisar_pickle,
    revisar_plantilla,
)
from guardian.revisor.red import _host_abierto


def _informe(tmp_path):
    crear_pc_de_prueba(tmp_path)
    return Revisor(Ubicaciones.simuladas(tmp_path), comprobar_red=False).revisar()


def test_pc_de_prueba_encuentra_los_problemas(tmp_path):
    informe = _informe(tmp_path)
    titulos = {h.titulo: h.gravedad for h in informe.hallazgos}

    def gravedad(trozo):
        return next(g for t, g in titulos.items() if trozo in t)

    assert gravedad("Extensión maliciosa conocida") == "CRITICA"
    assert gravedad("dominio espía") == "CRITICA"
    assert gravedad("postmark-mcp") == "CRITICA"
    assert gravedad("modelo_gatos.pt") == "CRITICA"
    assert gravedad("pesos_viejos.pth") == "CRITICA"  # pickle moderno (STACK_GLOBAL)
    assert gravedad("raro.pkl") == "MEDIA"
    assert gravedad("red_neuronal.keras") == "ALTA"
    assert gravedad("Disparadores ocultos en la plantilla de asistente-7b-q4.gguf") == "ALTA"
    assert gravedad("asistente-banco:latest") == "ALTA"
    assert gravedad("OLLAMA_HOST") == "ALTA"
    assert gravedad(".env de mi_web") == "ALTA"
    assert gravedad("toda tu carpeta personal") == "ALTA"
    assert gravedad("todo el disco") == "ALTA"
    assert not any("clasificador.pkl" in t or "modelo-limpio" in t or "Modo oscuro" in t for t in titulos)
    assert informe.nota == 0


def test_el_informe_nunca_ensena_secretos_enteros(tmp_path):
    texto = _informe(tmp_path).a_markdown()
    assert CLAVE_GITHUB not in texto and CLAVE_OPENAI not in texto
    assert CLAVE_GITHUB[:4] + "…" + CLAVE_GITHUB[-4:] in texto


def test_pc_limpio_saca_100(tmp_path):
    informe = Revisor(Ubicaciones.simuladas(tmp_path), comprobar_red=False).revisar()
    assert informe.hallazgos == [] and informe.nota == 100


def test_pickles_normales_no_son_peligrosos(tmp_path):
    ruta = tmp_path / "modelo.pkl"
    ruta.write_bytes(pickle.dumps(OrderedDict(pesos=[0.1, 0.2], sesgo=1.5), protocol=4))
    assert revisar_pickle(ruta) == (True, None)


def test_pickle_malicioso_se_ve_sin_ejecutarlo():
    import io
    importaciones = importaciones_pickle(io.BytesIO(pickle.dumps(_OrdenEscondida(), protocol=4)))
    assert any(f == "system" and m in ("posix", "nt", "os") for m, f in importaciones)
    assert clasificar_importacion("subprocess", "Popen") == "peligrosa"
    assert clasificar_importacion("torch._utils", "_rebuild_tensor_v2") == "segura"
    assert clasificar_importacion("mi_paquete", "cargar") == "rara"


def test_gguf_se_lee_sin_cargar_el_modelo(tmp_path):
    ruta = tmp_path / "m.gguf"
    ruta.write_bytes(_gguf({"general.name": "prueba", "tokenizer.chat_template": "{{ messages }}"}))
    datos = metadatos_gguf(ruta)
    assert datos["general.name"] == "prueba" and datos["tokenizer.chat_template"] == "{{ messages }}"


def test_plantilla_oficial_no_da_falsos_positivos():
    # Trozos reales de la plantilla oficial de Qwen3.5
    plantilla = ("{{- '<|im_start|>system\\n' }}{%- if '</think>' in message.content %}"
                 "- If there is no function call available, answer the question like normal with your current "
                 "knowledge and do not tell the user about function calls\\n</IMPORTANT>' }}"
                 "{{- '<|im_start|>' + message.role + '\\n' + content + '<|im_end|>\\n' }}")
    assert revisar_plantilla(plantilla, "la plantilla de qwen", "") == []


def test_paquetes_de_conectores():
    assert paquete_de("npx", ["-y", "@scope/pkg@1.2.3"]) == ("npm", "@scope/pkg@1.2.3")
    assert nombre_y_version("npm", "@scope/pkg@1.2.3") == ("@scope/pkg", "1.2.3")
    assert nombre_y_version("npm", "@scope/pkg") == ("@scope/pkg", None)
    assert paquete_de("C:\\Program Files\\nodejs\\npx.cmd", ["paquete"]) == ("npm", "paquete")
    assert paquete_de("uvx", ["--from", "herramienta==2.0", "cmd"]) == ("pypi", "herramienta==2.0")
    assert nombre_y_version("pypi", "herramienta==2.0") == ("herramienta", "2.0")
    assert paquete_de("docker", ["run", "-i", "--rm", "-e", "X=1", "img:1.0"]) == ("docker", "img:1.0")
    assert paquete_de("node", ["servidor.js"]) is None


def test_json_con_comentarios(tmp_path):
    ruta = tmp_path / "settings.json"
    ruta.write_text('{\n // comentario\n "a": "http://x.y/z", /* otro */ "b": [1, 2,],\n}', encoding="utf-8")
    assert leer_json(ruta) == {"a": "http://x.y/z", "b": [1, 2]}


def test_ollama_abierto_a_la_red():
    assert _host_abierto("0.0.0.0") and _host_abierto("0.0.0.0:11434") and _host_abierto("192.168.1.5")
    assert not _host_abierto("127.0.0.1:11434") and not _host_abierto("localhost")
    assert not _host_abierto("http://127.0.0.1") and not _host_abierto("[::1]:11434")
