"""Cadena de tres pasos con LangChain, sobre una consulta laboral.

Un trabajador escribe un mensaje largo y desordenado, con la pregunta
mezclada entre el relato. La cadena lo convierte en una respuesta clara
en tres pasos, donde la salida de cada uno es la entrada del siguiente.

    1. Extraer      del mensaje, deja la consulta en una sola pregunta.
    2. Responder    contesta esa pregunta según la normativa chilena.
    3. Simplificar  reescribe la respuesta sin jerga legal.

Una sola llamada no podría hacerlo igual de bien, porque primero hay
que entender qué está preguntando el trabajador antes de buscar la
norma, y recién después se puede traducir la norma a algo legible.

El modelo entra como parámetro de construir_cadena y no se crea
adentro, para poder reemplazarlo por un falso en las pruebas.

Se corre con el botón de ejecutar, o desde la terminal con
`python src/cadena_tres_pasos.py`
"""

import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


def construir_cadena(modelo):
    """Arma los tres pasos y los devuelve encadenados, sin ejecutar.

    Cada plantilla espera una variable distinta, y entre un paso y el
    siguiente hay una función intermedia que envuelve el texto de
    salida en el diccionario que la plantilla siguiente necesita. El
    nombre de esa clave tiene que coincidir exactamente con la
    variable de la plantilla, o se cae con KeyError.

    Args:
        modelo: el modelo de lenguaje ya creado. Entra por parámetro
            para que las pruebas puedan pasar uno falso.

    Returns:
        La cadena armada, lista para recibir .invoke({"mensaje": ...}).
    """
    # Paso 1. Saca la consulta concreta del relato del trabajador.
    plantilla_extraccion = PromptTemplate.from_template(
        "Lee el siguiente mensaje de un trabajador y devuelve solo "
        "la consulta laboral concreta que está haciendo, redactada "
        "como una sola pregunta, sin responderla:\n\n{mensaje}"
    )
    paso_extraccion = plantilla_extraccion | modelo | StrOutputParser()

    # Paso 2. Responde esa pregunta según la normativa chilena.
    plantilla_respuesta = PromptTemplate.from_template(
        "Responde la siguiente consulta basándote exclusivamente en "
        "el Código del Trabajo de Chile vigente, en dos o tres "
        "oraciones, indicando siempre el número del artículo que "
        "respalda la respuesta:\n\n{consulta}"
    )
    paso_respuesta = plantilla_respuesta | modelo | StrOutputParser()

    # Paso 3. Traduce la respuesta a lenguaje de todos los días.
    plantilla_simplificacion = PromptTemplate.from_template(
        "Reescribe la siguiente respuesta para un trabajador que "
        "nunca ha leído el Código del Trabajo. Sin jerga legal, "
        "tratándolo de usted, en un párrafo corto. Conserva los "
        "datos concretos y el artículo que los respalda:"
        "\n\n{respuesta}"
    )
    paso_simplificacion = (
        plantilla_simplificacion | modelo | StrOutputParser()
    )

    return (
        paso_extraccion
        | (lambda consulta: {"consulta": consulta})
        | paso_respuesta
        | (lambda respuesta: {"respuesta": respuesta})
        | paso_simplificacion
    )


if __name__ == "__main__":
    # El módulo no usa colores, solo esta corrida. contraste.py está
    # en esta misma carpeta, así que se importa directo.
    from contraste import *                                # noqa: F403

    load_dotenv()

    # Un mensaje real, del estilo que llega de verdad. La pregunta
    # viene enterrada en el relato y además trae un dato equivocado,
    # lo que dijo el jefe.
    MENSAJE = (
        "Hola, buenas. Mire, le cuento que falleció mi papá el jueves "
        "pasado y avisé en el trabajo al tiro, pero no me queda claro "
        "cuántos días me corresponden. Llevo tres años en la empresa "
        "y mi jefe me dijo que eran dos días nomás, pero una "
        "compañera me dijo que eran más. ¿Me pueden aclarar cuánto es "
        "lo que me toca? Gracias."
    )

    # El modelo se crea aquí y no dentro de construir_cadena, para que
    # las pruebas puedan armar la cadena con un modelo falso.
    #
    # La credencial no se pasa por parámetro. ChatGoogleGenerativeAI
    # la busca sola en GOOGLE_API_KEY y, como respaldo, en
    # GEMINI_API_KEY, que load_dotenv acaba de cargar desde el .env.
    #
    # No se pasa temperature. Google la marcó como obsoleta junto
    # con top_p y top_k en los modelos flash de esta generación, que
    # las ignoran, y anunció que las próximas van a responder con
    # error 400 si se envían. Esas perillas no tienen reemplazo
    # exacto. Lo que Google recomienda en su lugar es escribir reglas
    # explícitas en el prompt, que es lo que hacen las tres
    # plantillas al fijar el largo, el tono y el formato.
    modelo = ChatGoogleGenerativeAI(
        model=os.getenv("AI_MODEL"),
    )

    cadena = construir_cadena(modelo)

    titulobn("\nCadena de tres pasos sobre una consulta laboral")
    salbn(f"\n  Mensaje del trabajador\n    {MENSAJE}")

    resultado = cadena.invoke({"mensaje": MENSAJE})

    exitobn(f"\n  Respuesta final\n    {resultado}")
    notabn("\nFin de la corrida.")
