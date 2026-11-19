"""Indexación del corpus legal en un vector store (Bloques 24, 25 y 28).

Toma los once artículos del corpus, los parte respetando sus incisos,
calcula un embedding por fragmento y guarda todo en disco. Después de
esto, la consulta del Bloque 26 se conecta al índice sin volver a
calcular nada.

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

Por qué la indexación borra los ids que sobran

Sobrescribir alcanza mientras los ids nuevos incluyan a los viejos.
Cuando una configuración produce menos fragmentos que la anterior,
los ids que sobran quedan en la colección con su texto antiguo y la
búsqueda los sigue recuperando, mezclados con los nuevos.

Eso pasó al cambiar el tope de 700 a 1500, que bajó el corpus de
cuarenta y cinco fragmentos a diecinueve. El artículo 163 pasó de
siete fragmentos a tres, y sus ids art_163_3 a art_163_6 no se
sobrescribieron porque ya no se generan. Lo detectó --verificar, que
contó cuarenta y cinco guardados contra diecinueve esperados.

Por eso la indexación borra, al terminar, los ids que están en la
colección y no están en la tanda que acaba de escribir. Borra después
y no antes para que un fallo a mitad de camino no deje el índice
vacío.

El cambio posterior de 1500 a 1300 sube de diecinueve fragmentos a
veintidós, así que no deja ninguno sobrante. El borrado se queda
igual, porque el caso puede volver cada vez que el tope suba.

Por qué los incisos se separan con línea en blanco antes de partir

El corpus separa sus incisos con un salto de línea, igual que separa
las letras a) y b) de adentro de un inciso. El splitter prefiere
cortar en línea en blanco y después en salto simple, de modo que sin
esa distinción trata el borde entre dos incisos igual que el borde
entre dos letras, y corta en cualquiera de los dos.

Medido sobre este corpus, trece de los cuarenta y cinco fragmentos de
la configuración anterior empezaban a media oración o en una letra
suelta. Cuatro de ellos traían una regla sin la condición que la
limita, porque esa condición vive en el encabezado de su inciso.

El daño se vio en una respuesta real. El modelo presentó como regla
general de cálculo el promedio de los últimos once años del artículo
40 bis D, que rige solo para la jornada parcial de treinta horas o
menos, porque el fragmento que lo traía se cortaba antes de la nota
de alcance.

La línea en blanco se agrega aquí y no en el corpus. El texto está
verificado contra la fuente y esta es una decisión de indexación, no
del texto. Lo único que se inserta son saltos de línea, así que el
contenido sin espacios queda idéntico y eso se puede comprobar.

Por qué el tope es 1300 y el solape 234

El criterio estructural da un piso y no un valor. La unidad legal más
larga de este corpus mide 1057 caracteres, y medido con una grilla
fina el piso es ese mismo valor y no uno más, porque en 1056 se parte
una unidad y en 1057 no se parte ninguna. Por encima del piso ninguna
unidad se parte por dentro, y lo único que el tope decide es cuántas
unidades enteras se empaquetan en un mismo fragmento.

El piso tiene dos razones medidas y no una.

La primera es de estructura. Una unidad partida por dentro puede
entregar una regla sin la condición que la limita, que es lo que
produjo las dos respuestas legalmente equivocadas de la sección 5 del
docs/limites_bloque26.md.

La segunda es de recuperación. Una unidad partida se recupera peor
que la unidad entera, porque el embedding representa lo que hay en
ese pedazo. El inciso 1 del artículo 172 mide 779 caracteres, con
tope 700 se parte y no alcanza el top 3 de la consulta del cálculo.
Con cualquier tope por encima del piso cabe entero y sí lo alcanza.

Por encima del piso la partición no cambia de a un carácter sino por
tramos. Se barrió el tope de uno en uno desde el piso hasta 1600, y
los tramos largos son 1071 a 1153 con treinta fragmentos, 1172 a 1220
con veintisiete, 1229 a 1273 con veinticuatro, 1293 a 1351 con
veintidós y 1447 a 1600 con diecinueve. El conteo no es estrictamente
decreciente, porque en 1070 baja a veintinueve y en 1071 vuelve a
treinta.

Cuál tramo se toma se decidió midiendo cuatro cosas.

    el recall es plano arriba del piso, 0.857 en 1100, 1250 y
    1500, y fallan las mismas tres preguntas

    el costo de la entrada baja cuando baja el tope, 0.87x,
    0.91x y 1.00x

    el primer fragmento es relevante en doce preguntas de
    dieciseis con 1300 y en diez con 1500

    el tope de noventa unidades de fomento del artículo 172
    solo viaja junto a la base de cálculo desde 1293

La última es la que decide. El artículo 172 con sus incisos separados
mide 1293 caracteres, su base de cálculo vive en el primer inciso y
su tope de noventa unidades de fomento en el tercero. Por debajo de
1293 el artículo no cabe entero, ese tercer inciso queda en otro
fragmento y la consulta del cálculo recupera la base sin el tope. Es
un límite legal real sobre lo que se paga.

Y 1293 es justo donde empieza el tramo de veintidós fragmentos. El
conteo baja a veintidós porque ese artículo pasa a caber en un
fragmento, así que la frontera del tramo y el largo del artículo son
el mismo número.

El valor entregado no es más fino que eso. Comparando fragmento por
fragmento, desde 1293 hasta 1345 la partición es idéntica, no solo en
cantidad sino en contenido, de modo que cincuenta y tres valores de
tope producen exactamente los mismos veintidós fragmentos. Lo que se
midió es la banda, y 1300 es un número redondo adentro. Con 1294 o
con 1330 el sistema sería el mismo.

Las tablas están en docs/limites_bloque28.md, y los scripts que las
produjeron son src/medir_incisos.py y src/comparar_topes.py.

Dos de esas cuatro condiciones quedaron confirmadas después por
corridas que no son las que eligieron el tope. La tercera sale igual
de src/resultados_evaluacion.txt, donde la precisión con k=1 vale
0.750 sobre dieciséis preguntas, que son doce. La cuarta se ve
entera en la corrida de src/probar_generacion.py, donde la respuesta
de la consulta del cálculo cita el tope de noventa unidades de
fomento. No es que el fragmento llegue, es que el límite aparece en
la respuesta.

Esto queda fuera de lo que la lección sugiere

La lección del Bloque 24 habla de unos pocos cientos de caracteres
con un overlap del quince al veinte por ciento, y la actividad no
impone un chunk_size y pide elegirlo con criterio. La sección 7 del
docs/limites_bloque24.md usó esa sugerencia como argumento para
descartar el tope de 1000.

Este corpus no permite quedarse en ese rango. Su unidad legal más
larga mide 1057 caracteres y partirla por dentro produce los dos
errores de arriba. De las mesetas por encima del piso se toma la que
cumple las cuatro condiciones, que es la menor desviación posible que
sirve.

El solape sí queda dentro de lo sugerido, en el dieciocho por ciento,
la misma proporción del Bloque 24. Con este tope no hace nada, y eso
está medido. Ningún par de fragmentos consecutivos comparte un solo
carácter. Con tope 700 se repiten 605 caracteres, con 1500 se repiten
248 y con 1300 se repiten cero.

El splitter arrastra solape solo si lo que queda al cerrar un
fragmento cabe en los 234 caracteres del presupuesto, y en este tope
la unidad del borde siempre es más larga que eso. No es un defecto,
es una consecuencia del piso. El solape existe para que un concepto
cortado sobreviva en los dos pedazos, y por encima del piso no se
corta nada. Queda definido por la proporción del Bloque 24 para que
lo fije la misma regla, y vuelve a servir solo si alguna unidad
llegara a superar el tope, que es el caso del procedimiento de abajo.

Qué hacer cuando el corpus cambie

Este procedimiento es propio. Ni la plataforma ni los dos trabajos
citados en el documento del Bloque 28 lo prescriben, y existe porque
esta implementación hace que el tope decida la integridad de la
unidad.

Agregar o editar un artículo puede alargar la unidad más larga, así
que hay que volver a correr src/medir_incisos.py y subir el tope si
el piso se movió. Sacar un artículo no puede romper el piso, pero
puede dejar el tope más alto de lo necesario, y eso cuesta sin dar
nada.

Cortando por estructura de forma explícita, como hacen los dos
trabajos citados, el tope dejaría de decidir la integridad y este
procedimiento sobraría. Queda anotado como pendiente.

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
fragmentos que ya habían entrado. Con este corpus son veintidós y el
429 es improbable, así que se acepta. Con un corpus grande convendría
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
TOPE = 1300
SOLAPE = 234
MODELO_EMBEDDINGS = "models/gemini-embedding-001"

# Reconoce "Art. 162.", "Art. 40 bis D." y "[1] Artículo 66.-", que
# son las tres formas con que el corpus abre un artículo.
ETIQUETA = re.compile(
    r"(?:\[1\]\s*)?Art(?:ículo)?\.?\s+([\w\s]+?)\s*[.\-]"
)

# Un salto de línea que precede a un inciso [n] o a una causal
# numerada N.- pasa a ser línea en blanco. Las letras a), b) y c) de
# adentro de un inciso conservan el salto simple, y eso es lo que
# hace que el splitter corte primero entre incisos y solo después
# dentro de uno.
SEPARA_INCISOS = re.compile(r"\n(?=(?:\[\d+\]|\d+\.-))")


def separar_incisos(texto):
    """Deja una línea en blanco entre los incisos de un artículo.

    Solo inserta saltos de línea. Ninguna palabra del texto legal
    cambia, y eso se puede comprobar comparando el contenido sin
    espacios de antes y de después.
    """
    return SEPARA_INCISOS.sub("\n\n", texto)


def preparar_documentos():
    """Devuelve los textos del corpus y un metadato por cada uno.

    El metadato lleva el número del artículo. El splitter lo copia a
    cada fragmento que salga de ese texto, así que un fragmento del
    medio de un artículo sigue sabiendo de dónde viene.

    Los incisos salen separados por línea en blanco, para que el
    splitter corte entre incisos antes que dentro de uno. La cabecera
    explica por qué.
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
        textos.append(separar_incisos(texto))
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
    artículos que pasan del tope y se parten en varios fragmentos.

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

    Al terminar borra los ids que quedaron de una configuración
    anterior y que esta tanda ya no produce. La cabecera explica por
    qué hace falta.
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

    sobrantes = sorted(set(almacen.get()["ids"]) - set(ids))
    if sobrantes:
        almacen.delete(ids=sobrantes)
        print(f"  borrados {len(sobrantes)} fragmentos que habían "
              "quedado de una configuración anterior")
        print(f"    {', '.join(sobrantes[:6])}"
              f"{' y otros' if len(sobrantes) > 6 else ''}")

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
    print(f"  tope {TOPE}, solape {SOLAPE}")
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
