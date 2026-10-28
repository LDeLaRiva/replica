"""Pruebas unitarias del cliente modular.

En cada prueba se reemplaza la parte que habla con el proveedor por
una respuesta escrita. La suite corre en milisegundos, no gasta
tokens y no depende de que el servicio esté disponible.

Lo simulado es la respuesta del servicio. Las funciones que se prueban
son las de verdad, las de src.cliente y las de src.consumir_gemini.

Las rutas de los patch nombran el módulo donde la pieza se usa, no la
librería en general. Por eso dicen src.consumir_gemini.requests.post
y src.cliente.time.sleep, con el mismo prefijo src. que usa el resto
del proyecto. Así Python carga cada archivo una sola vez, en vez de
dos veces bajo dos nombres distintos.

Se corre desde la raíz del repositorio con
`pytest src/test_cliente.py -v`
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# La raíz se agrega a la ruta de búsqueda, igual que en cliente.py y
# en ensayo_rate_limit.py. Con esto la prueba importa con el mismo
# prefijo src. que usa el resto del proyecto, y Python carga cada
# archivo una sola vez en vez de dos bajo dos nombres distintos.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import src.cliente as cliente                            # noqa: E402
from src.cliente import (                                # noqa: E402
    con_reintento,
    consultar_modelo,
    registrar_costo,
)
from src.consumir_gemini import (                        # noqa: E402
    PRECIO_ENTRADA,
    PRECIO_SALIDA,
    enviar_peticion,
)

# Los tres argumentos que pide enviar_peticion. La dirección es la
# real, la misma que arma armar_peticion, y se puede escribir entera
# porque en este proyecto la credencial no viaja en la dirección sino
# en la cabecera. Esa credencial sí es falsa, por razones obvias.
#
# Ninguno de los tres llega a usarse, porque requests.post está
# reemplazado en cada prueba y el corte ocurre ahí.
URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
       "gemini-3.5-flash-lite:generateContent")
CABECERAS = {"x-goog-api-key": "clave_de_prueba"}
CUERPO = {
    "systemInstruction": {"parts": [{"text": "Responde en español."}]},
    "contents": [{"parts": [{"text": "¿Cuál es la capital de Chile?"}]}],
}

# La forma que tiene una respuesta de Gemini cuando todo sale bien.
RESPUESTA_SIMULADA = {
    "candidates": [{"content": {"parts": [{"text": "Santiago."}]}}],
    "usageMetadata": {
        "promptTokenCount": 18,
        "candidatesTokenCount": 9,
        "totalTokenCount": 27,
    },
}

# Un uso con números redondos, para que el costo esperado se pueda
# calcular a mano y la prueba no dependa de una respuesta real.
USO_CONOCIDO = {
    "usageMetadata": {
        "promptTokenCount": 1000,
        "candidatesTokenCount": 2000,
    }
}
COSTO_CONOCIDO = (1000 * PRECIO_ENTRADA) + (2000 * PRECIO_SALIDA)


@pytest.fixture(autouse=True)
def reiniciar_costo_total():
    """Deja el acumulado en cero antes de cada prueba.

    costo_total_sesion lo comparte todo el módulo. Si una prueba lo
    dejara con un valor distinto de cero, la siguiente podría fallar,
    o peor, pasar por la razón equivocada.

    El autouse hace que corra sola, sin que ninguna prueba la llame.
    """
    cliente.costo_total_sesion = 0.0
    yield


# ===== enviar_peticion ================================================

def test_enviar_peticion_credencial_invalida():
    """Un 401 y un 403 se clasifican como ValueError.

    Son problemas de credencial o de permiso. Reintentarlos no los
    arregla, por eso llevan un tipo que con_reintento no atrapa.
    """
    for codigo in (401, 403):
        respuesta_falsa = Mock(status_code=codigo, text="sin permiso",
                               headers={})
        with patch("src.consumir_gemini.requests.post",
                   return_value=respuesta_falsa):
            with pytest.raises(ValueError, match=str(codigo)):
                enviar_peticion(URL, CABECERAS, CUERPO)


def test_enviar_peticion_limite_de_uso():
    """Un 429 y un 500 o mayor se clasifican como TimeoutError.

    Los dos se resuelven esperando, el primero porque es el límite de
    uso y el segundo porque el proveedor se cayó. Ese tipo es el único
    que con_reintento vuelve a intentar.
    """
    for codigo in (429, 500, 503):
        respuesta_falsa = Mock(status_code=codigo, text="no disponible",
                               headers={})
        with patch("src.consumir_gemini.requests.post",
                   return_value=respuesta_falsa):
            with pytest.raises(TimeoutError, match=str(codigo)):
                enviar_peticion(URL, CABECERAS, CUERPO)


def test_enviar_peticion_exito():
    """Una respuesta exitosa devuelve el JSON tal cual.

    Sin esta prueba, un arreglo en la clasificación de errores podría
    romper el camino bueno sin que ninguna de las otras lo avise.
    """
    respuesta_falsa = Mock(status_code=200, text="", headers={})
    respuesta_falsa.json.return_value = RESPUESTA_SIMULADA

    with patch("src.consumir_gemini.requests.post",
               return_value=respuesta_falsa):
        resultado = enviar_peticion(URL, CABECERAS, CUERPO)

    assert resultado == RESPUESTA_SIMULADA


# ===== con_reintento ==================================================

def test_con_reintento_reintenta_en_timeout():
    """Ante un TimeoutError vuelve a intentar, y lo logra.

    No se comprueba cuántos segundos esperó, porque el jitter los hace
    distintos en cada corrida. Solo que la espera ocurrió.
    """
    llamadas = {"n": 0}

    def falla_la_primera_vez():
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise TimeoutError("[técnico] El servicio respondió 429.")
        return "listo"

    with patch("src.cliente.time.sleep") as espera_falsa:
        resultado = con_reintento(falla_la_primera_vez)

    assert resultado == "listo"
    assert llamadas["n"] == 2
    espera_falsa.assert_called_once()


def test_con_reintento_no_reintenta_value_error():
    """Ante cualquier otro tipo no reintenta, deja pasar el error.

    Insistir en algo que no es momentáneo solo gastaría tiempo y
    peticiones. Se comprueba que llamó una sola vez y que ni siquiera
    llegó a esperar.
    """
    llamadas = {"n": 0}

    def falla_por_configuracion():
        llamadas["n"] += 1
        raise ValueError("credencial inválida")

    with patch("src.cliente.time.sleep") as espera_falsa:
        with pytest.raises(ValueError):
            con_reintento(falla_por_configuracion)

    assert llamadas["n"] == 1
    espera_falsa.assert_not_called()


def test_con_reintento_agota_intentos():
    """Al agotar los intentos deja propagarse el error original.

    El match del 429 es lo que confirma que sale el error de siempre,
    con su mensaje, y no uno nuevo inventado por con_reintento.
    """
    llamadas = {"n": 0}

    def siempre_falla():
        llamadas["n"] += 1
        raise TimeoutError("[técnico] El servicio respondió 429.")

    with patch("src.cliente.time.sleep"):
        with pytest.raises(TimeoutError, match="429"):
            con_reintento(siempre_falla, intentos=3)

    assert llamadas["n"] == 3


# ===== registrar_costo ================================================

def test_registrar_costo_calcula_bien():
    """Calcula el costo correcto a partir de un uso conocido.

    Los precios de entrada y de salida son distintos, así que el
    cálculo multiplica cada conteo por el suyo. No usa el total.
    """
    assert registrar_costo(USO_CONOCIDO) == COSTO_CONOCIDO


def test_registrar_costo_acumula():
    """Cada costo se suma al total de la sesión.

    Dos respuestas iguales tienen que dejar el acumulado en el doble.
    El fixture lo dejó en cero antes de empezar.
    """
    registrar_costo(USO_CONOCIDO)
    registrar_costo(USO_CONOCIDO)

    assert cliente.costo_total_sesion == COSTO_CONOCIDO * 2


# ===== consultar_modelo ===============================================

def test_consultar_modelo_convierte_error():
    """Un TimeoutError agotado sale como RuntimeError.

    El cambio de tipo dice que esto ya no se arregla esperando, porque
    esperar es justo lo que acaba de fallar tres veces.
    """
    agotado = TimeoutError("[usuario] No hay conexión.\n"
                           "[técnico] ConnectionError. sin red")

    with patch("src.cliente.con_reintento", side_effect=agotado):
        with pytest.raises(RuntimeError, match="intentos"):
            consultar_modelo("pregunta de prueba")


def test_consultar_modelo_propaga_value_error():
    """Un ValueError sale sin que el cliente lo toque.

    Ya trae un mensaje claro desde enviar_peticion. El match confirma
    que es ese error y no otro que se haya colado antes.
    """
    credencial = ValueError("[usuario] Credencial inválida.\n"
                            "[técnico] El servicio respondió 401.")

    with patch("src.cliente.con_reintento", side_effect=credencial):
        with pytest.raises(ValueError, match="401"):
            consultar_modelo("pregunta de prueba")