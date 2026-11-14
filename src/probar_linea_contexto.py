"""Prueba de la linea de contexto en una coleccion aparte (Bloque 27).

Que se prueba. La mayoria de los fragmentos no nombra a su propio articulo,
porque el rotulo vive en su propia linea y el tope los separa de ella. Este
script cuenta cuantos son, les pega arriba una linea con el rotulo y la
primera frase del contenido, las dos copiadas del corpus, y mide si la
recuperacion mejora.

Por que la linea no la redacta nadie. Si la escribiera una persona
resumiendo el articulo, nadie podria comprobarla sin leer el articulo
completo. Copiada del corpus, comprobarla es una busqueda de texto, y el
script la hace con las once de una vez.

Como no se contamina la medicion. Pegar la primera frase arriba de todos
los fragmentos de un articulo hace que una frase que antes resolvia a un
fragmento resuelva a varios, y el recall subiria sin que la busqueda
mejorara. Por eso las etiquetas se resuelven contra los fragmentos
originales, sin linea, y quedan fijas. Lo que se compara despues es solo
la recuperacion.

El conteo de fragmentos sin identificar compara sin tildes, porque el
articulo 66 escribe su rotulo como Articulo con tilde y los otros diez
como Art. Una comparacion literal lo contaba de menos.

Que no se toca. La coleccion de produccion no se abre ni para leer. Todo
va a una carpeta y una coleccion de prueba, declaradas abajo.

Guardas antes de medir. Una corrida anterior dio 0.000 en las tres medidas
porque resolver_etiquetas devuelve los casos con sus campos, no listas de
ids, y se estaban comparando ids de fragmentos contra nombres de campo. Un
cero exacto en las dieciseis preguntas no es un resultado, es una
comparacion mal armada. Por eso ahora, antes de calcular nada, se revisa
que los ids recuperados traigan valor, que existan en la coleccion, que el
caso resuelto calce con su pregunta, que los textos guardados en disco sean
los mismos que arma esta corrida, y que haya cruce entre lo recuperado y lo
etiquetado. Si alguna guarda falla, el script se detiene en vez de imprimir
un numero que no mide nada.

Banderas. Con --solo-revisar hace la fase 1 nada mas, que arma las lineas y
resuelve las etiquetas, sin consumir API. Con --usar-indice salta la
indexacion y usa la coleccion de prueba que ya esta en disco.

Las observaciones de la corrida van en docs/limites_bloque27.md.
"""

import inspect
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indexar_corpus import (
    ETIQUETA,
    SOLAPE,
    TOPE,
    cargar_vectorstore,
    fragmentar,
    hay_algo_en_disco,
    ids_de,
    preparar_documentos,
)
from evaluacion_recuperacion import CASOS, K_ELEGIDO, K_MAX, resolver_etiquetas

CARPETA_PRUEBA = "vectorstore_pruebas/"
COLECCION_PRUEBA = "corpus_con_linea"

CORTE = re.compile(r"(?<=\.)\s+(?=[A-ZÁÉÍÓÚÑ])")
MARCADOR = re.compile(r"\[\s*\d+\s*\]")
CORCHETE = re.compile(r"\[\s*\d")
ESPACIOS = re.compile(r"\s+")
SOBRA = " .-:;\n\t"
CAPA = 180
ANCHO = 62
CLAVES_IDS = ("ids_relevantes", "relevantes", "ids")
CLAVES_PREGUNTA = ("pregunta", "consulta", "texto")

# Numeros de la corrida sin linea, tomados de resultados_evaluacion.txt.
BASE_PRECISION = 0.203
BASE_RECALL = 0.821
BASE_F1 = 0.326


def normalizar(texto):
    """Junta los espacios para comparar sin que importe el salto de linea."""
    return ESPACIOS.sub(" ", texto).strip()


def sin_tildes(texto):
    """Quita las tildes, para que Articulo y articulo cuenten igual."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(
        letra for letra in descompuesto
        if unicodedata.category(letra) != "Mn"
    )


def se_nombra(texto, etiqueta):
    """Dice si el fragmento menciona a su propio articulo en el texto."""
    plano = sin_tildes(normalizar(texto)).lower()
    rotulo = sin_tildes(str(etiqueta)).lower()
    return f"art. {rotulo}" in plano or f"articulo {rotulo}" in plano


def recortar(frase, tope=CAPA):
    """Corta la frase en el tope sin partir una palabra. Sigue siendo copia."""
    if len(frase) <= tope:
        return frase
    return frase[:tope].rsplit(" ", 1)[0].rstrip(SOBRA)


def partes_de(texto):
    """Devuelve el rotulo y la primera frase del contenido, los dos copiados."""
    limpio = MARCADOR.sub("", texto.strip()).strip()
    encontrada = ETIQUETA.search(limpio)
    if not encontrada:
        return "", ""
    rotulo = limpio[encontrada.start():encontrada.end()].strip()
    resto = limpio[encontrada.end():].lstrip(SOBRA).strip()
    return rotulo, recortar(CORTE.split(resto, maxsplit=1)[0].strip())


def es_copia(parte, texto):
    """Confirma que la parte salio del articulo y no de otro lugar."""
    return bool(parte) and normalizar(parte) in normalizar(texto)


def campo(objeto, claves, nombre):
    """Saca un campo del caso, sea dict o sea objeto con atributos."""
    if isinstance(objeto, dict):
        for clave in claves:
            if clave in objeto:
                return objeto[clave]
        raise KeyError(f"no encuentro {nombre} entre {sorted(objeto)}")
    for clave in claves:
        if hasattr(objeto, clave):
            return getattr(objeto, clave)
    raise AttributeError(f"no encuentro {nombre} en {type(objeto).__name__}")


def pregunta_de(caso):
    """Devuelve el texto de la pregunta del caso."""
    return campo(caso, CLAVES_PREGUNTA, "la pregunta")


def ids_relevantes_de(resuelto):
    """Devuelve la lista de ids etiquetados, no el caso que la contiene."""
    if isinstance(resuelto, (list, tuple, set)):
        return list(resuelto)
    return list(campo(resuelto, CLAVES_IDS, "los ids relevantes"))


def envolver(texto, ancho=ANCHO):
    """Parte el texto en lineas cortas para que se lea en pantalla."""
    lineas = []
    actual = ""
    for palabra in texto.split():
        if actual and len(actual) + 1 + len(palabra) > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        lineas.append(actual)
    return lineas


def pares_de(salida):
    """Deja los fragmentos como texto y metadato, sea cual sea su forma."""
    if isinstance(salida, tuple) and len(salida) == 2:
        return list(zip(salida[0], salida[1]))
    pares = []
    for item in salida:
        texto = getattr(item, "page_content", None)
        datos = getattr(item, "metadata", None) or {}
        pares.append((texto if texto is not None else str(item), dict(datos)))
    return pares


def precision_en_k(recuperados, relevantes, k):
    """Formula de la plataforma. Cuantos de los k traidos eran relevantes."""
    traidos = recuperados[:k]
    if not traidos:
        return 0.0
    return len([uno for uno in traidos if uno in relevantes]) / len(traidos)


def recall_en_k(recuperados, relevantes, k):
    """Formula de la plataforma. Cuantos de los relevantes se alcanzaron."""
    if not relevantes:
        return None
    traidos = recuperados[:k]
    return len([uno for uno in relevantes if uno in traidos]) / len(relevantes)


def promediar(valores):
    """Promedia dejando fuera los None, como lo hace la plataforma."""
    utiles = [valor for valor in valores if valor is not None]
    if not utiles:
        return 0.0
    return sum(utiles) / len(utiles)


def f1(precision, recall):
    """Media armonica de las dos medidas."""
    if not precision or not recall:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def armar_lineas(articulos):
    """Arma la linea de cada articulo y revisa que sea copia de su texto."""
    lineas = {}
    fallas = []
    for etiqueta, texto in articulos.items():
        rotulo, frase = partes_de(texto)
        linea = f"{rotulo} {frase}".strip()
        lineas[etiqueta] = linea

        avisos = []
        if not es_copia(rotulo, texto):
            avisos.append("rotulo no copiado")
        if not es_copia(frase, texto):
            avisos.append("frase no copiada")
        if CORCHETE.search(linea):
            avisos.append("CORCHETE")
        if avisos:
            fallas.append((etiqueta, ", ".join(avisos)))

        entera = "entera" if es_copia(linea, texto) else "en dos partes"
        marca = ", ".join(avisos) if avisos else f"copiada, {entera}"
        print(f"\n  art. {etiqueta}   {len(linea)} caracteres   {marca}")
        for renglon in envolver(linea) or ["(vacia)"]:
            print(f"      {renglon}")
    return lineas, fallas


def fase_uno():
    """Arma las lineas, las verifica y resuelve las etiquetas. Sin API."""
    print(f"\n  ETIQUETA               {ETIQUETA.pattern}")
    print(f"  firma de resolver      {inspect.signature(resolver_etiquetas)}")
    print(f"  carpeta de prueba      {CARPETA_PRUEBA}")
    print(f"  coleccion de prueba    {COLECCION_PRUEBA}")

    salida = preparar_documentos()
    textos, metadatos = salida[0], salida[1]
    articulos = {
        str(dato.get("articulo", "?")): texto
        for texto, dato in zip(textos, metadatos)
    }

    print("\n" + "=" * 70)
    print("  LAS LINEAS, ROTULO Y PRIMERA FRASE, LAS DOS COPIADAS")
    print("=" * 70)

    lineas, fallas = armar_lineas(articulos)

    crudos = fragmentar(textos, metadatos, TOPE, SOLAPE)
    originales = pares_de(crudos)
    ids = list(ids_de(crudos))

    nuevos = []
    for (texto, metadato), identificador in zip(originales, ids):
        etiqueta = str(metadato.get("articulo", "?"))
        linea = lineas.get(etiqueta, "")
        nuevos.append((f"{linea}\n\n{texto}".strip(), dict(metadato), identificador))

    print("\n" + "=" * 70)
    print("  LAS ETIQUETAS, RESUELTAS CONTRA LOS FRAGMENTOS SIN LINEA")
    print("=" * 70)

    guardado = {
        "ids": list(ids),
        "documents": [texto for texto, _ in originales],
        "metadatas": [metadato for _, metadato in originales],
    }
    resueltos = resolver_etiquetas(CASOS, guardado)

    primero = resueltos[0]
    print(f"\n  resolver_etiquetas devuelve   {type(primero).__name__}")
    if isinstance(primero, dict):
        print(f"  campos de cada caso           {', '.join(sorted(primero))}")

    etiquetados = [ids_relevantes_de(uno) for uno in resueltos]

    desalineados = []
    for numero, (caso, resuelto) in enumerate(zip(CASOS, resueltos), 1):
        try:
            if normalizar(pregunta_de(caso)) != normalizar(pregunta_de(resuelto)):
                desalineados.append(numero)
        except (KeyError, AttributeError):
            pass

    conocidos = set(ids)
    fuera = sorted({
        uno for lista in etiquetados for uno in lista if uno not in conocidos
    })

    sin_respuesta = len([lista for lista in etiquetados if not lista])
    print(f"\n  Fragmentos          {len(originales)}")
    print(f"  Primeros ids        {', '.join(ids[:4])}")
    print(f"  Preguntas           {len(CASOS)}")
    print(f"  Sin respuesta       {sin_respuesta}")
    print(f"  Con respuesta       {len(etiquetados) - sin_respuesta}")
    print(f"  Ids etiquetados     {sum(len(lista) for lista in etiquetados)}")

    if fallas:
        print("\n  PROBLEMAS EN LAS LINEAS, no seguir.")
        for etiqueta, motivo in fallas:
            print(f"      art. {etiqueta}   {motivo}")
        return None
    if desalineados:
        print("\n  PROBLEMA, los casos resueltos no calzan con CASOS.")
        print(f"      posiciones   {desalineados}")
        return None
    if fuera:
        print("\n  PROBLEMA, hay ids etiquetados que no existen en el corpus.")
        print(f"      {', '.join(fuera[:8])}")
        return None
    if sin_respuesta == 0:
        print("\n  PROBLEMA, ninguna pregunta quedo sin respuesta, y deberian")
        print("  ser dos. Los ids no se estan leyendo del campo correcto.")
        return None

    print("\n" + "=" * 70)
    print("  CUANTOS FRAGMENTOS NO SE IDENTIFICAN SOLOS")
    print("=" * 70)

    huerfanos = [
        identificador
        for (texto, metadato), identificador in zip(originales, ids)
        if not se_nombra(texto, metadato.get("articulo", "?"))
    ]
    print(f"\n  Fragmentos en total                      {len(originales)}")
    print(f"  Fragmentos que nombran a su articulo     {len(originales) - len(huerfanos)}")
    print(f"  Fragmentos que no lo nombran             {len(huerfanos)}")
    if originales:
        print(f"  Proporcion sin identificar               "
              f"{len(huerfanos) / len(originales):.0%}")
    print("\n  Esa es la medida del problema que la linea intenta arreglar.")
    print("  El rotulo del articulo vive en su propia linea, y el tope de")
    print(f"  {TOPE} lo deja solo en el primer fragmento de cada articulo.")

    crecimientos = [
        len(nuevo[0]) / len(viejo[0]) for nuevo, viejo in zip(nuevos, originales)
    ]
    print(f"\n  Los fragmentos crecen entre {min(crecimientos):.0%} y "
          f"{max(crecimientos):.0%} de su largo original.")
    print(f"  Siguen siendo {len(nuevos)}, el corte de {TOPE} no cambio.")
    print("\n  Las guardas pasaron. Se puede medir.")
    return nuevos, etiquetados


def indexar(nuevos):
    """Indexa en la coleccion de prueba. Gasta API. No toca produccion."""
    print("\n" + "=" * 70)
    print("  INDEXANDO EN LA COLECCION DE PRUEBA")
    print("=" * 70)
    if hay_algo_en_disco(CARPETA_PRUEBA):
        print(f"\n  Ya hay algo en {CARPETA_PRUEBA}.")
        print("  Corre con --usar-indice para medir sobre lo que ya esta,")
        print("  o borra la carpeta si quieres indexar de nuevo.")
        return None
    almacen = cargar_vectorstore(CARPETA_PRUEBA, COLECCION_PRUEBA)
    almacen.add_texts(
        texts=[texto for texto, _, _ in nuevos],
        metadatas=[metadato for _, metadato, _ in nuevos],
        ids=[identificador for _, _, identificador in nuevos],
    )
    print(f"\n  Indexados {len(nuevos)} fragmentos en {COLECCION_PRUEBA}.")
    return almacen


def recuperar(almacen, nuevos):
    """Trae K_MAX fragmentos por pregunta y revisa que los ids sirvan."""
    print("\n" + "=" * 70)
    print("  RECUPERANDO")
    print("=" * 70)

    guardado = almacen.get()
    en_disco = set(guardado.get("ids") or [])
    print(f"\n  Fragmentos en la coleccion   {len(en_disco)}")

    esperados = {
        identificador: texto for texto, _, identificador in nuevos
    }
    almacenados = dict(zip(
        guardado.get("ids") or [], guardado.get("documents") or []
    ))
    distintos = sorted(
        identificador for identificador, texto in esperados.items()
        if normalizar(almacenados.get(identificador, "")) != normalizar(texto)
    )
    if len(almacenados) != len(esperados) or distintos:
        print("\n  PROBLEMA, lo indexado no es lo que acaba de armar la fase 1.")
        print(f"      en disco {len(almacenados)}, esperados {len(esperados)}")
        if distintos:
            print(f"      textos distintos   {', '.join(distintos[:6])}")
        print("  Borra la carpeta de prueba y corre sin --usar-indice.")
        return None
    print("  Los 45 textos en disco calzan con los que arma la fase 1.")

    recuperador = almacen.as_retriever(search_kwargs={"k": K_MAX})
    traidos = []
    sin_id = 0
    for caso in CASOS:
        documentos = recuperador.invoke(pregunta_de(caso))
        obtenidos = [documento.id for documento in documentos]
        sin_id += len([uno for uno in obtenidos if not uno])
        traidos.append([uno for uno in obtenidos if uno])

    if sin_id:
        print(f"\n  PROBLEMA, {sin_id} documentos volvieron sin id.")
        print("  Sin id no se puede comparar con las etiquetas.")
        return None

    desconocidos = sorted({
        uno for lista in traidos for uno in lista if uno not in en_disco
    })
    if desconocidos:
        print("\n  PROBLEMA, se recuperaron ids que no estan en la coleccion.")
        print(f"      {', '.join(desconocidos[:8])}")
        return None

    print(f"  Documentos por pregunta      {len(traidos[0])}")
    print("  Todos con id, y todos existen en la coleccion.")
    return traidos


def medir(traidos, etiquetados):
    """Compara contra la base y detalla. Se detiene si no hay cruce."""
    cruce = sum(
        len(set(uno) & set(otros)) for uno, otros in zip(traidos, etiquetados)
    )
    print(f"\n  Ids que se cruzan en el top {K_MAX}     {cruce}")
    if cruce == 0:
        print("\n  ALARMA. Cero cruce en las dieciseis preguntas no es un")
        print("  resultado de busqueda, es una comparacion mal armada.")
        print("  No se calcula nada mas.")
        return

    print("\n" + "=" * 70)
    print(f"  RESULTADO EN K={K_ELEGIDO}")
    print("=" * 70)

    precision = promediar([
        precision_en_k(uno, otros, K_ELEGIDO)
        for uno, otros in zip(traidos, etiquetados)
    ])
    recall = promediar([
        recall_en_k(uno, otros, K_ELEGIDO)
        for uno, otros in zip(traidos, etiquetados)
    ])
    medida = f1(precision, recall)

    print(f"\n  {'':<14}{'precision':>12}{'recall':>10}{'F1':>10}")
    print("  " + "-" * 46)
    print(f"  {'sin linea':<14}{BASE_PRECISION:>12.3f}{BASE_RECALL:>10.3f}"
          f"{BASE_F1:>10.3f}")
    print(f"  {'con linea':<14}{precision:>12.3f}{recall:>10.3f}{medida:>10.3f}")
    print(f"  {'diferencia':<14}{precision - BASE_PRECISION:>+12.3f}"
          f"{recall - BASE_RECALL:>+10.3f}{medida - BASE_F1:>+10.3f}")

    print("\n" + "=" * 70)
    print("  PREGUNTA POR PREGUNTA")
    print("=" * 70)
    print(f"\n  {'#':>3}  {'recall':>9}  pregunta")
    print("  " + "-" * 66)
    for numero, (caso, uno, otros) in enumerate(zip(CASOS, traidos, etiquetados), 1):
        valor = recall_en_k(uno, otros, K_ELEGIDO)
        texto = "sin resp." if valor is None else f"{valor:.2f}"
        print(f"  {numero:>3}  {texto:>9}  {pregunta_de(caso)[:54]}")

    print("\n" + "=" * 70)
    print("  LAS QUE SIGUEN FALLANDO")
    print("=" * 70)
    quedan = False
    for numero, (caso, uno, otros) in enumerate(zip(CASOS, traidos, etiquetados), 1):
        valor = recall_en_k(uno, otros, K_ELEGIDO)
        if valor is None or valor >= 1.0:
            continue
        quedan = True
        perdidos = [otro for otro in otros if otro not in uno[:K_ELEGIDO]]
        print(f"\n  #{numero}  recall {valor:.2f}")
        for renglon in envolver(pregunta_de(caso)):
            print(f"      {renglon}")
        print(f"      no llegaron    {', '.join(perdidos)}")
        posiciones = [
            f"{faltante} en {uno.index(faltante) + 1}"
            for faltante in perdidos if faltante in uno
        ]
        print(f"      donde quedaron {', '.join(posiciones) or 'fuera del top 8'}")
    if not quedan:
        print("\n  Ninguna. Todas las que tienen respuesta llegaron a 1.00.")
    print()


def main():
    salida = fase_uno()
    if salida is None:
        return
    nuevos, etiquetados = salida
    if "--solo-revisar" in sys.argv:
        print("\n  Fase 1 nada mas. Corre sin la bandera para medir.\n")
        return

    if "--usar-indice" in sys.argv:
        almacen = cargar_vectorstore(CARPETA_PRUEBA, COLECCION_PRUEBA)
        print(f"\n  Usando la coleccion {COLECCION_PRUEBA} que ya esta en disco.")
    else:
        almacen = indexar(nuevos)
    if almacen is None:
        return

    traidos = recuperar(almacen, nuevos)
    if traidos is None:
        return
    medir(traidos, etiquetados)


if __name__ == "__main__":
    main()
