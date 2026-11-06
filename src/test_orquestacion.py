"""Pruebas de orquestación del Bloque 20.

aquí viven las pruebas de manejo de errores. Las de clasificación y
enrutamiento del Bloque 19 están en test_enrutamiento.py, en esta misma
carpeta, y no se repiten aquí.

La suite completa del checklist son las dos juntas, ocho pruebas. Para
correrla entera, desde la raíz del repositorio

    pytest src/ -v

El reparto contra la tabla del checklist del Bloque 20 queda así.

    Clasificación      normalización      test_enrutamiento.py
                       texto vacío        este archivo

    Bifurcación        cada condición     test_enrutamiento.py
                       ruta por defecto   test_enrutamiento.py

    Ruta de destino    prompt distinto    se ve en la corrida real
                       with_fallbacks     este archivo

    Flujo completo     ningún fallo sin   este archivo
                       respuesta

Ninguna prueba llama al modelo. Las que tienen que fallar usan un
RunnableLambda real que lanza la excepción, y no un MagicMock genérico,
porque LangChain puede envolver un mock de una forma que hace que la
aserción no pruebe lo que se cree.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

# pytest se corre desde la raíz del repositorio. Si este archivo se
# ejecutara directamente, Python solo mira la carpeta de este archivo y
# no encontraría src/. Agregar la raíz del repositorio permite las dos
# formas de ejecución.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.enrutamiento import (                            # noqa: E402
    construir_cadena_con_enrutamiento,
    construir_cadena_consulta_segura,
    construir_paso_clasificacion,
    procesar_mensaje_seguro,
)


def test_cadena_consulta_usa_fallback_ante_fallo_del_modelo():
    # Fila "cada ruta de destino" del checklist. Verifica que el
    # fallback se ejecutó de verdad, no solo que no se lanzó una
    # excepción, porque la aserción busca el texto de respaldo.
    def fallar_a_proposito(entrada):
        raise ConnectionError("simulado")

    cadena_consulta_falsa = RunnableLambda(fallar_a_proposito)
    cadena_consulta_segura = construir_cadena_consulta_segura(
        cadena_consulta_falsa
    )

    resultado = cadena_consulta_segura.invoke(
        {"mensaje": "¿cuántos días de feriado me corresponden?"}
    )

    assert "responder tu consulta" in resultado.lower()


def test_procesar_mensaje_seguro_no_propaga_excepciones():
    # Fila "el flujo completo" del checklist. El fallo pasa en la
    # clasificación, o sea antes de que RunnableBranch elija una ruta,
    # así que ningún with_fallbacks de una ruta lo cubre. Solo lo
    # atrapa el try/except de procesar_mensaje_seguro.
    #
    # side_effect va sobre el mock directamente y no sobre .invoke,
    # por el mismo motivo que .return_value en el Bloque 19.
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.side_effect = ConnectionError("simulado")

    cadena_falsa = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
    )

    resultado = procesar_mensaje_seguro(
        cadena_falsa, "mensaje de prueba"
    )

    assert "procesar tu mensaje" in resultado.lower()


def test_clasificacion_no_rompe_con_texto_vacio():
    # Fila "clasificación" del checklist, la parte que dice que un
    # texto vacío o ambiguo no rompa el paso.
    #
    # Esta fila está en la tabla pero no en las cuatro preguntas de
    # verificación de la actividad. Se cubre igual, porque la actividad
    # manda a repasarse contra el checklist completo.
    #
    # Entra un mensaje vacío y el modelo responde vacío. El paso tiene
    # que devolver una cadena vacía sin lanzar nada. Esa cadena vacía
    # después no coincide con ninguna condición de la bifurcación, así
    # que la entrada cae en la ruta por defecto, que ya está probada en
    # test_enrutamiento.py.
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content="")

    resultado = construir_paso_clasificacion(modelo_falso).invoke(
        {"mensaje": ""}
    )

    assert resultado == ""
