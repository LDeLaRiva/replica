"""Comparación de topes de partición, por recuperación y por costo.

Qué responde. La sección 11 del `limites_bloque28.md` fija un piso
para el tope, que no quede por debajo de la unidad estructural más
larga del corpus, 1057 caracteres. Medido, ese piso se cumple desde
1057 mismo y no elige ningún valor. Por encima del piso ninguna
unidad se parte, y lo único que cambia es cuántas unidades enteras se
empaquetan en un fragmento.

El tope de 1500 se había tomado de una grilla de cuatro, 700, 1000,
1500 y 2000, por ser el menor con cero fragmentos a media unidad.
Entre el piso y 1500 no se había medido nada, y el cero empieza en
1057.

Qué mide. Las dos cosas que el Bloque 28 midió, recuperación y costo.
Un tope menor da fragmentos menores, y fragmentos menores significan
menos tokens de entrada por consulta. Mirar solo el recall dejaría
fuera la mitad de la pregunta.

Por qué la precisión no se puede comparar entre topes. La cantidad de
fragmentos relevantes de una pregunta depende de cómo quedó partido
el corpus. La pregunta 3 tiene dos frases etiquetadas que con tope
1500 caen en un mismo fragmento y con 1100 caen en dos. Esa pregunta
pasa de un relevante a dos sin que la búsqueda haya mejorado, y la
precisión sube sola. Por eso este script imprime cuántos relevantes
tiene cada tope y la comparación se lee por recall.

De dónde salen las tarifas. Están despejadas de las cuatro filas
medidas de la sección 5 del `limites_bloque28.md`, y reproducen las
cuatro exactas. Son las de ejemplo de la lección 13 y no las reales
de Google, así que sirven para comparar y no para presupuestar.

Qué no toca. La colección de producción no se abre ni para leer. Cada
tope va a su propia colección de prueba, igual que hizo
`probar_linea_contexto.py` en el Bloque 27.

El límite del plan gratis es de cien embeddings por minuto. Cada tope
gasta sus fragmentos más dieciséis preguntas, así que entre un tope y
el siguiente se espera, y ningún bloque pasa de cien.

Banderas. Con `--usar-indice` salta la indexación y mide sobre las
colecciones de prueba que ya estén en disco, sin esperas.

Qué se decidió con esto. El tope quedó en 1300 y el solape en 234. De
este script salen dos de las cuatro condiciones de esa decisión, el
recall plano por encima del piso, 0.857 en los cuatro topes de la
grilla, y el costo de la entrada, que baja 0.87x, 0.91x y 1.00x sobre
los topes 1100, 1250 y 1500. La justificación completa está en la
sección 11 del `limites_bloque28.md`.

Esos tres factores no se comparan con los tokens reales del registro.
Este script estima la entrada a partir de los caracteres del prompt
sobre las catorce preguntas que el corpus responde, y el registro
mide tokens reales sobre tres. Las dos mediciones apuntan en la misma
dirección y no son el mismo número.

Por qué queda en el repositorio. Sostiene una decisión que está en el
código entregado, y el repositorio guarda lo que permite volver a
verificar una decisión entregada. Vuelve a correrse cuando el corpus
cambie, que es el procedimiento escrito en la cabecera de
`indexar_corpus.py`.

Se corre desde la raíz del proyecto con
`python src/comparar_topes.py`.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from indexar_corpus import (
    cargar_vectorstore,
    fragmentar,
    hay_algo_en_disco,
    ids_de,
    preparar_documentos,
)
from recuperacion import PROMPT_TEMPLATE, formatear_contexto
from evaluacion_recuperacion import (
    CASOS,
    K_MAX,
    f1,
    precision_at_k,
    promediar,
    recall_at_k,
    resolver_etiquetas,
)

load_dotenv()

CARPETA_PRUEBA = "vectorstore_topes/"

#   1100   un tope por encima del piso y por debajo de 1293, donde
#          el artículo 172 todavía no cabe entero
#   1250   otro del mismo caso, para ver si el recall se mueve
#          entre dos topes de ese rango
#   1300   el adoptado, el primero por encima de 1293
#   1500   el anterior
#
# El 1250 estuvo en esta grilla por una razón que se descartó, que
# los 250 tokens del trabajo peruano a cinco caracteres por token
# dan 1250. La sección 17 del docs/limites_bloque28.md explica por
# qué esos 250 tokens no se comparan con este tope, son otro
# tokenizador y cumplen otro papel. El valor se queda en la grilla
# porque la medición ya está hecha y sirve como punto intermedio,
# pero no respalda nada.
TOPES = (1100, 1250, 1300, 1500)

PROPORCION_SOLAPE = 0.18
K_PROYECTO = 3

# El límite del plan gratis son cien embeddings por minuto. Se espera
# entre un tope y el siguiente para no agotarlo.
ESPERA_ENTRE_TOPES = 65

# Despejadas de la sección 5 del documento del Bloque 28. Reproducen
# las cuatro filas medidas con diferencia menor a una millonésima.
COSTO_ENTRADA = 1e-7
COSTO_SALIDA = 4e-7

# Una aproximación para pasar de caracteres de prompt a tokens de
# entrada. Sale de que en el tope 700 cada fragmento extra costaba
# unos ciento cuarenta tokens, pero esa cuenta usa el tope y no el
# largo real del fragmento, que ahí promediaba 472 caracteres, así
# que la razón verdadera de ese caso está más cerca de 3.4 que de 5.
#
# Lo que esto afecta y lo que no. El costo absoluto que imprime este
# script es una estimación y no un valor medido, y con esta razón
# queda por debajo de los tokens reales. Los tokens reales de cada
# llamada están en src/registros_latencia_costo.jsonl. Lo que sí
# sirve es la comparación entre topes, porque la misma razón se
# aplica a todas las filas y el cociente no cambia.
CARACTERES_POR_TOKEN = 5

# Los tokens de salida no se miden aquí, porque medirlos costaría una
# generación por pregunta y por tope. Se usa el valor medido en la
# sección 5, y se usa igual para todas las filas, de modo que la
# comparación entre topes no depende de él.
#
# Lo medido después, en la sección 5, matiza esto. El efecto del tope
# sobre los tokens de salida cambia de signo según la pregunta y no se
# distingue de la variación propia del modelo, así que dejarlo fijo es
# razonable. Lo que sí mueve la salida es la plantilla del prompt, que
# la acortó entre un veintidós y un cuarenta y cinco por ciento, y eso
# no lo captura este script.
SALIDA_MEDIDA = 262


def nombre_coleccion(tope):
    """Una colección por tope, para que no se pisen entre corridas."""
    return f"topes_{tope}"


def preparar(tope):
    """Arma los fragmentos de un tope, sin indexar ni gastar nada."""
    textos, metadatos = preparar_documentos()
    solape = int(tope * PROPORCION_SOLAPE)
    fragmentos = fragmentar(textos, metadatos, tope, solape)
    return fragmentos, ids_de(fragmentos), solape


def indexar(tope, fragmentos, ids):
    """Indexa ese tope en su colección de prueba. Gasta API."""
    almacen = cargar_vectorstore(CARPETA_PRUEBA, nombre_coleccion(tope))
    almacen.add_texts(
        texts=[f.page_content for f in fragmentos],
        metadatas=[f.metadata for f in fragmentos],
        ids=ids,
    )
    return almacen


def guardado_de(almacen):
    """Lo que hay en la colección, en la forma que espera el evaluador."""
    datos = almacen.get()
    return {
        "ids": datos["ids"],
        "documents": datos["documents"],
        "metadatas": datos["metadatas"],
    }


def revisar(almacen, fragmentos, ids):
    """Guardas antes de medir. Devuelve el motivo o None si pasa.

    Un número que sale de una colección que no es la que se armó no
    mide el tope, mide otra cosa. El Bloque 27 ya tuvo una corrida
    así y por eso estas guardas existen.
    """
    datos = almacen.get()
    en_disco = dict(zip(datos["ids"], datos["documents"]))

    if len(en_disco) != len(ids):
        return (f"la coleccion tiene {len(en_disco)} fragmentos y "
                f"este tope arma {len(ids)}")

    distintos = [
        ident for ident, fragmento in zip(ids, fragmentos)
        if en_disco.get(ident) != fragmento.page_content
    ]
    if distintos:
        return f"hay {len(distintos)} textos que no calzan con los armados"

    return None


def recuperar(almacen, casos_resueltos):
    """Trae K_MAX por pregunta y devuelve los documentos enteros.

    Devuelve los documentos y no solo sus ids, porque con el texto se
    puede armar el prompt real y medir cuánto pesa, que es la mitad
    de esta comparación.
    """
    retriever = almacen.as_retriever(search_kwargs={"k": K_MAX})
    return [retriever.invoke(caso["pregunta"]) for caso in casos_resueltos]


def curva_de(traidos, casos_resueltos):
    """Precisión, recall y F1 para cada k, sobre la misma recuperación."""
    curva = []
    for k in range(1, K_MAX + 1):
        precision = promediar([
            precision_at_k([d.id for d in docs[:k]],
                           caso["ids_relevantes"])
            for docs, caso in zip(traidos, casos_resueltos)
        ])
        recall = promediar([
            recall_at_k([d.id for d in docs[:k]], caso["ids_relevantes"])
            for docs, caso in zip(traidos, casos_resueltos)
        ])
        curva.append((k, precision, recall, f1(precision, recall)))
    return curva


def peso_del_prompt(traidos, casos_resueltos, k):
    """Arma el prompt real de cada pregunta y devuelve cuánto pesa.

    Usa la plantilla y el formateador del proyecto, no una cuenta
    aproximada, de modo que lo que se mide es el prompt que de verdad
    viajaría al modelo con ese tope.

    Quedan fuera las preguntas que el corpus no responde, porque el
    costo que interesa es el de una consulta que se contesta.
    """
    largos = []
    for docs, caso in zip(traidos, casos_resueltos):
        if not caso["ids_relevantes"]:
            continue
        contexto, _ = formatear_contexto(docs[:k])
        prompt = PROMPT_TEMPLATE.format(contexto=contexto,
                                        pregunta=caso["pregunta"])
        largos.append(len(prompt))
    return largos


def costo_de(caracteres):
    """Tokens de entrada y costo por consulta, con la salida medida."""
    entrada = caracteres / CARACTERES_POR_TOKEN
    costo = entrada * COSTO_ENTRADA + SALIDA_MEDIDA * COSTO_SALIDA
    return entrada, costo


def fallidas_de(traidos, casos_resueltos, k):
    """Las preguntas que no alcanzan recall 1.00 con ese k."""
    salida = []
    for numero, (docs, caso) in enumerate(
            zip(traidos, casos_resueltos), start=1):
        valor = recall_at_k([d.id for d in docs[:k]],
                            caso["ids_relevantes"])
        if valor is not None and valor < 1.0:
            salida.append((numero, valor, caso["pregunta"]))
    return salida


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            'Falta GEMINI_API_KEY. Defínela en tu archivo ".env" y '
            "vuelve a ejecutar."
        )

    usar_indice = "--usar-indice" in sys.argv

    print("\n  La comparacion")
    print(f"    topes          {', '.join(str(t) for t in TOPES)}")
    print(f"    k              {K_PROYECTO}")
    print(f"    carpeta        {os.path.abspath(CARPETA_PRUEBA)}")
    print("    produccion     no se toca")
    if not usar_indice:
        print(f"    espera         {ESPERA_ENTRE_TOPES} s entre topes, "
              "por el limite de cien por minuto")

    if hay_algo_en_disco(CARPETA_PRUEBA) and not usar_indice:
        raise SystemExit(
            f"\n  Ya hay algo en {CARPETA_PRUEBA}.\n"
            "  Corre con --usar-indice para medir sobre lo que ya "
            "esta,\n  o borra la carpeta si quieres indexar de nuevo."
        )

    resumen, detalle = [], {}

    for numero_tope, tope in enumerate(TOPES):
        if numero_tope and not usar_indice:
            print(f"\n  esperando {ESPERA_ENTRE_TOPES} s")
            time.sleep(ESPERA_ENTRE_TOPES)

        fragmentos, ids, solape = preparar(tope)
        print("\n" + "=" * 70)
        print(f"  TOPE {tope}, solape {solape}, {len(fragmentos)} "
              "fragmentos")
        print("=" * 70)

        if usar_indice:
            almacen = cargar_vectorstore(CARPETA_PRUEBA,
                                         nombre_coleccion(tope))
            print("\n  usando la coleccion que ya esta en disco")
        else:
            print(f"\n  indexando, {len(fragmentos)} llamadas")
            almacen = indexar(tope, fragmentos, ids)

        motivo = revisar(almacen, fragmentos, ids)
        if motivo:
            print(f"\n  PROBLEMA, {motivo}.")
            print("  No se mide este tope.")
            continue

        casos = resolver_etiquetas(CASOS, guardado_de(almacen))
        sin_respuesta = len([c for c in casos if not c["ids_relevantes"]])
        relevantes = sum(len(c["ids_relevantes"]) for c in casos)
        if sin_respuesta != 2:
            print(f"\n  PROBLEMA, quedaron {sin_respuesta} preguntas sin "
                  "respuesta y tienen que ser dos.")
            continue

        print(f"  guardas pasadas, {len(casos)} preguntas, "
              f"{sin_respuesta} sin respuesta")
        print(f"  ids relevantes en esta particion   {relevantes}")
        print(f"  recuperando, {len(casos)} llamadas")

        traidos = recuperar(almacen, casos)
        curva = curva_de(traidos, casos)
        largos = peso_del_prompt(traidos, casos, K_PROYECTO)
        medio = sum(largos) // len(largos)
        entrada, costo = costo_de(medio)

        fila = curva[K_PROYECTO - 1]
        resumen.append((tope, len(fragmentos), relevantes, fila[1],
                        fila[2], medio, entrada, costo))
        detalle[tope] = (curva, fallidas_de(traidos, casos, K_PROYECTO))

    if not resumen:
        raise SystemExit("\n  No se midio ningun tope.\n")

    print("\n" + "=" * 70)
    print(f"  RECUPERACION EN K={K_PROYECTO}")
    print("=" * 70)
    print("\n  La precision no se compara entre topes, porque la cantidad")
    print("  de relevantes cambia con la particion. Se lee el recall.\n")
    print(f"  {'tope':>6}{'frag':>6}{'relev':>7}{'precision':>11}"
          f"{'recall':>9}")
    print("  " + "-" * 39)
    for tope, cuantos, relev, precision, recall, _, _, _ in resumen:
        print(f"  {tope:>6}{cuantos:>6}{relev:>7}{precision:>11.3f}"
              f"{recall:>9.3f}")

    print("\n" + "=" * 70)
    print(f"  COSTO POR CONSULTA EN K={K_PROYECTO}")
    print("=" * 70)
    print("\n  Prompt real armado con la plantilla del proyecto, sobre")
    print("  las catorce preguntas que el corpus responde.\n")
    base = resumen[-1]
    print(f"  {'tope':>6}{'prompt':>9}{'entrada':>9}{'costo':>11}"
          f"{'vs ultimo':>11}")
    print("  " + "-" * 46)
    for tope, _, _, _, _, medio, entrada, costo in resumen:
        relativo = costo / base[7]
        print(f"  {tope:>6}{medio:>9}{entrada:>9.0f}{costo:>11.6f}"
              f"{relativo:>10.2f}x")

    print("\n" + "=" * 70)
    print("  LA CURVA DE K DE CADA UNO")
    print("=" * 70)
    for tope in TOPES:
        if tope not in detalle:
            continue
        curva, fallidas = detalle[tope]
        print(f"\n  tope {tope}")
        print(f"    {'k':>3}{'precision':>12}{'recall':>9}{'F1':>8}")
        for k, precision, recall, medida in curva:
            marca = "  <--" if k == K_PROYECTO else ""
            print(f"    {k:>3}{precision:>12.3f}{recall:>9.3f}"
                  f"{medida:>8.3f}{marca}")
        if fallidas:
            print(f"    las que no llegan a 1.00 con k={K_PROYECTO}")
            for n, valor, pregunta in fallidas:
                print(f"      #{n:<3} {valor:.2f}  {pregunta[:44]}")
        else:
            print("    todas las que tienen respuesta llegan a 1.00")
    print()
