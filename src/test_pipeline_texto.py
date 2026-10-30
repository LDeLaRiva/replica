"""Pruebas unitarias del pipeline de texto y de sus métricas.

Estas pruebas no necesitan ningún reemplazo. Las funciones de
src.pipeline_texto reciben texto o listas y devuelven texto, listas o
números, sin tocar la red ni depender de nada externo, así que se
llaman directo con un valor escrito a mano.

Es la diferencia con test_cliente.py, donde sí había que reemplazar
requests.post porque enviar_peticion sale a internet.

Los números esperados de las métricas no están inventados. Son los que
las lecciones del Bloque 16 dejan calculados en su texto.

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
    calcular_metricas,
    calcular_precision_cobertura_f1,
    contar_coincidencias,
    limpiar_texto,
    procesar_texto,
    resumir_metricas,
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


# ===== contar_coincidencias ===========================================

def test_contar_coincidencias_no_pierde_repeticiones():
    """Toma el mínimo de cada palabra, no solo si aparece o no.

    Es el ejemplo que la lección calcula a mano. La referencia trae dos
    veces "el" y la respuesta tres, así que la intersección se queda
    con dos. Sumando "gato", "duerme" y "en" dan cinco coincidencias.
    "sofá" no está en la respuesta y no suma.

    Un conjunto habría contado cuatro, una sola vez cada palabra.
    """
    referencia = procesar_texto("El gato duerme en el sofá.")
    respuesta = procesar_texto("El gato duerme en el sillón todo el día.")

    assert contar_coincidencias(referencia, respuesta) == 5


# ===== calcular_precision_cobertura_f1 ================================

def test_precision_cobertura_f1_con_el_ejemplo_de_la_leccion():
    """Los tres números del ejemplo calculado a mano en la lección.

    Con cinco coincidencias sobre nueve palabras de la respuesta, la
    precisión queda en 5/9. Sobre las seis de la referencia, la
    cobertura queda en 5/6. Es el patrón de una respuesta más larga
    que la referencia, que dice todo lo necesario pero con palabras
    de más.
    """
    referencia = procesar_texto("El gato duerme en el sofá.")
    respuesta = procesar_texto("El gato duerme en el sillón todo el día.")

    resultado = calcular_precision_cobertura_f1(referencia, respuesta)

    assert resultado["precision"] == pytest.approx(5 / 9)
    assert resultado["cobertura"] == pytest.approx(5 / 6)
    assert resultado["f1"] == pytest.approx(2 / 3)


def test_precision_cobertura_f1_con_listas_vacias():
    """Una lista vacía devuelve ceros, no una división por cero.

    Pasa de verdad cuando el modelo contesta vacío o cortado, porque
    procesar_texto devuelve una lista vacía y el largo es cero. Sin
    esta guarda la función reventaría con ZeroDivisionError.
    """
    llena = procesar_texto("El cielo es azul.")
    cero = {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

    assert calcular_precision_cobertura_f1([], llena) == cero
    assert calcular_precision_cobertura_f1(llena, []) == cero
    assert calcular_precision_cobertura_f1([], []) == cero


# ===== calcular_metricas ==============================================

def test_calcular_metricas_procesa_los_dos_lados():
    """Recibe dos textos crudos y devuelve las métricas ya calculadas.

    Se comprueba con el caso de la negación de la lección, que es el
    más engañoso de los tres. La respuesta dice lo contrario de la
    referencia y aun así saca 0.909, porque la única palabra que falta
    es el "no".

    Que los números salgan iguales confirma que la función procesó los
    dos lados. Si procesara solo uno, no cuadrarían.
    """
    resultado = calcular_metricas(
        "Python no es un lenguaje compilado.",
        "Python es un lenguaje compilado.")

    assert resultado["precision"] == pytest.approx(1.0)
    assert resultado["cobertura"] == pytest.approx(5 / 6)
    assert resultado["f1"] == pytest.approx(10 / 11)


# ===== resumir_metricas ===============================================

def test_resumir_metricas_promedia_y_soporta_la_lista_vacia():
    """Promedia los tres números, y con cero casos devuelve ceros.

    El promedio esconde el detalle. Dos respuestas buenas y una mala
    dan lo mismo que tres regulares, y por eso la lección pide además
    ordenar por F1 y leer las peores.
    """
    resultados = [
        {"precision": 1.0, "cobertura": 0.5, "f1": 0.0},
        {"precision": 0.0, "cobertura": 0.5, "f1": 1.0},
    ]

    resumen = resumir_metricas(resultados)

    assert resumen["precision_promedio"] == pytest.approx(0.5)
    assert resumen["cobertura_promedio"] == pytest.approx(0.5)
    assert resumen["f1_promedio"] == pytest.approx(0.5)

    vacio = resumir_metricas([])

    assert vacio["precision_promedio"] == 0
    assert vacio["cobertura_promedio"] == 0
    assert vacio["f1_promedio"] == 0
