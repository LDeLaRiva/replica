"""Evaluación de la recuperación, precisión y recall (Bloque 27).

Corre un conjunto de dieciséis preguntas etiquetadas a mano contra el
retriever real y mide si la búsqueda trae los fragmentos que de
verdad responden cada una.

Se corre con el botón de ejecutar, o desde la terminal con
`python src/evaluacion_recuperacion.py`, desde la raíz del proyecto.

Cuesta una llamada por pregunta, el embedding de cada una. No llama
al modelo de chat, porque esto mide la recuperación y no la
respuesta.

Por qué las etiquetas son frases y no ids

Un id como art_163_1 significa el segundo pedazo del artículo 163, y
cuál es ese pedazo depende del chunk_size. Etiquetando por id, las
etiquetas sirven solo con el tope de hoy y habría que rehacerlas
para medir otro.

Las frases del texto legal no cambian con el tope. El id se calcula
a partir de ellas contra el índice que esté puesto, de modo que el
mismo conjunto sirve para comparar configuraciones distintas.

De paso, una frase mal copiada no pasa en silencio. El script la
busca antes de medir y corta si no la encuentra o si calza en más de
un artículo.

Cómo se etiquetó

Las preguntas las escribió la autora del proyecto, pensando en lo
que consulta un trabajador. Para cada una eligió el artículo y el
inciso que la responde, leyendo el Código y no el resultado de la
búsqueda, que es lo que la lección pide.

Ninguna de estas dieciséis se había corrido antes contra el
retriever. Las cuatro consultas del Bloque 26 eran otras. La única
salvedad está escrita en docs/limites_bloque27.md.

Por qué se recupera una sola vez y después se corta

La curva de k no necesita una corrida por cada valor. Se recupera
con el k más alto, y para cada k menor se miran los primeros k de
esa misma lista, que es el mismo resultado. Así la curva entera
cuesta lo mismo que una sola corrida.

Es lo que hace la lección 1 de este bloque con su ranked[:k].

Por qué las preguntas sin respuesta bajan la precisión

Dos de las dieciséis no se pueden responder con este corpus. Para
esas, la fórmula de la lección devuelve precisión 0.0, porque nada
de lo recuperado puede ser correcto, y ese cero entra en el
promedio. El recall sí queda fuera.

No se corrige, porque es la fórmula que la plataforma define. Lo que
sí hay que saber es que la precisión promedio de este conjunto no se
puede comparar contra la de otro que tenga otra proporción de
preguntas sin respuesta. Entre corridas de este mismo conjunto sí,
que es para lo que sirve.
"""

import os
from datetime import date

from dotenv import load_dotenv

from indexar_corpus import (
    CARPETA_INDICE,
    COLECCION,
    MODELO_EMBEDDINGS,
    SOLAPE,
    TOPE,
    cargar_vectorstore,
)

load_dotenv()

# El k que usa la configuración actual del proyecto. Salió de la
# medición del Bloque 26 y es el que este archivo pone a prueba.
K_ELEGIDO = 4

# Hasta dónde llega la curva. Recuperar ocho cuesta lo mismo que
# recuperar cuatro, así que la curva sale gratis.
K_MAX = 8

ARCHIVO_RESULTADOS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resultados_evaluacion.txt"
)

# Las dieciséis preguntas, con las frases del texto legal que las
# responden. Una tupla de frases vacía es una pregunta que el corpus
# no puede responder, y la actividad pide incluir esos casos.
CASOS = (
    {
        "pregunta": "soy subgerente, ¿el despido es distinto para "
                    "mi cargo?",
        "frases": (
            "tales como gerentes, subgerentes, agentes o apoderados",
        ),
    },
    {
        "pregunta": "tengo un conflicto con una compañera que me "
                    "hostiga y no tengo pruebas, ¿pueden despedirme "
                    "por eso?",
        "frases": (
            "conductas indebidas de carácter grave, debidamente "
            "comprobadas",
        ),
    },
    {
        "pregunta": "¿en qué casos se termina el contrato sin que "
                    "nadie despida a nadie?",
        "frases": (
            "El contrato de trabajo terminará en los siguientes casos",
            "6.- Caso fortuito o fuerza mayor",
        ),
    },
    {
        "pregunta": "me avisaron el despido con una carta común, no "
                    "certificada, ¿vale igual?",
        "frases": (
            "personalmente o por carta certificada enviada al "
            "domicilio señalado en el contrato",
        ),
    },
    {
        "pregunta": "mi contrato a plazo fijo venció y no me dijeron "
                    "nada, ¿se terminó solo?",
        "frases": (
            "4.- Vencimiento del plazo convenido en el contrato",
        ),
    },
    {
        "pregunta": "mi contrato a plazo fijo venció y yo seguí "
                    "yendo a trabajar, ¿qué pasa con mi contrato?",
        "frases": (
            "El hecho de continuar el trabajador prestando servicios "
            "con conocimiento del empleador",
        ),
    },
    {
        "pregunta": "mi empleador no pagó mis cotizaciones y me "
                    "despidió, ¿qué pasa con ese despido?",
        "frases": (
            "éste no producirá el efecto de poner término al "
            "contrato de trabajo",
        ),
    },
    {
        "pregunta": "¿qué se cuenta como sueldo para calcular la "
                    "indemnización?",
        "frases": (
            "la última remuneración mensual comprenderá toda "
            "cantidad que estuviere percibiendo",
        ),
    },
    {
        "pregunta": "¿cómo se calcula el aguinaldo en un contrato "
                    "indefinido?",
        "frases": (),
    },
    {
        "pregunta": "trabajo veinte horas a la semana, ¿cómo se "
                    "calcula mi indemnización?",
        "frases": (
            "una jornada de trabajo no superior a treinta horas "
            "semanales",
            "se entenderá por última remuneración el promedio de las "
            "remuneraciones percibidas",
        ),
    },
    {
        "pregunta": "me despidieron por necesidades de la empresa, "
                    "¿a qué tengo derecho?",
        "frases": (
            "a lo menos con treinta días de anticipación",
            "una indemnización equivalente a treinta días de la "
            "última remuneración mensual devengada por cada año de "
            "servicio",
        ),
    },
    {
        "pregunta": "¿en qué consiste la indemnización por años de "
                    "servicio y qué incluye?",
        "frases": (
            "una indemnización equivalente a treinta días de la "
            "última remuneración mensual devengada por cada año de "
            "servicio",
        ),
    },
    {
        "pregunta": "¿en qué casos tengo fuero laboral?",
        "frases": (
            "gozará de fuero laboral por el periodo de un mes",
        ),
    },
    {
        "pregunta": "¿cómo se calcula mi finiquito?",
        "frases": (),
    },
    {
        "pregunta": "¿hay diferencia en el finiquito si mi contrato "
                    "es indefinido o a plazo fijo?",
        "frases": (
            "Si el contrato hubiere estado vigente un año o más y el "
            "empleador le pusiere término en conformidad al artículo "
            "161",
            "4.- Vencimiento del plazo convenido en el contrato",
        ),
    },
    {
        "pregunta": "creo que me despidieron injustamente, ¿qué "
                    "puedo hacer?",
        "frases": (
            "podrá recurrir al juzgado competente, dentro del plazo "
            "de sesenta días hábiles",
        ),
    },
)


def normalizar(texto):
    """Deja el texto con un solo espacio entre palabras.

    El corpus separa los incisos con salto de línea y las frases de
    las etiquetas se escriben de corrido. Sin esto, una frase que
    cruza un salto no se encontraría nunca.
    """
    return " ".join(texto.split())


def ids_con_la_frase(frase, guardado):
    """Devuelve los ids de los fragmentos que contienen esa frase.

    Busca contra lo que está guardado en el índice y no contra una
    partición hecha de nuevo, para que una etiqueta no pueda apuntar
    a un fragmento que en el índice no existe.
    """
    buscada = normalizar(frase)
    return {
        ident
        for ident, texto in zip(guardado["ids"], guardado["documents"])
        if buscada in normalizar(texto)
    }


def resolver_etiquetas(casos, guardado):
    """Traduce las frases de cada caso a los ids del índice.

    Corta si alguna frase no aparece. Una etiqueta que no resuelve
    haría que esa pregunta midiera cero sin que nada avise, y un cero
    por una etiqueta mal copiada se parece demasiado a un cero por
    una recuperación mala.
    """
    resueltos, rotas = [], []

    for numero, caso in enumerate(casos, start=1):
        relevantes = set()
        for frase in caso["frases"]:
            encontrados = ids_con_la_frase(frase, guardado)
            if not encontrados:
                rotas.append((numero, frase))
            relevantes |= encontrados

        resueltos.append({
            "pregunta": caso["pregunta"],
            "ids_relevantes": relevantes,
        })

    if rotas:
        detalle = "\n".join(
            f"  pregunta {n}, {f[:50]}" for n, f in rotas
        )
        raise ValueError(
            "Hay frases que no aparecen en ningún fragmento del "
            "índice. O están mal copiadas, o el índice no está al "
            f"día con el corpus.\n{detalle}"
        )

    return resueltos


def precision_at_k(ids_recuperados, ids_relevantes):
    """Fracción de los recuperados que son relevantes.

    Devuelve 0.0 si el retriever no devolvió ninguno.
    """
    if not ids_recuperados:
        return 0.0
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_recuperados)


def recall_at_k(ids_recuperados, ids_relevantes):
    """Fracción de los relevantes que se recuperaron.

    Devuelve None si el caso no tiene relevantes, porque no hay nada
    que recuperar y la fracción no está definida.
    """
    if not ids_relevantes:
        return None
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_relevantes)


def f1(precision, recall):
    """Media armónica de precisión y recall."""
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def promediar(valores):
    """Promedio que ignora los None y evita dividir por cero."""
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else 0.0


def recuperar_todo(retriever, casos):
    """Recupera una vez por pregunta y guarda la lista completa.

    Es la única parte que llama a la API. Después, cada k se calcula
    cortando esta misma lista.
    """
    return [
        [c.id for c in retriever.invoke(caso["pregunta"])]
        for caso in casos
    ]


def evaluar(recuperados, casos, k):
    """Mide precisión y recall con los primeros k de cada lista."""
    resultados = []

    for ids, caso in zip(recuperados, casos):
        cortados = ids[:k]
        resultados.append({
            "pregunta": caso["pregunta"],
            "precision": precision_at_k(cortados,
                                        caso["ids_relevantes"]),
            "recall": recall_at_k(cortados, caso["ids_relevantes"]),
        })

    return (
        resultados,
        promediar(x["precision"] for x in resultados),
        promediar(x["recall"] for x in resultados),
    )


def lineas_del_detalle(resultados):
    """Una línea por pregunta, con su precisión y su recall."""
    lineas = []
    for r in resultados:
        recall = "n/a" if r["recall"] is None else f"{r['recall']:.2f}"
        lineas.append(
            f"{r['precision']:.2f}  {recall}  {r['pregunta']}"
        )
    return lineas


def escribir_resultados(ruta, resultados, precision, recall, k):
    """Deja el registro de la corrida, para comparar con la próxima."""
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(f"Fecha: {date.today()}\n")
        archivo.write(
            f"Configuracion: k={k}, chunk_size={TOPE}, "
            f"chunk_overlap={SOLAPE}\n"
        )
        archivo.write(f"Embeddings: {MODELO_EMBEDDINGS}\n")
        archivo.write("Splitter: RecursiveCharacterTextSplitter\n")
        archivo.write(f"Coleccion: {COLECCION}\n\n")

        for linea in lineas_del_detalle(resultados):
            archivo.write(linea + "\n")

        archivo.write(
            f"\npromedio -> precision: {precision:.3f}  "
            f"recall: {recall:.3f}\n"
        )


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            'Falta GEMINI_API_KEY. Defínela en tu archivo ".env" y '
            "vuelve a ejecutar."
        )

    vectorstore = cargar_vectorstore(CARPETA_INDICE, COLECCION)
    guardado = vectorstore.get()

    if not guardado["ids"]:
        raise SystemExit(
            "El índice no tiene fragmentos. Corre "
            "python src/indexar_corpus.py --verificar"
        )

    casos = resolver_etiquetas(CASOS, guardado)

    print("La configuración")
    print(f"  carpeta      {os.path.abspath(CARPETA_INDICE)}")
    print(f"  colección    {COLECCION}")
    print(f"  fragmentos   {len(guardado['ids'])}")
    print(f"  tope {TOPE}, solape {SOLAPE}")
    print(f"  preguntas    {len(casos)}")
    sin_respuesta = sum(1 for c in casos if not c["ids_relevantes"])
    print(f"  de ellas sin respuesta en el corpus   {sin_respuesta}")
    print()

    retriever = vectorstore.as_retriever(search_kwargs={"k": K_MAX})
    recuperados = recuperar_todo(retriever, casos)
    print(f"Recuperado. {len(casos)} llamadas, una por pregunta.")
    print()

    resultados, precision, recall = evaluar(recuperados, casos,
                                            K_ELEGIDO)

    print("=" * 68)
    print(f"Resultado con k={K_ELEGIDO}")
    print("=" * 68)
    for linea in lineas_del_detalle(resultados):
        print(linea)
    print()
    print(f"promedio -> precision: {precision:.3f}  "
          f"recall: {recall:.3f}")
    print()

    print("=" * 68)
    print("La curva de k, sobre la misma recuperación")
    print("=" * 68)
    print(f"  {'k':>3}  {'precision':>9}  {'recall':>7}  {'F1':>6}")
    print("  " + "-" * 32)

    curva = []
    for k in range(1, K_MAX + 1):
        _, p, r = evaluar(recuperados, casos, k)
        curva.append((k, p, r, f1(p, r)))
        marca = "  <-- el elegido" if k == K_ELEGIDO else ""
        print(f"  {k:>3}  {p:>9.3f}  {r:>7.3f}  {f1(p, r):>6.3f}"
              f"{marca}")

    # Dos lecturas de la misma curva, que no siempre coinciden.
    #
    # F1 pesa precisión y recall por igual. En este conjunto hay dos
    # preguntas sin respuesta que le restan precisión a todos los k,
    # de modo que F1 puede premiar un k chico que deja fragmentos
    # afuera.
    #
    # Este proyecto prefiere el recall, y no es una preferencia
    # suelta. La lección dice que el recall bajo es más grave que la
    # precisión baja, porque un fragmento que no llegó no lo
    # compensa ningún prompt. En una consulta laboral eso es una
    # respuesta equivocada sobre dinero que alguien va a cobrar.
    mejor_recall = max(r for _, _, r, _ in curva)
    k_recall = min(k for k, _, r, _ in curva if r == mejor_recall)
    k_f1 = max(curva, key=lambda fila: fila[3])[0]

    print()
    print("  Las dos lecturas de esta curva")
    print()
    print(f"    el recall deja de subir en k={k_recall}, "
          f"en {mejor_recall:.3f}")
    print(f"    F1 llega a su máximo en k={k_f1}")

    if k_recall == k_f1:
        print()
        print("    Coinciden, así que ese es el k.")
    else:
        print()
        print("    No coinciden. Este proyecto se queda con el del")
        print("    recall, porque un fragmento que no llega no lo")
        print("    compensa ningún prompt, y la lección dice que el")
        print("    recall bajo es más grave que la precisión baja.")
    print()

    print("Las preguntas donde el recall quedó en cero")
    fallidas = [
        r["pregunta"] for r in resultados if r["recall"] == 0.0
    ]
    if fallidas:
        for pregunta in fallidas:
            print(f"  {pregunta}")
        print()
        print("  En esas, el fragmento que responde no llegó. Es el")
        print("  fallo que más importa, porque ningún prompt lo")
        print("  puede compensar.")
    else:
        print("  ninguna")

    print()
    escribir_resultados(ARCHIVO_RESULTADOS, resultados, precision,
                        recall, K_ELEGIDO)
    print(f"Resultados guardados en {ARCHIVO_RESULTADOS}")
