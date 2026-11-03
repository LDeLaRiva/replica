"""Pruebas de la cadena de tres pasos.

No tocan la API. El modelo se reemplaza por uno falso, así que la
suite corre en segundos y no gasta cuota, igual que en test_cliente.py
del Módulo 2.

Dos detalles que la lección advierte y que no son evidentes.

    El side_effect va en modelo_falso directamente, no en
    modelo_falso.invoke. Al componer un objeto suelto dentro de una
    cadena con el operador de barra, LangChain lo llama como
    modelo_falso(...), nunca como modelo_falso.invoke(...).

    Cada valor del side_effect tiene que ser un AIMessage de verdad,
    no un MagicMock con content. StrOutputParser necesita un objeto
    de mensaje real para poder sacarle el texto.

Se corre desde la raíz del repositorio con
`pytest src/test_cadena_tres_pasos.py -v`
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

# La raíz se agrega a la ruta de búsqueda, igual que en las otras
# pruebas del proyecto, para importar con el mismo prefijo src.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.cadena_tres_pasos import construir_cadena          # noqa: E402


def respuestas_falsas():
    """Las tres salidas que simula el modelo, en orden.

    La primera imita el paso de extracción, la segunda el de
    respuesta y la tercera el de simplificación.
    """
    return [
        AIMessage(content="¿Cuántos días de permiso corresponden por "
                          "el fallecimiento del padre?"),
        AIMessage(content="Corresponden cuatro días hábiles de "
                          "permiso pagado, según el artículo 66 del "
                          "Código del Trabajo."),
        AIMessage(content="Usted tiene derecho a cuatro días pagados "
                          "para ausentarse del trabajo."),
    ]


def test_cadena_conecta_los_tres_pasos():
    """La cadena llama al modelo tres veces y devuelve lo último.

    Si alguien quitara un paso, el conteo bajaría a dos. Si alguien
    cambiara el orden del encadenamiento, el texto final no sería el
    del tercer paso.
    """
    modelo_falso = MagicMock()
    modelo_falso.side_effect = respuestas_falsas()

    cadena = construir_cadena(modelo_falso)
    resultado = cadena.invoke({"mensaje": "mi papá falleció el jueves"})

    assert modelo_falso.call_count == 3
    assert "cuatro días pagados" in resultado


def test_la_cadena_devuelve_texto_plano():
    """El resultado es un str, no un objeto de respuesta.

    Es la comprobación que la lección pide hacer con print(type(...))
    mientras se desarrolla. Si a algún paso le faltara
    StrOutputParser, esto se caería, y ese es un error que de otro
    modo pasa en silencio.
    """
    modelo_falso = MagicMock()
    modelo_falso.side_effect = respuestas_falsas()

    cadena = construir_cadena(modelo_falso)
    resultado = cadena.invoke({"mensaje": "mi papá falleció el jueves"})

    assert isinstance(resultado, str)


def test_cada_paso_recibe_lo_que_salio_del_anterior():
    """El texto de un paso aparece dentro del prompt del siguiente.

    Es lo que distingue una cadena de verdad de tres llamadas sueltas
    disfrazadas. Se revisan los prompts que recibió el modelo falso.
    """
    modelo_falso = MagicMock()
    modelo_falso.side_effect = respuestas_falsas()

    cadena = construir_cadena(modelo_falso)
    cadena.invoke({"mensaje": "mi papá falleció el jueves"})

    prompts = [str(llamada.args[0]) for llamada in
               modelo_falso.call_args_list]

    assert "mi papá falleció el jueves" in prompts[0]
    assert "fallecimiento del padre" in prompts[1]
    assert "artículo 66" in prompts[2]
