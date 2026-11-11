"""Medición para elegir el chunk_size del corpus legal (Bloque 24).

La actividad no impone un chunk_size, pide elegirlo con criterio.
Este archivo es ese criterio. Parte el mismo corpus con varios topes
y mide qué pasa con cada uno, para que el valor que queda en
indexar_corpus.py esté respaldado por una corrida y no por una
preferencia.

Qué mide cada columna

chunks es cuántos fragmentos salen, y es también cuántas llamadas de
embeddings va a costar la indexación, porque se calcula uno por
fragmento.

limpios es cuántos de esos fragmentos empiezan donde empieza un
inciso y no a mitad de una regla. En este corpus cada inciso es una
norma completa, y un fragmento que arranca a mitad de una norma la
entrega partida. Mide dónde empieza el fragmento y no si la norma
llegó completa, de modo que un fragmento que arranca cortado pero
que trae el final por el overlap cuenta igual como no limpio.

mezclados es cuántos fragmentos traen dos o más incisos adentro, y
es la contraparte de limpios. Hace falta porque limpios sola premia
el tope grande. Con menos fragmentos hay menos comienzos que puedan
estar mal, así que el porcentaje mejora sin que el corpus quede
mejor partido. Un tope de 5000 metería cada artículo completo en un
fragmento y la columna los marcaría todos limpios, con el corpus sin
partir. La lección advierte lo contrario, que un fragmento que
mezcla temas distintos produce un embedding a medio camino entre
todos ellos. Esta columna es esa advertencia convertida en número, y
el tope se elige mirando las dos a la vez.

corto, mediana y largo son los tamaños de los fragmentos, y sirven
para ver que el tope no quedó tan chico que los parta todos ni tan
grande que no parta ninguno.

El overlap va en el dieciocho por ciento del tope en todas las
filas, que es la proporción del ejemplo de la lección, veinte sobre
ciento diez. Se deja fija para que lo único que cambie entre filas
sea el tope.

Los números de la corrida y el tope elegido están en
docs/limites_bloque24.md. En este archivo no van escritos, porque el
script lee el corpus que haya en ese momento y los números cambian
con él. Al agregar los artículos 159 y 172, los incisos pasaron de
53 a 66 y la mediana de sus largos bajó de 302 a 244 caracteres, así
que cada vez que el corpus crece esta medición se vuelve a correr.

No llama a ningún modelo y no gasta tokens. El chunking es una
operación local sobre texto que ya está en memoria, así que se puede
correr todas las veces que haga falta.

Se corre con python src/medir_chunks.py
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from soporte_corpus_legal import ARTICULOS

# Los textos, sin las claves de búsqueda.
CORPUS = [texto for claves, texto in ARTICULOS]

# Los incisos, que son la unidad real del corpus. Sirven para saber
# cuántos chunks empiezan justo donde empieza un inciso y cuántos
# empiezan a mitad de uno.
INCISOS = [
    linea.strip()
    for texto in CORPUS
    for linea in texto.split("\n")
    if linea.strip()
]

# Los tamaños a comparar. El 200 es el del ejemplo de la lección y va
# para tener la referencia.
TAMANOS = (200, 300, 400, 500, 700, 1000)


def empieza_en_inciso(chunk):
    """Dice si el chunk arranca donde arranca algún inciso.

    Se compara contra los primeros treinta caracteres y no contra el
    inciso completo, porque el chunk puede terminar antes de que el
    inciso termine.

    Treinta alcanzan para este corpus, donde ningún inciso empieza
    igual que otro en ese tramo. Es una comparación de prefijo, de
    modo que confirma dónde empieza el chunk y no que el chunk
    completo calce con un inciso completo.
    """
    return any(
        inciso.startswith(chunk[:30]) or chunk.startswith(inciso[:30])
        for inciso in INCISOS
    )


def incisos_adentro(chunk):
    """Cuenta cuántos incisos empiezan dentro del fragmento.

    Es la contraparte de empieza_en_inciso. Esa mira el comienzo del
    fragmento y esta mira el fragmento entero, para saber cuántas
    normas distintas quedaron juntas en un mismo embedding.

    Usa los mismos treinta caracteres de prefijo, que en este corpus
    identifican a cada inciso sin repetirse, y los busca en cualquier
    posición y no solo al principio.
    """
    return sum(1 for inciso in INCISOS if inciso[:30] in chunk)


if __name__ == "__main__":
    print("El corpus")
    print(f"  {len(CORPUS)} artículos, "
          f"{sum(len(t) for t in CORPUS)} caracteres")
    print(f"  {len(INCISOS)} incisos")
    print()

    print(f"{'tope':>6}  {'chunks':>6}  {'corto':>6}  {'mediana':>7}"
          f"  {'largo':>6}  {'limpios':>10}  {'mezclados':>10}")
    print("  " + "-" * 63)

    for tope in TAMANOS:
        # El overlap va en el 18% del tope, que es la proporción que
        # la lección usa en su propio ejemplo, 20 sobre 110.
        solape = round(tope * 0.18)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=tope,
            chunk_overlap=solape,
        )
        chunks = splitter.create_documents(CORPUS)
        textos = [c.page_content for c in chunks]

        largos = sorted(len(t) for t in textos)
        limpios = sum(1 for t in textos if empieza_en_inciso(t))
        mezclados = sum(1 for t in textos if incisos_adentro(t) > 1)

        print(f"{tope:>6}  {len(chunks):>6}  {largos[0]:>6}"
              f"  {largos[len(largos) // 2]:>7}  {largos[-1]:>6}"
              f"  {limpios:>3} de {len(chunks):<3}"
              f"  {mezclados:>3} de {len(chunks):<3}")

    print()
    print("Qué mirar en cada columna")
    print("  chunks    cuántas llamadas de embeddings va a costar")
    print("  limpios   cuántos empiezan donde empieza un inciso")
    print("            y no a mitad de una regla")
    print("  mezclados cuántos traen dos o más incisos adentro,")
    print("            que es el costo de un tope grande")
    print()
    print("El tope se elige mirando las dos últimas a la vez.")
    print("Limpios sola premia el tope grande, porque con menos")
    print("fragmentos hay menos comienzos que puedan estar mal.")
    print()
    print("Y un ejemplo completo, para verlo con los ojos.")

    # El tope elegido, para ver fragmentos de verdad y no solo
    # números. Se imprimen tres y no todos, porque son decenas. Si la
    # tabla de arriba llegara a favorecer otro tope, este valor y el
    # de indexar_corpus.py tienen que cambiar juntos.
    MUESTRA = 700
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MUESTRA,
        chunk_overlap=round(MUESTRA * 0.18),
    )
    chunks = splitter.create_documents(CORPUS)

    print(f"\nCon chunk_size={MUESTRA}, los tres primeros chunks\n")
    for i, chunk in enumerate(chunks[:3]):
        texto = chunk.page_content
        print(f"--- chunk {i} ({len(texto)} caracteres) ---")
        print(texto)
        print()

    # Qué junta el tope elegido. La columna mezclados cuenta por
    # igual dos cosas distintas. Juntar dos reglas independientes es
    # un defecto, y juntar dos números de una misma enumeración no lo
    # es, porque los números del 159 y del 160 son una lista bajo un
    # mismo encabezado y quien pregunta por las causales las quiere
    # juntas. Para distinguirlos hay que identificar cada inciso,
    # comparando su largo contra el inventario, y ver si los
    # identificados pertenecen a la misma enumeración. El largo solo
    # no alcanza, porque los dos grupos se solapan. La clasificación
    # de la corrida está en docs/limites_bloque24.md.
    print(f"Con chunk_size={MUESTRA}, qué juntan los mezclados\n")
    for i, chunk in enumerate(chunks):
        dentro = [x for x in INCISOS if x[:30] in chunk.page_content]
        if len(dentro) < 2:
            continue
        largos_incisos = sorted(len(x) for x in dentro)
        print(f"  fragmento {i:>2}   {len(dentro)} incisos   "
              f"largos {largos_incisos}")
        print(f"                 empieza con {dentro[0][:44]}")
