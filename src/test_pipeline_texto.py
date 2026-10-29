"""Pruebas unitarias del pipeline de texto.

Estas pruebas no necesitan reemplazo. Las funciones de
src.pipeline_texto reciben un texto y devuelven un texto, una lista o
un conteo, sin tocar la red ni depender de nada externo,
se llaman directo con un valor escrito a mano.

Es la diferencia con test_cliente.py, donde sí había que reemplazar
requests.post porque enviar_peticion sale a internet.

Se corre desde la raíz del repositorio con
`pytest src/test_pipeline_texto.py -v`
"""

import sys
from collections import Counter
from pathlib import Path

import pytest

# La raíz se agrega a la ruta de búsqueda, igual que en cliente.py y en
# test_cliente.py. Con esto la prueba importa con el mismo prefijo src.
# que usa el resto del proyecto.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.pipeline_texto import (                          # noqa: E402
    limpiar_texto,
    procesar_texto,
    vectorizar,
)


# ===== procesar_texto =================================================

def test_procesar_texto_normaliza_mayusculas_y_puntuacion():
    """Un texto con mayúsculas y signos sale en minúsculas y limpio.

    Es el caso que da sentido a todo el pipeline. Sin él, comparar
    "El Cielo, es AZUL!" con "el cielo es azul" daría una coincidencia
    baja por diferencias de forma, no de contenido.
    """
    resultado = procesar_texto("El Cielo, es AZUL!")

    assert resultado == ["el", "cielo", "es", "azul"]


def test_procesar_texto_solo_puntuacion_devuelve_lista_vacia():
    """Un texto que era solo signos devuelve una lista vacía.

    No es un caso rebuscado. Una respuesta del modelo que llegó cortada
    o vacía produce exactamente esto. Importa que devuelva una lista y
    no un error, porque quien compare después tiene que poder revisar
    si está vacía antes de dividir por su largo.
    """
    resultado = procesar_texto("¡¡¡...!!!")

    assert resultado == []


# ===== limpiar_texto ==================================================

def test_limpiar_texto_no_deja_espacios_de_sobra():
    """El texto limpio no queda con espacios dobles ni en los bordes.

    Esta prueba fija el orden de los tres pasos. Quitar la puntuación
    crea espacios nuevos, porque al borrar la coma de "perro , y"
    quedan pegados el de antes y el de después. Si alguien invirtiera
    el orden y limpiara los espacios primero, esos nuevos quedarían sin
    limpiar y esta prueba lo avisaría.
    """
    sucio = "  El perro , y  el gato !  "

    assert limpiar_texto(sucio) == "el perro y el gato"


def test_limpiar_texto_rechaza_lo_que_no_es_texto():
    """Cualquier cosa que no sea texto sale como TypeError.

    El match comprueba que el mensaje nombre el tipo que llegó. Sin la
    comprobación, el error aparecería más abajo como un AttributeError
    de texto.lower(), que no dice nada sobre la causa real.
    """
    for valor in (None, 42, ["texto"], {"clave": "valor"}):
        with pytest.raises(TypeError, match=type(valor).__name__):
            limpiar_texto(valor)


# ===== vectorizar =====================================================

def test_vectorizar_cuenta_las_repeticiones():
    """Una palabra que aparece dos veces se cuenta como dos.

    Es justo lo que un conjunto no puede hacer. Si alguien cambiara el
    conteo por Counter(set(tokens)), el "el" bajaría de dos a uno y
    esta prueba lo avisaría.
    """
    tokens = procesar_texto("El gato y el perro")

    assert vectorizar(tokens) == Counter(
        {"el": 2, "gato": 1, "y": 1, "perro": 1})