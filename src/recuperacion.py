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
corridas están en docs/limites_bloque26.md. El cambio de la plantilla
que se hizo después está medido en docs/limites_bloque28.md.

Por qué importa los valores de indexar_corpus.py

La guía del Bloque 25 pide que el script de consulta use la misma
carpeta, la misma colección y el mismo modelo de embeddings que el
de indexación. Importándolos no pueden quedar distintos.

La colección es la que más se pasa por alto. El ejemplo de la lección
se reconecta sin nombrarla porque su índice quedó en la colección por
defecto. Este no, y reconectarse sin nombrarla devolvería una
colección vacía y ninguna advertencia.

Por qué la cita lleva la norma, el artículo y el archivo

La actividad pide que cada valor del diccionario de citas sea un
nombre reconocible del proyecto y nunca la palabra desconocida.

La cita nombra tres cosas y cada una sirve a un lector distinto. La
norma, el Código del Trabajo, es la fuente y es lo que permite ir a
contrastar el texto fuera de este repositorio. El artículo es lo que
identifica el fragmento, porque este corpus está entero en un
archivo y el nombre del archivo por sí solo sería igual en todos. Y
el archivo dice dónde vive ese texto dentro del repositorio.

La primera versión de esta cita llevaba solo el archivo y el
artículo, y se leía como un script y no como una fuente legal. El
criterio es el que dio el profesor en clase, que una persona que
quiera comprobar que la información no está inventada pueda ir a
verificarla en la documentación.

El nombre del archivo no se escribe a mano, se toma del módulo que
guarda el corpus. Escrito a mano quedaría viejo al renombrar ese
archivo, y las citas nombrarían algo que no existe sin que nada
avise.

La norma sí va escrita, porque los once artículos salen del mismo
código y no hay de dónde deducirla. Lo que varía fragmento a
fragmento es el artículo, que sale del metadato.

Cuando falta el artículo la cita dice desconocida y no se arma el
texto, porque esa palabra es la alarma que la actividad quiere ver y
una cita armada siempre la taparía.

Por qué el modelo nunca ve el id del fragmento

El modelo cita por número de bloque y este programa traduce ese
número al artículo. Los ids del índice, del tipo art_162_0, no viajan
ni en el texto ni en el metadato, así que el modelo no los puede
confundir con un número de artículo.

Por qué la plantilla ofrece tres salidas y no dos

Es la plantilla de la lección con dos cosas agregadas. La frase
exacta para el vacío, y la salida del medio.

Cuando el contexto no alcanza, el modelo responde una frase
determinada en vez de redactar la suya, y así la comprobación que
pide la lección se hace en código y no a ojo. La frase vive en
SIN_CONTEXTO y se inserta una sola vez, para que la que se le pide al
modelo y la que se busca en la respuesta no puedan quedar distintas.

La salida del medio se agregó en el Bloque 28, después de medirla.
Con solo dos salidas, responder todo o abstenerse de todo, una
pregunta que pide dos cosas y un contexto que cubre una termina en
abstención completa. Se comprobó con el contexto idéntico, los mismos
cuatro fragmentos y los mismos 2082 caracteres, cuatro corridas de
cuatro. Las mismas preguntas partidas en mitades respondían.

Ahora son tres. Si el contexto cubre todo, el modelo responde. Si
cubre una parte, responde esa parte y dice cuál no puede responder
con ese contexto. Si no cubre nada, la frase exacta.

Para una consulta laboral la salida del medio importa más que en otro
dominio. Callarse entero deja a la persona sin nada que sí estaba en
la ley, y media respuesta sin avisar la deja creyendo que tiene todo.

Por qué las tres salidas van enumeradas y la frase va sin comillas

La primera versión de la plantilla de tres salidas escribía las tres
instrucciones como párrafos corridos y ponía la frase entre comillas.
Con esa forma, la consulta del acoso devolvía la tercera instrucción
en vez de la frase, convertida en afirmación.

    El contexto no responde ninguna parte de la pregunta, responde
    exactamente esta frase y nada mas: "El contexto disponible no
    alcanza para responder esta consulta."

Ciento sesenta y cuatro caracteres donde la frase sola mide sesenta y
tres. La comprobación en código no lo detectaba, porque busca la
frase dentro de la respuesta y la frase está dentro.

Se midió de dónde venía. Quitando la salida del medio la filtración
desaparece, con el mismo contexto, pero eso devolvería el problema
que la salida del medio arregló. Así que el párrafo se queda y lo que
cambió es la forma.

Se compararon cinco redacciones sobre el mismo contexto, la de
entonces como línea base y cuatro variantes. Reescribir la tercera
instrucción no sirvió, el modelo copió la redacción nueva igual, y
eso pasó con las dos redacciones que se probaron. Lo que sirvió fue
cambiar la estructura. Dejaron de filtrar dos variantes, enumerar las
tres salidas y mover las instrucciones después del contexto. Se tomó
la primera porque cambia menos el orden del prompt.

La enumerada se validó con el criterio del Bloque 26. Cero
filtraciones en nueve corridas de la consulta del acoso, contra una
base que filtra cerca de la mitad de las veces, y los tres controles
aguantan, la pregunta compuesta responde, las de fuera del corpus se
abstienen con la frase limpia y la consulta del Bloque 26 responde
citando.

Las dos mediciones están en la sección 8 del
docs/limites_bloque28.md, con sus tablas.

La frase va sin comillas porque el modelo las copiaba, y una
respuesta entrecomillada deja de ser igual a SIN_CONTEXTO.

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

Por qué k vale 3

La actividad del Bloque 26 ofrece empezar en 3 o en 4 y pide que
cualquier ajuste vaya respaldado por una medición.

Con la partición de entonces, de setecientos caracteres y sin separar
los incisos, ganaba el 4. Con 3, el fragmento que respondía una de
las consultas de prueba quedaba justo debajo del corte, y la
evaluación del Bloque 27 lo confirmó.

Con la partición por inciso del Bloque 28 cada fragmento trae un
inciso completo, de modo que hacen falta menos fragmentos para cubrir
lo mismo. Medido sobre las dieciséis preguntas del conjunto de
evaluación, el 3 supera a la configuración anterior en las tres
medidas a la vez, precisión, recall y F1.

Subir al 4 agregaría media pregunta de catorce, y esa media pregunta
es la que ya fallaba de la manera contenida, abstieniéndose en vez de
contestar de otra cosa. Es la misma cuenta que dejó el k en 4 en el
Bloque 27 y que ahora lo deja en 3.

Lo que cuesta, con los tokens medidos al tope 1300. Cada fragmento
extra agrega unos 305 tokens de entrada, así que sobre la pregunta
del medio la entrada sube un treinta y ocho por ciento y el costo
total un diecisiete, dejando la salida igual. La versión anterior de
esta cabecera decía un catorce por ciento, que venía de la proyección
hecha al tope 1500 y no de los tokens medidos.

Bajar al 1 es la pregunta que queda, porque el F1 tiene su máximo
ahí. Con el tope de 1300 el k=1 mejoró, de 0.643 a 0.786 de recall, y
la distancia contra el k=3 se angostó a una pregunta de catorce. El
recall promedio ya no alcanza para defender la decisión.

Lo que la defiende es el mismo límite legal que fijó el tope. En la
consulta del cálculo los tres fragmentos llegan en este orden,
artículo 163, artículo 40 bis D y artículo 172. El tope de noventa
unidades de fomento vive en el artículo 172, que llega tercero, así
que con k=1 o con k=2 no llega. El 3 es el mínimo que lo trae, y se
ve en la corrida de src/probar_generacion.py, donde la respuesta cita
ese límite con la fuente [3].

El tope y el k quedan entonces fijados por la misma condición. El
tope de 1300 para que el artículo 172 quepa entero en un fragmento, y
el k de 3 para que ese fragmento llegue.

Las tablas están en docs/limites_bloque28.md.

Por qué el modelo entra por parámetro

La misma razón que en cadena_tres_pasos.py. Creado adentro de la
función, no hay forma de correr la lógica con un modelo falso.

Por qué load_dotenv se llama otra vez

Importar indexar_corpus.py ya lo llama. Se deja igual porque depender
de un efecto colateral de un import para algo tan central como la
clave lo vuelve invisible para quien lee este archivo, y llamarlo dos
veces no hace daño.

Por qué la cita acepta un marcador subnumerado

El modelo a veces escribe [3.1] en vez de [3], aunque la instrucción
pide el número del bloque. En la corrida del 26 de noviembre de 2026
escribió [1], [2], [3.1], [3.2] y [3.3] en la misma respuesta.

Con el grupo de caracteres sin el punto, esos tres marcadores no
coincidían con nada. Tres afirmaciones de la respuesta quedaban sin
fuente que las respaldara, la lista mostraba dos fuentes y el conteo
de citas inválidas salía en cero, porque el programa no las veía. El
criterio no compensable del Gate 2 pide que cada respuesta cite la
fuente que la respalda, así que no era una falla de presentación.

El punto entró al grupo y cada marcador se resuelve al número entero
de antes del punto, que es el bloque que el modelo estaba citando. Las
letras siguen afuera, de modo que las notas del corpus siguen sin
entrar. Un decimal que no sea una cita, como [90.5], se resuelve a 90
y se nombra cita inválida si ese bloque no está en el contexto.

No se tocó la plantilla. La huella del prompt sigue en faa337bde6a2,
comprobada después del cambio, que es la que asertan
src/registro_prompts.py y src/grafo_supervision.py.
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

# La norma de la que sale todo el corpus. Va escrita porque los once
# artículos son del mismo código y no hay de dónde deducirla, y es
# lo que permite contrastar una respuesta fuera de este repositorio.
FUENTE_LEGAL = "Código del Trabajo de Chile"

# Cuántos fragmentos se recuperan por pregunta. Es el k del proyecto
# y lo importan los demás módulos, para que no quede escrito dos
# veces y puedan quedar distintos.
RECUPERADOS = 3

# La frase que el modelo tiene que responder cuando el contexto no
# cubre ninguna parte de la pregunta. Se le pide en la plantilla y se
# busca en la respuesta.
SIN_CONTEXTO = (
    "El contexto disponible no alcanza para responder esta consulta."
)

# La marca que separa la instrucción del contexto dentro del prompt.
# contexto_de la usa para recortar.
MARCA_CONTEXTO = "Contexto:\n"

PROMPT_TEMPLATE = """\
Tienes tres formas de responder y eliges una sola.

1. Si el contexto responde toda la pregunta, respondela usando SOLO \
el contexto. Cita la fuente de cada afirmacion con su numero entre \
corchetes, como [1].

2. Si el contexto responde una parte, responde esa parte citando \
igual, y despues di con claridad que parte no se puede responder con \
este contexto.

3. Si el contexto no responde ninguna parte, tu respuesta completa \
es la linea siguiente, copiada tal cual y sin explicar nada antes ni \
despues.

""" + SIN_CONTEXTO + """

""" + MARCA_CONTEXTO + """{contexto}

Pregunta: {pregunta}

Respuesta:"""

# Los grupos entre corchetes que el modelo escribe al citar, y los
# marcadores de cada grupo. Exigir que el grupo entero sea de dígitos
# y separadores es lo que deja afuera a las notas del corpus. El punto
# entra porque el modelo a veces subnumera, [3.1] en vez de [3], y sin
# el punto ese marcador queda invisible. Las letras siguen afuera.
CITA = re.compile(r"\[([\d\s,.;]+)\]")
NUMERO = re.compile(r"\d+")
MARCADOR = re.compile(r"\d+(?:\.\d+)*")


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
        citas[i] = (f"{FUENTE_LEGAL}, art. {articulo} "
                    f"({ARCHIVO_CORPUS})"
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

    Lee también las subnumeradas, [3.1], que el modelo escribe a
    veces aunque la instrucción pida [3]. Se resuelven al número
    entero de antes del punto, que es el bloque que el modelo estaba
    citando. Sin esto el marcador no coincide con ningún corchete
    reconocido y la afirmación queda sin fuente que la respalde, que
    es el criterio no compensable del Gate 2.

    Un número que no esté en el diccionario se nombra como cita
    inválida, porque en una respuesta legal sería una fuente
    inventada.
    """
    numeros = []
    for grupo in CITA.findall(respuesta):
        for marcador in MARCADOR.findall(grupo):
            numeros.append(int(marcador.split(".")[0]))
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

    # La segunda, una por cada consulta de afuera. Estas dos no tienen
    # ninguna parte cubierta por el corpus, de modo que les toca la
    # frase exacta y no la salida del medio. Se informa y no se corta,
    # porque una respuesta que admita el vacío con otras palabras
    # también cumple el criterio de la actividad. Lo que esta
    # comprobación resuelve es el caso claro.
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
