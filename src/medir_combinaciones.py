"""Medición local del tope y el solape, antes de gastar llamadas.

Responde dos preguntas sin tocar la API, porque partir texto es una
operación local.

La primera es dónde están los topes que importan. Un tope solo vale
la pena probarlo si en ese punto empiezan a entrar enteros incisos
que antes se partían. Entre dos umbrales, subir el tope no cambia
nada estructural.

La segunda es cuánto costaría cada combinación de tope y solape. El
número de fragmentos es el número de llamadas de embeddings que esa
configuración va a cobrar al indexarla.

Es el paso previo a medir la recuperación de verdad. Primero se mira
la grilla completa gratis, y recién después se paga por las
combinaciones que valga la pena indexar.

No reemplaza a medir_chunks.py. Ese eligió el tope mirando cómo
quedaba partido el texto. Este prepara la medición de si la búsqueda
encuentra mejor, que es otra cosa.

Se corre con el botón de ejecutar, o desde la terminal con
`python src/medir_combinaciones.py`, desde la raíz del proyecto.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from soporte_corpus_legal import ARTICULOS

CORPUS = [texto for claves, texto in ARTICULOS]

INCISOS = [
    linea.strip()
    for texto in CORPUS
    for linea in texto.split("\n")
    if linea.strip()
]

# Los topes de la grilla. Los de arriba del 500 se eligen mirando la
# tabla de umbrales que este mismo archivo imprime primero.
TOPES = (400, 500, 600, 700, 800, 900, 1000)

# Los solapes, como proporción del tope. El 18 es el actual y viene
# del ejemplo de la lección. Los otros lo rodean para poder
# compararlo en vez de darlo por bueno.
PROPORCIONES = (0.10, 0.18, 0.25, 0.35)


def empieza_en_inciso(chunk):
    """Dice si el chunk arranca donde arranca algún inciso."""
    return any(
        inciso.startswith(chunk[:30]) or chunk.startswith(inciso[:30])
        for inciso in INCISOS
    )


def incisos_adentro(chunk):
    """Cuenta cuántos incisos empiezan dentro del fragmento."""
    return sum(1 for inciso in INCISOS if inciso[:30] in chunk)


def partir(tope, solape):
    """Parte el corpus y devuelve los textos de los fragmentos."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=tope,
        chunk_overlap=solape,
    )
    return [c.page_content for c in splitter.create_documents(CORPUS)]


if __name__ == "__main__":
    largos = sorted(len(i) for i in INCISOS)

    print("El corpus")
    print(f"  {len(CORPUS)} artículos, "
          f"{sum(len(t) for t in CORPUS)} caracteres")
    print(f"  {len(INCISOS)} incisos")
    print(f"  el inciso más largo mide {largos[-1]}")
    print()

    # Primera pregunta. Cuántos incisos entran enteros en cada tope.
    # Donde ese número salta es donde el tope cambia algo. Donde se
    # queda igual, subir el tope solo junta más incisos sin salvar
    # ninguno.
    print("Cuántos incisos entran enteros en cada tope")
    print()
    print(f"  {'tope':>6}  {'enteros':>7}  {'del total':>9}"
          f"  {'ganados':>8}")
    print("  " + "-" * 36)

    antes = None
    for tope in range(300, 1101, 100):
        enteros = sum(1 for largo in largos if largo <= tope)
        ganados = "" if antes is None else f"+{enteros - antes}"
        porcentaje = enteros / len(largos)
        print(f"  {tope:>6}  {enteros:>7}  {porcentaje:>8.0%}"
              f"  {ganados:>8}")
        antes = enteros

    print()
    print("  Un tope vale la pena probarlo donde la columna ganados")
    print("  no es cero. Entre dos umbrales, subir el tope no salva")
    print("  ningún inciso y solo junta más.")
    print()

    # Los largos de los incisos que todavía no entran en el tope
    # actual, que son los que marcan los umbrales de más arriba.
    sobre_700 = [largo for largo in largos if largo > 700]
    print(f"  Los {len(sobre_700)} incisos que no entran en 700 miden")
    print(f"  {sobre_700}")
    print()

    # Segunda pregunta. La grilla completa, con lo que costaría cada
    # combinación.
    print("La grilla de tope por solape")
    print()
    print("  fragmentos, que es lo que costaría indexar cada una")
    print()

    encabezado = "  " + f"{'tope':>6}"
    for proporcion in PROPORCIONES:
        encabezado += f"  {proporcion:>9.0%}"
    print(encabezado)
    print("  " + "-" * (6 + 11 * len(PROPORCIONES)))

    grilla = {}
    for tope in TOPES:
        fila = f"  {tope:>6}"
        for proporcion in PROPORCIONES:
            solape = round(tope * proporcion)
            trozos = partir(tope, solape)
            grilla[(tope, proporcion)] = trozos
            fila += f"  {len(trozos):>9}"
        print(fila)

    print()
    print("  limpios, los que empiezan donde empieza un inciso")
    print()
    print(encabezado)
    print("  " + "-" * (6 + 11 * len(PROPORCIONES)))

    for tope in TOPES:
        fila = f"  {tope:>6}"
        for proporcion in PROPORCIONES:
            trozos = grilla[(tope, proporcion)]
            limpios = sum(1 for t in trozos if empieza_en_inciso(t))
            fila += f"  {limpios / len(trozos):>9.0%}"
        print(fila)

    print()
    print("  mezclados, los que traen dos o más incisos adentro")
    print()
    print(encabezado)
    print("  " + "-" * (6 + 11 * len(PROPORCIONES)))

    for tope in TOPES:
        fila = f"  {tope:>6}"
        for proporcion in PROPORCIONES:
            trozos = grilla[(tope, proporcion)]
            mezclados = sum(1 for t in trozos if incisos_adentro(t) > 1)
            fila += f"  {mezclados / len(trozos):>9.0%}"
        print(fila)

    print()
    total = sum(len(t) for t in grilla.values())
    print(f"Indexar la grilla entera costaría {total} llamadas.")
    print("Por eso esta tabla va primero y después se elige qué")
    print("combinaciones vale la pena pagar.")
