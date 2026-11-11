"""Indexación del corpus legal en un vector store (Bloque 24).

Toma los once artículos del corpus, los parte con el tope que se
eligió midiendo, calcula un embedding por fragmento y guarda todo en
disco. Después de esto, la consulta del bloque siguiente se conecta
al índice sin volver a calcular nada.

Esta es la única parte de la cadena que hace llamadas reales a la
API. Una por fragmento.

Se corre desde la raíz del proyecto.

    python src/indexar_corpus.py
    python src/indexar_corpus.py --verificar

Por qué el corpus se importa y no se escribe de nuevo

El texto vive en soporte_corpus_legal.py, verificado artículo por
artículo contra la fuente. Copiarlo aquí crearía un segundo original
que se puede desincronizar del primero. La línea que lo importa se
queda además solo con el texto y descarta las claves de búsqueda,
que son de la búsqueda por palabra y no son ley.

Por qué 700 y 126

El tope es el que resultó de la medición de medir_chunks.py, con el
overlap en el dieciocho por ciento que usa el ejemplo de la lección.
La tabla y el razonamiento están en docs/limites_bloque24.md. En
este archivo van como constantes para que se vea de dónde salen y para que
cambiarlos sea un solo lugar.

Por qué la carpeta es una constante

La lección advierte que si el script de consulta apunta a una
carpeta distinta de la del script de indexación, el conteo devuelve
cero y parece que no se guardó nada. Dejándola como constante, el
script del bloque siguiente la importa en vez de volver a escribir
el texto y las dos no pueden quedar distintas.

Esa carpeta es contenido generado y está en el .gitignore, porque se
reconstruye corriendo esto de nuevo.

Por qué la comprobación vive en este mismo archivo

La lección pide comprobar la persistencia desde un intérprete nuevo,
para que no quede duda de que el índice está en disco y no en
memoria. Una invocación nueva es un intérprete nuevo, así que
--verificar cumple eso sin agregar un cuarto archivo, y de paso la
carpeta sigue escrita en un solo lugar.

Por qué se revisa antes de gastar

Volver a correr la indexación sobre una carpeta que ya tiene el
índice vuelve a pagar una llamada por fragmento, y eso es seguro.
Por eso el guardia se fija primero y no hace nada si ya hay algo.
Para reindexar de verdad hay que borrar la carpeta a mano, que es
una decisión y no un accidente.

Si la indexación se corta por la mitad

La lección dice que from_documents no guarda un progreso parcial que
se pueda retomar. Si se corta, la carpeta queda a medias, hay que
borrarla y correr de nuevo desde cero. Ante un 429 por límite de
peticiones, la lección indica esperar un minuto y repetir. No se
programó ningún reintento, por lo mismo que no lo tiene el agente,
que un reintento automático sobre algo que cuesta dinero conviene
que sea una decisión de quien lo corre.
"""

import os
import sys

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from soporte_corpus_legal import ARTICULOS

# La clave vive en el .env y la lee la librería por su cuenta, con el
# nombre GEMINI_API_KEY. No se nombra en este archivo ni se imprime.
load_dotenv()

CARPETA_INDICE = "vectorstore/"
TOPE = 700
SOLAPE = 126
MODELO_EMBEDDINGS = "models/gemini-embedding-001"


def partir_el_corpus():
    """Devuelve los fragmentos del corpus, listos para indexar.

    Cada artículo entra como un documento aparte, de modo que un
    fragmento nunca mezcla dos artículos. Eso no se configura, sale
    de pasarle una lista y no un texto solo.
    """
    textos = [texto for claves, texto in ARTICULOS]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=TOPE,
        chunk_overlap=SOLAPE,
    )
    return splitter.create_documents(textos)


def ya_esta_indexado():
    """Dice si la carpeta del índice ya tiene algo adentro.

    Mira el disco y no abre el índice. Abrirlo crearía un cliente de
    Chroma sobre la misma carpeta que después vuelve a abrir la
    indexación, y no hace falta para contestar esta pregunta.

    Es también la primera de las tres comprobaciones que pide la
    lección, que la carpeta se cree con archivos adentro.
    """
    if not os.path.isdir(CARPETA_INDICE):
        return False
    return bool(os.listdir(CARPETA_INDICE))


def contar_lo_guardado(embeddings):
    """Se conecta al índice que esté en disco y cuenta sus fragmentos.

    Conectarse no calcula ningún embedding y no cuesta nada. Eso es
    justamente lo que se quiere demostrar, que el trabajo quedó hecho
    y guardado.

    El conteo sale de _collection, que es un atributo privado de
    Chroma. Se usa porque es el que indica la lección y porque la
    clase no expone otro para esto. Un atributo privado puede cambiar
    de nombre entre versiones, y si eso pasa, esta línea es la que
    hay que mirar.
    """
    indice = Chroma(
        persist_directory=CARPETA_INDICE,
        embedding_function=embeddings,
    )
    return indice._collection.count()


if __name__ == "__main__":
    embeddings = GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)

    if "--verificar" in sys.argv:
        if not ya_esta_indexado():
            print(f"No hay nada en {CARPETA_INDICE}. Corre primero la "
                  "indexación, sin --verificar.")
            sys.exit(1)

        guardados = contar_lo_guardado(embeddings)
        print(f"El índice de {CARPETA_INDICE} tiene {guardados} "
              "fragmentos.")
        print("Se contaron sin calcular ningún embedding, en un "
              "intérprete nuevo.")
        sys.exit(0)

    fragmentos = partir_el_corpus()

    if ya_esta_indexado():
        print(f"La carpeta {CARPETA_INDICE} ya tiene el índice, así que "
              "no se indexó nada.")
        print(f"El corpus de hoy daría {len(fragmentos)} fragmentos y "
              "cada uno cuesta una llamada.")
        print("Para contar lo que hay, córrelo con --verificar.")
        print("Para reindexar, borra la carpeta y vuelve a correr esto.")
        sys.exit(0)

    print(f"Partiendo el corpus con tope {TOPE} y overlap {SOLAPE}.")
    print(f"Son {len(fragmentos)} fragmentos y cada uno cuesta una "
          "llamada de embeddings.")

    Chroma.from_documents(
        documents=fragmentos,
        embedding=embeddings,
        persist_directory=CARPETA_INDICE,
    )

    print(f"Indexados {len(fragmentos)} fragmentos en {CARPETA_INDICE}")
    print("Ahora córrelo con --verificar para comprobar que quedó en "
          "disco.")
