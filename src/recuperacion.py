"""Recuperación semántica y prompt con fuente citada (Bloque 26).

Toma una pregunta escrita en lenguaje corriente, recupera del índice
los fragmentos que más se le parecen en significado, arma con ellos
el prompt que obliga al modelo a citar, y traduce de vuelta los
números que el modelo citó al artículo del que salió cada uno.

No indexa nada. Se conecta al índice que ya dejó indexar_corpus.py.
Por consulta se pagan dos llamadas, el embedding de la pregunta y la
respuesta del modelo.

Se corre con el botón de ejecutar, o desde la terminal con
`python src/recuperacion.py`, siempre desde la raíz del proyecto.
Corriéndolo desde otra carpeta, Chroma crea un índice nuevo y vacío
sin avisar y la búsqueda devuelve una lista vacía sin lanzar error.
Es el fallo más silencioso de esta etapa y la lección lo advierte.

Las mediciones que respaldan estas decisiones y lo que mostraron las
corridas están en docs/limites_bloque26.md.

Por qué importa los valores de indexar_corpus.py

La guía del Bloque 25 pide que el script de consulta use la misma
carpeta, la misma colección y el mismo modelo de embeddings que el
de indexación. Importándolos no pueden quedar distintos.

La colección es la que más se pasa por alto. El ejemplo de la lección
se reconecta sin nombrarla porque su índice quedó en la colección por
defecto. Este no, y reconectarse sin nombrarla devolvería una
colección vacía y ninguna advertencia.

Por qué la cita lleva el archivo y el artículo

La actividad pide que cada valor del diccionario de citas sea un
nombre de archivo reconocible del proyecto y nunca la palabra
desconocida.

Este corpus está entero en un archivo, así que el nombre por sí solo
sería igual en los cuarenta y cinco fragmentos y no distinguiría
nada. El artículo sí identifica el origen, y además es lo único
verificable fuera de este repositorio. Por eso van los dos.

El nombre del archivo no se escribe a mano, se toma del módulo que
guarda el corpus. Escrito a mano quedaría viejo al renombrar ese
archivo, y las citas nombrarían algo que no existe sin que nada
avise.

Cuando falta el artículo la cita dice desconocida y no se arma el
texto, porque esa palabra es la alarma que la actividad quiere ver y
una cita armada siempre la taparía.

Por qué el modelo nunca ve el id del fragmento

El modelo cita por número de bloque y este programa traduce ese
número al artículo. Los ids del índice, del tipo art_162_0, no viajan
ni en el texto ni en el metadato, así que el modelo no los puede
confundir con un número de artículo.

Por qué la plantilla trae una frase exacta para el vacío

Es la plantilla de la lección con una sola cosa agregada. Cuando el
contexto no alcanza, el modelo responde una frase determinada en vez
de redactar la suya, y así la comprobación que pide la lección se
hace en código y no a ojo.

La frase vive en SIN_CONTEXTO y se inserta una sola vez, para que la
que se le pide al modelo y la que se busca en la respuesta no puedan
quedar distintas.

Por qué las citas se traducen de vuelta, y con dos expresiones

El modelo responde con números y quien lee necesita artículos. De
paso se atrapa un número que nunca estuvo en el contexto, un [9]
cuando se pasaron cuatro bloques, que en una respuesta legal sería
una fuente inventada.

Las citas no siempre vienen de a una. El modelo puede escribir [1, 4]
para respaldar una afirmación con dos fragmentos, y eso no lo
reconoce una expresión que exija corchete, dígitos y corchete. Por
eso se buscan primero los grupos entre corchetes que traigan solo
dígitos y separadores, y después los números de cada grupo. Lo
primero deja afuera a las notas del corpus, que también van entre
corchetes y traen números adentro.

Por qué k vale 4

La actividad ofrece empezar en 3 o en 4 y pide que cualquier ajuste
vaya respaldado por una medición. Con 3, el fragmento que respondía
una de las consultas de prueba quedaba justo debajo del corte. Más no
se sube, porque es hasta donde llega lo medido.

Por qué el modelo entra por parámetro

La misma razón que en cadena_tres_pasos.py. Creado adentro de la
función, no hay forma de correr la lógica con un modelo falso.

Por qué load_dotenv se llama otra vez

Importar indexar_corpus.py ya lo llama. Se deja igual porque depender
de un efecto colateral de un import para algo tan central como la
clave lo vuelve invisible para quien lee este archivo, y llamarlo dos
veces no hace daño.
"""

import os
import re
import sys

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

import soporte_corpus_legal
from indexar_corpus import (
    CARPETA_INDICE,
    COLECCION,
    cargar_vectorstore,
)

load_dotenv()

# El archivo donde vive el corpus completo. Acompaña al número de
# artículo en cada cita. Se toma del módulo y no se escribe a mano,
# para que nunca nombre un archivo que ya no existe.
ARCHIVO_CORPUS = os.path.basename(soporte_corpus_legal.__file__)

# Cuántos fragmentos se recuperan por pregunta.
RECUPERADOS = 4

# La frase que el modelo tiene que responder cuando el contexto no
# alcanza. Se le pide en la plantilla y se busca en la respuesta.
SIN_CONTEXTO = (
    "El contexto disponible no alcanza para responder esta consulta."
)

# La marca que separa la instrucción del contexto dentro del prompt.
# contexto_de la usa para recortar.
MARCA_CONTEXTO = "Contexto:\n"

PROMPT_TEMPLATE = """Responde la pregunta usando SOLO el contexto de abajo. Cita la \
fuente de cada afirmacion con su numero entre corchetes, como [1]. Si el contexto no \
alcanza para responder, dilo explicitamente en vez de inventar, con esta frase exacta \
y sin agregar nada mas.

""" + SIN_CONTEXTO + """

""" + MARCA_CONTEXTO + """{contexto}

Pregunta: {pregunta}

Respuesta:"""

# Los grupos entre corchetes que el modelo escribe al citar, y los
# números de cada grupo. Exigir que el grupo entero sea de dígitos y
# separadores es lo que deja afuera a las notas del corpus.
CITA = re.compile(r"\[([\d\s,;]+)\]")
NUMERO = re.compile(r"\d+")


def formatear_contexto(chunks_recuperados):
    """Arma el contexto numerado y el mapa de número a fuente.

    Devuelve dos cosas. El texto numerado que va dentro del prompt, y
    un diccionario que empareja cada número con el origen de ese
    fragmento, para reconstruir la cita cuando el modelo responda.

    La numeración arranca en 1 y no en 0 porque es la que lee una
    persona en la respuesta del modelo.

    El diccionario no viaja en el prompt. Se queda en el programa, y
    es lo que permite traducir después sin que el modelo intervenga.
    """
    lineas = []
    citas = {}

    for i, doc in enumerate(chunks_recuperados, start=1):
        articulo = doc.metadata.get("articulo")
        citas[i] = (f"{ARCHIVO_CORPUS} · art. {articulo}"
                    if articulo else "desconocida")
        lineas.append(f"[{i}] {doc.page_content}")

    contexto = "\n\n".join(lineas)
    return contexto, citas


def construir_prompt(pregunta, carpeta=CARPETA_INDICE,
                     coleccion=COLECCION, k=RECUPERADOS):
    """Recupera los k fragmentos más cercanos y arma el prompt.

    Se reconecta al índice y nunca vuelve a indexar. Ese es el error
    frecuente que marca la actividad, porque indexar de nuevo
    recalcularía en cada pregunta embeddings ya pagados.

    Reconectarse no cuesta nada. Lo único que se paga es el embedding
    de la pregunta.
    """
    vectorstore = cargar_vectorstore(carpeta, coleccion)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})

    chunks_recuperados = retriever.invoke(pregunta)
    contexto, citas = formatear_contexto(chunks_recuperados)
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)

    return prompt, citas


def responder_con_citas(modelo, pregunta, carpeta=CARPETA_INDICE,
                        coleccion=COLECCION, k=RECUPERADOS):
    """Arma el prompt, se lo pasa al modelo y devuelve las tres cosas.

    El prompt, para poder mostrarlo como evidencia. La respuesta en
    texto. Y el diccionario de citas, que es con lo que después se
    traduce cada número a su artículo.

    Corta antes de llamar al modelo si la recuperación vino vacía. Un
    índice vacío no lanza error, devuelve una lista vacía, y seguir
    adelante pagaría una respuesta armada sobre nada.

    Args:
        modelo: el modelo de lenguaje ya creado. Entra por parámetro
            para que se pueda correr con uno falso.
    """
    prompt, citas = construir_prompt(pregunta, carpeta, coleccion, k)

    if not citas:
        raise ValueError(
            "La recuperación no trajo ningún fragmento y no se llamó "
            "al modelo. El índice está vacío o la colección no es la "
            "que se esperaba. Corre "
            "python src/indexar_corpus.py --verificar"
        )

    respuesta = (modelo | StrOutputParser()).invoke(prompt)
    return prompt, respuesta, citas


def fuentes_citadas(respuesta, citas):
    """Traduce a su artículo cada número que el modelo citó.

    Devuelve los pares de número y fuente en el orden en que
    aparecieron, sin repetir, porque el mismo bloque se suele citar
    más de una vez en una respuesta.

    Lee tanto las citas de un número, [1], como las de varios en un
    mismo corchete, [1, 4].

    Un número que no esté en el diccionario se nombra como cita
    inválida, porque en una respuesta legal sería una fuente
    inventada.
    """
    numeros = []
    for grupo in CITA.findall(respuesta):
        numeros.extend(int(n) for n in NUMERO.findall(grupo))
    numeros = tuple(dict.fromkeys(numeros))

    return tuple(
        (numero,
         citas.get(numero,
                   "cita inválida, ese número no estaba en el contexto"))
        for numero in numeros
    )


def contexto_de(prompt):
    """Recorta el contexto de un prompt ya armado.

    Sirve para comparar dos consultas sin volver a recuperar nada. La
    actividad pide confirmar que el contexto cambia entre una
    pregunta y otra, y comparar los prompts enteros no serviría,
    porque siempre difieren en la línea de la pregunta.

    Depende de cómo está escrita PROMPT_TEMPLATE, así que avisa en vez
    de reventar si esa plantilla cambiara.
    """
    if MARCA_CONTEXTO not in prompt:
        raise ValueError(
            f"Este prompt no trae la marca {MARCA_CONTEXTO!r}. Si "
            "cambió PROMPT_TEMPLATE, hay que cambiar también esta "
            "función."
        )
    return prompt.split(MARCA_CONTEXTO, 1)[1].split("\n\nPregunta:", 1)[0]


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            'Falta GEMINI_API_KEY. Defínela en tu archivo ".env" y '
            "vuelve a ejecutar."
        )

    if not os.getenv("AI_MODEL"):
        raise SystemExit(
            'Falta AI_MODEL. Es el nombre del modelo de chat y va en '
            'el mismo archivo ".env", igual que en los bloques '
            "anteriores."
        )

    # Las etiquetas no son decorativas. Las comprobaciones de abajo
    # buscan por ellas cuál consulta es cuál, en vez de dar por hecho
    # en qué posición quedó cada una.
    #
    # Las dos del corpus tienen que traer contextos distintos entre sí.
    #
    # Las de afuera son dos y no una, a dos distancias del corpus. El
    # criterio escrito de la actividad pide una pregunta que el corpus
    # no pueda responder, y el ejemplo que dio el profesor en clase
    # fue algo de otro tema por completo. Las dos juntas cubren lo
    # escrito y lo dicho, y además muestran si la abstención aguanta
    # cuando el contexto se parece y cuando no se parece en nada.
    #
    # El feriado anual son los artículos 67 al 76 y no están
    # indexados, pero el 66 sí, y menciona el feriado anual al pasar,
    # así que la búsqueda va a traer algo del mismo tema. La receta no
    # tiene nada cerca en el corpus.
    DENTRO = "del corpus"
    CONSULTAS = (
        (DENTRO,
         "me despidieron por necesidades de la empresa, "
         "¿cuántos días de aviso me corresponden?"),
        (DENTRO,
         "¿cómo se calcula la indemnización por años de servicio?"),
        ("fuera del corpus, del mismo tema",
         "¿cuántos días de vacaciones me corresponden al año?"),
        ("fuera del corpus, de otro tema",
         "¿cuál es la receta del pastel de choclo?"),
    )

    # El modelo se crea aquí y no dentro de responder_con_citas, por
    # la misma razón que en cadena_tres_pasos.py.
    #
    # La credencial no se pasa por parámetro. La librería la busca
    # sola en GOOGLE_API_KEY y, como respaldo, en GEMINI_API_KEY.
    modelo = ChatGoogleGenerativeAI(
        model=os.getenv("AI_MODEL"),
    )

    print("El índice")
    print(f"  carpeta     {os.path.abspath(CARPETA_INDICE)}")
    print(f"  colección   {COLECCION}")
    print(f"  k           {RECUPERADOS}")
    print()

    # Cada corrida queda guardada bajo su etiqueta, para que las
    # comprobaciones la busquen por ahí y no por su posición.
    corridas = {}

    for etiqueta, pregunta in CONSULTAS:
        prompt, respuesta, citas = responder_con_citas(modelo, pregunta)
        corridas.setdefault(etiqueta, []).append((prompt, respuesta))

        print("=" * 68)
        print(f"Consulta {etiqueta}")
        print("=" * 68)
        print(prompt)
        print()

        print("El diccionario de citas")
        for numero, fuente in citas.items():
            print(f"  [{numero}]  {fuente}")
        print()

        print("La respuesta del modelo")
        print(respuesta)
        print()

        print("Las fuentes que citó")
        citadas = fuentes_citadas(respuesta, citas)
        if not citadas:
            print("  ninguna, la respuesta no trae números entre "
                  "corchetes")
        for numero, fuente in citadas:
            print(f"  [{numero}]  {fuente}")
        print()

    print("=" * 68)
    print("Las comprobaciones de la actividad")
    print("=" * 68)

    # Del corpus son las etiquetadas así. De afuera es todo lo demás,
    # cualquiera sea la etiqueta, para que agregar otro caso fuera del
    # corpus no obligue a tocar esta comprobación.
    del_corpus = corridas.get(DENTRO, [])
    de_afuera = [
        (etiqueta, respuesta)
        for etiqueta, pares in corridas.items()
        if etiqueta != DENTRO
        for _, respuesta in pares
    ]

    if len(del_corpus) < 2 or not de_afuera:
        raise SystemExit(
            "CONSULTAS tiene que traer al menos dos preguntas del "
            "corpus y una de afuera, que son los escenarios que pide "
            "la actividad."
        )

    # La primera. Si dos contextos salieran iguales, la búsqueda no
    # estaría mirando el significado de la pregunta.
    (primer_prompt, _), (segundo_prompt, _) = del_corpus[:2]

    if contexto_de(primer_prompt) == contexto_de(segundo_prompt):
        print("  el contexto NO cambió entre las dos preguntas del")
        print("  corpus, así que la recuperación no está siendo")
        print("  semántica de verdad")
        sys.exit(1)

    print("  el contexto cambió entre las dos preguntas del corpus")

    # La segunda, una por cada consulta de afuera. Se informa y no se
    # corta, porque una respuesta que admita el vacío con otras
    # palabras también cumple el criterio de la actividad. Lo que
    # esta comprobación resuelve es el caso claro.
    for etiqueta, respuesta_fuera in de_afuera:
        if SIN_CONTEXTO in respuesta_fuera:
            print(f"  {etiqueta}, se abstuvo sin inventar")
        else:
            print(f"  {etiqueta}, NO trajo la frase de abstención.")
            print("    Lee la respuesta de más arriba, porque admitir")
            print("    el vacío con otras palabras también vale")

    # La tercera queda para hacerla a mano. Tomar el [1] de una de
    # las respuestas de arriba, ver qué artículo dice su cita, y
    # contrastar ese texto contra la fuente en BCN.
    print()
    print("La tercera comprobación va a mano. Toma el [1] de la")
    print("primera respuesta, mira qué artículo indica su cita, y")
    print("contrasta ese texto contra la fuente.")
