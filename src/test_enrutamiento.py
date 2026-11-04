"""Pruebas del enrutamiento condicional del Bloque 19.

Son cinco, que es el piso que pide la lección. Una por cada condición
explícita, que acá son tres, una para la ruta por defecto y una para la
normalización del texto antes de comparar.

Ninguna llama al modelo. La clasificación se reemplaza por un mock, así
cada prueba decide qué categoría entra y verifica a qué ruta salió, sin
depender de cómo clasifique el modelo ese día.

Fíjate que el valor falso se pone con .return_value sobre el mock y no
con .invoke.return_value. LangChain invoca un mock compuesto dentro de
una chain como una función común, así que .invoke.return_value nunca se
consulta y la prueba fallaría por un motivo que no es el que se cree.
Se corre desde la raíz del repositorio con
pytest src/test_enrutamiento.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

# pytest se corre desde la raíz del repositorio. Si este archivo se
# ejecutara directamente, Python solo mira la carpeta de este archivo y
# no encontraría src/. Agregar la raíz del repositorio permite las dos
# formas de ejecución.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.enrutamiento import (                            # noqa: E402
    construir_cadena_con_enrutamiento,
    construir_paso_clasificacion,
)


def test_enrutamiento_va_a_cadena_clausula():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "clausula"
    cadena_clausula_falsa = MagicMock()
    cadena_clausula_falsa.return_value = "respuesta de clausula"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_clausula=cadena_clausula_falsa,
    )
    resultado = cadena.invoke(
        {"mensaje": "La jornada será de 48 horas semanales."}
    )

    assert cadena_clausula_falsa.called
    assert resultado == "respuesta de clausula"


def test_enrutamiento_va_a_cadena_contrato():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "contrato"
    cadena_contrato_falsa = MagicMock()
    cadena_contrato_falsa.return_value = "respuesta de contrato"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_contrato=cadena_contrato_falsa,
    )
    resultado = cadena.invoke(
        {"mensaje": "CONTRATO DE TRABAJO. Entre la empresa y don..."}
    )

    assert cadena_contrato_falsa.called
    assert resultado == "respuesta de contrato"


def test_enrutamiento_va_a_cadena_ley():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "ley"
    cadena_ley_falsa = MagicMock()
    cadena_ley_falsa.return_value = "respuesta de ley"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_ley=cadena_ley_falsa,
    )
    resultado = cadena.invoke(
        {"mensaje": "Artículo 66. En el caso de muerte de un hijo..."}
    )

    assert cadena_ley_falsa.called
    assert resultado == "respuesta de ley"


def test_enrutamiento_usa_default_ante_categoria_desconocida():
    # La ruta por defecto es la más fácil de dejar sin probar, porque
    # no tiene una condición explícita que recuerde que existe. Y es
    # justo la que se ejecuta ante cualquier categoría no prevista.
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "categoria_inventada"
    cadena_consulta_falsa = MagicMock()
    cadena_consulta_falsa.return_value = "respuesta por defecto"

    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_consulta=cadena_consulta_falsa,
    )
    resultado = cadena.invoke({"mensaje": "una entrada ambigua"})

    assert cadena_consulta_falsa.called
    assert resultado == "respuesta por defecto"


def test_clasificacion_normaliza_antes_de_comparar():
    # Esta no verifica el enrutamiento, verifica el paso intermedio por
    # separado. El modelo falso devuelve un AIMessage real y no un
    # MagicMock con content simulado, porque StrOutputParser necesita
    # leer .content de un mensaje genuino.
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content=" Clausula \n")

    resultado = construir_paso_clasificacion(modelo_falso).invoke(
        {"mensaje": "La jornada será de 48 horas semanales."}
    )

    assert resultado == "clausula"
