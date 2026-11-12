"""Indexación del corpus legal en un vector store (Bloques 24 y 25).

Toma los once artículos del corpus, los parte con el tope que se
eligió midiendo, calcula un embedding por fragmento y guarda todo en
disco. Después de esto, la consulta del Bloque 26 se conecta al
índice sin volver a calcular nada.

Es la única parte de la cadena que hace llamadas reales a la API. Una
por fragmento.

Las tres formas de correrlo, desde la raíz del proyecto.

    python src/indexar_corpus.py              indexa si no hay nada
    python src/indexar_corpus.py --reindexar  vuelve a indexar
    python src/indexar_corpus.py --verificar  cuenta y compara

Por qué el corpus se importa y no se escribe de nuevo

El texto vive en soporte_corpus_legal.py, verificado artículo por
artículo contra la fuente. Copiarlo aquí crearía un segundo original
que se puede desincronizar del primero. La función que lo prepara se
queda solo con el texto y descarta las claves de búsqueda, que son de
la búsqueda por palabra y no son ley.

Por qué cada fragmento lleva el número de su artículo

El primer fragmento de cada artículo empieza con "Art. 162." y se
identifica solo. Los siguientes no. El fragmento 2 del artículo 40
bis D empieza con "del contrato. Con todo, si la indemnización..." y
no dice de qué artículo es.

La búsqueda por significado del Bloque 26 va a recuperar fragmentos
cualesquiera, no solo los primeros. Si recupera uno de esos, el
modelo no tiene con qué citar el artículo. Y la regla central de este
proyecto es que toda respuesta se pueda contrastar contra el texto
que la respalda.

Por eso el número del artículo viaja como metadato en cada fragmento,
puesto al partir y copiado por el splitter a cada pedazo que sale de
un mismo documento.

Por qué los ids son explícitos

Son del tipo art_162_3, el artículo y la posición del fragmento
dentro de él. La lección del Bloque 25 lo recomienda para quien vaya
a actualizar el corpus de a poco, y este corpus cambia, pasó de nueve
artículos a once.

Con ids explícitos, volver a indexar sobrescribe en vez de duplicar.
Eso se comprobó antes de escribir esto, agregando el mismo documento
dos veces con el mismo id, y el conteo quedó en uno las dos veces.

De ahí salen tres cosas. Que --reindexar sea seguro. Que se pueda
reemplazar o borrar un artículo suelto sin tocar el resto. Y que no
haga falta borrar la carpeta a mano para rehacer el índice.

Por qué el tope es 700 y el solape 126

Salieron de la medición de medir_chunks.py, con el solape en el
dieciocho por ciento que usa el ejemplo de la lección. La tabla y el
razonamiento están en docs/limites_bloque24.md.

Por qué la carpeta y la colección son constantes

La guía de troubleshooting del Bloque 25 pide usar exactamente los
mismos dos valores en el script de indexación y en el de consulta, y
avisa que dejar el nombre de colección en su valor por defecto es la
causa más común de colecciones fantasma, cuando dos corpus distintos
terminan compartiendo una colección sin que nadie se dé cuenta.

Dejándolos como constantes, el script del Bloque 26 los importa en
vez de volver a escribirlos y no pueden quedar distintos.

La carpeta es contenido generado y está en el .gitignore, porque se
reconstruye corriendo esto.

Por qué el reintento es solo para el 429

Es el patrón de la guía de troubleshooting. Reintenta solo cuando el
error es de límite de peticiones, espera cada vez el doble, y si se
agotan los intentos vuelve a lanzar el error para que no quede
oculto.

Un 429 significa que la llamada no se hizo, así que repetirla no
duplica nada. Es distinto del reintento que se le quitó al agente,
que podía repetir un envío irreversible.

Lo que la guía no dice es el costo. from_documents no guarda un
progreso parcial, de modo que un reintento vuelve a pagar los
fragmentos que ya habían entrado. Con este corpus son 45 y el 429 es
improbable, así que se acepta. Con un corpus grande convendría
indexar por lotes, que los ids explícitos ya permiten.
"""

import os
import re
import sys
import time

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from soporte_corpus_legal import ARTICULOS

# La clave vive en el .env y la lee la librería por su cuenta, con el
# nombre GEMINI_API_KEY. No se nombra en este archivo ni se imprime.
load_dotenv()

CARPETA_INDICE = "vectorstore/"
COLECCION = "corpus_legal_chile"
TOPE = 700
SOLAPE = 126
MODELO_EMBEDDINGS = "models/gemini-embedding-001"

# Reconoce "Art. 162.", "Art. 40 bis D." y "[1] Artículo 66.-", que
# son las tres formas con que el corpus abre un artículo.
ETIQUETA = re.compile(
    r"(?:\[1\]\s*)?Art(?:ículo)?\.?\s+([\w\s]+?)\s*[.\-]"
)


def preparar_documentos():
    """Devuelve los textos del corpus y un metadato por cada uno.

    El metadato lleva el número del artículo. El splitter lo copia a
    cada fragmento que salga de ese texto, así que un fragmento del
    medio de un artículo sigue sabiendo de dónde viene.
    """
    textos, metadatos = [], []

    for claves, texto in ARTICULOS:
        calce = ETIQUETA.match(texto)
        if calce is None:
            raise ValueError(
                "No pude leer el número de artículo del texto que "
                f"empieza con {texto[:40]!r}. El corpus abre sus "
                "artículos con Art. N., Art. N bis o Artículo N.-, y "
                "este no calza con ninguna."
            )
        textos.append(texto)
        metadatos.append({"articulo": calce.group(1).strip()})

    return textos, metadatos


def fragmentar(textos, metadatos, tope=TOPE, solape=SOLAPE):
    """Parte los textos y devuelve los fragmentos con su metadato.

    Cada texto entra como un documento aparte, de modo que un
    fragmento nunca mezcla dos artículos. Eso no se configura, sale
    de pasarle una lista y no un texto solo.

    Partir es local y no cuesta nada, así que se puede llamar para
    contar fragmentos sin gastar una sola llamada a la API.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=tope,
        chunk_overlap=solape,
    )
    return splitter.create_documents(textos, metadatas=metadatos)


def ids_de(fragmentos):
    """Arma un id explícito y predecible para cada fragmento.

    Quedan del tipo art_40_bis_d_1, el artículo y la posición del
    fragmento dentro de ese artículo. El número se reinicia en cada
    artículo para que agregar un artículo nuevo no corra los ids de
    los demás.

    El espacio de "40 bis D" pasa a guion bajo y todo va en
    minúsculas para que el id se pueda leer y escribir a mano, que es
    para lo que sirve tenerlo predecible. No es una exigencia de
    Chroma. La regla de Chroma sobre qué caracteres se permiten es
    para el nombre de la colección, que es otra cosa, y está en la
    constante COLECCION.
    """
    contados, ids = {}, []

    for fragmento in fragmentos:
        clave = fragmento.metadata["articulo"].lower().replace(" ", "_")
        posicion = contados.get(clave, 0)
        contados[clave] = posicion + 1
        ids.append(f"art_{clave}_{posicion}")

    return ids


def revisar_fragmentos(fragmentos, textos):
    """Comprueba la integridad de los fragmentos antes de gastar.

    Es la comprobación local que pide la lección del Bloque 25, y no
    cuesta nada porque no llama a la API.

    Las dos sumas de caracteres se imprimen para comparar, y no se
    exigen iguales. En este corpus la de los fragmentos es mayor, y
    eso es lo esperado. La lección lo dice, el solape repite texto a
    propósito cada vez que un documento hay que partirlo, y aquí hay
    cinco incisos que pasan de 700 y se parten.

    Lo que sí es señal de alerta es un fragmento vacío o uno
    repetido, y esos dos cortan la indexación.
    """
    vacios = [i for i, f in enumerate(fragmentos)
              if not f.page_content.strip()]
    contenidos = [f.page_content for f in fragmentos]
    repetidos = len(contenidos) != len(set(contenidos))

    print(f"  fragmentos vacíos            "
          f"{vacios if vacios else 'ninguno'}")
    print(f"  fragmentos repetidos         "
          f"{'sí' if repetidos else 'no'}")
    print(f"  caracteres en los fragmentos "
          f"{sum(len(c) for c in contenidos)}")
    print(f"  caracteres en el corpus      "
          f"{sum(len(t) for t in textos)}")

    if vacios or repetidos:
        raise ValueError(
            "No se indexó nada. Hay fragmentos vacíos o repetidos, y "
            "eso significa que el partido salió mal. Revisa el tope y "
            "el solape antes de volver a intentar."
        )


def con_reintentos(operacion, max_intentos=4, espera_inicial=5):
    """Repite una operación solo si falla por límite de peticiones.

    Es el patrón de la guía de troubleshooting del Bloque 25.
    Cualquier otro error se vuelve a lanzar de inmediato, y si se
    agotan los intentos también, para que no quede oculto.
    """
    espera = espera_inicial

    for intento in range(1, max_intentos + 1):
        try:
            return operacion()
        except Exception as error:
            mensaje = str(error)
            es_limite = ("429" in mensaje
                         or "RESOURCE_EXHAUSTED" in mensaje)
            if not es_limite or intento == max_intentos:
                raise
            print(f"  límite de peticiones alcanzado, reintento "
                  f"{intento} de {max_intentos - 1} en {espera} s")
            time.sleep(espera)
            espera *= 2


def indexar_corpus(textos, metadatos, carpeta, coleccion,
                   tope=TOPE, solape=SOLAPE):
    """Parte, calcula embeddings y persiste. Devuelve el vector store.

    Recibe la carpeta y la colección como argumentos, igual que la
    receta del Bloque 25, para que indexar otro corpus sea llamarla
    con otros valores y no copiar su cuerpo.
    """
    fragmentos = fragmentar(textos, metadatos, tope, solape)
    revisar_fragmentos(fragmentos, textos)

    ids = ids_de(fragmentos)
    print(f"  son {len(fragmentos)} fragmentos y cada uno cuesta una "
          "llamada")

    almacen = con_reintentos(
        lambda: Chroma.from_documents(
            documents=fragmentos,
            embedding=GoogleGenerativeAIEmbeddings(
                model=MODELO_EMBEDDINGS),
            ids=ids,
            collection_name=coleccion,
            persist_directory=carpeta,
        )
    )
    print(f"  indexados {len(fragmentos)} fragmentos en {carpeta}")
    return almacen


def cargar_vectorstore(carpeta, coleccion):
    """Reconecta a un vector store ya indexado, sin recalcular nada.

    Conectarse no calcula ningún embedding y no cuesta nada. Eso es
    lo que se quiere demostrar, que el trabajo quedó hecho y
    guardado.
    """
    return Chroma(
        collection_name=coleccion,
        embedding_function=GoogleGenerativeAIEmbeddings(
            model=MODELO_EMBEDDINGS),
        persist_directory=carpeta,
    )


def hay_algo_en_disco(carpeta):
    """Dice si esa carpeta del índice ya tiene archivos adentro.

    Mira el disco y no abre el índice, para no tener dos clientes de
    Chroma sobre la misma carpeta en un mismo proceso.

    Recibe la carpeta como argumento y no la toma de la constante,
    igual que las otras funciones de este archivo, para que valga
    también si alguna vez se indexa otro corpus en otra carpeta.

    Es también la primera de las tres comprobaciones que pide la
    actividad del Bloque 24, que la carpeta se cree con archivos.
    """
    if not os.path.isdir(carpeta):
        return False
    return bool(os.listdir(carpeta))


if __name__ == "__main__":
    # El chequeo que pide la lección. Sin él, una clave ausente da un
    # error de validación desde dentro de la librería, que es otra
    # cosa y se diagnostica distinto.
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            'Falta GEMINI_API_KEY. Defínela en tu archivo ".env" y '
            "vuelve a ejecutar."
        )

    print("El índice")
    print(f"  carpeta     {os.path.abspath(CARPETA_INDICE)}")
    print(f"  colección   {COLECCION}")
    print()

    textos, metadatos = preparar_documentos()

    if "--verificar" in sys.argv:
        if not hay_algo_en_disco(CARPETA_INDICE):
            raise SystemExit(
                "No hay nada en esa carpeta. Corre primero la "
                "indexación, sin --verificar."
            )

        guardados = cargar_vectorstore(CARPETA_INDICE, COLECCION)
        cuantos = guardados._collection.count()
        esperados = len(fragmentar(textos, metadatos))

        print(f"  fragmentos guardados   {cuantos}")
        print(f"  el corpus de hoy da    {esperados}")
        print("  se contaron sin calcular ningún embedding, en un "
              "proceso nuevo")
        print()

        if cuantos == esperados:
            print("El índice está al día con el corpus.")
        else:
            print("El índice NO está al día. El corpus cambió desde la")
            print("última indexación y la búsqueda va a responder con")
            print("el texto viejo sin avisar de nada.")
            print("Corre python src/indexar_corpus.py --reindexar")
        sys.exit(0)

    ya_hay = hay_algo_en_disco(CARPETA_INDICE)
    if ya_hay and "--reindexar" not in sys.argv:
        print("Esa carpeta ya tiene un índice, así que no se indexó")
        print("nada y no se gastó ninguna llamada.")
        print()
        print("Para ver si está al día, --verificar")
        print("Para rehacerlo, --reindexar")
        sys.exit(0)

    indexar_corpus(textos, metadatos, CARPETA_INDICE, COLECCION)
    print()
    print("EJECUTAR CON --verificar para comprobar que quedó en "
          "disco.")
