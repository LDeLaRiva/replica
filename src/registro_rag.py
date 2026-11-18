"""Registro de latencia y costo del flujo RAG (Bloque 28).

Corre una consulta RAG real midiendo por separado cuánto tarda cada
etapa y cuántos tokens cobró la llamada, y deja una línea por corrida
en un archivo que se pueda comparar más adelante.

Se corre desde la raíz del proyecto con
`python src/registro_rag.py`.

Cuesta una generación por consulta, más el embedding de la pregunta.
Es la única forma honesta de medir latencia y costo, porque los
números simulados no sirven para eso.

Por qué reusa el flujo del Bloque 26 en vez de rearmarlo

El script de la lección crea su propio PROMPT_TEMPLATE, su propia
formatear_contexto, sus embeddings y su Chroma. Copiarlo dejaría dos
plantillas de prompt en el proyecto, y el día que una cambie la otra
seguiría igual sin que nada avise. Lo que se mide tiene que ser el
flujo que el proyecto usa de verdad, no una copia parecida.

Hay además una razón que para este índice es decisiva. El Chroma de
la lección se construye sin nombrar la colección, porque el índice de
su ejemplo quedó en la colección por defecto. Este corpus vive en
corpus_legal_chile, y conectarse sin nombrarla devuelve una colección
vacía sin lanzar ningún error. La consulta correría, mediría tiempos
y guardaría su registro con el contexto en blanco.

construir_prompt de recuperacion.py ya resuelve las dos cosas. Trae
los fragmentos, arma el prompt con la plantilla del proyecto y se
conecta a la colección correcta porque importa sus constantes.

Por qué el modelo se llama directo y no con StrOutputParser

responder_con_citas pasa la respuesta por StrOutputParser, que la
convierte en texto pelado. Los tokens viajan en usage_metadata, que
es un campo del mensaje, y el parser lo descarta. Por eso se llama
a modelo.invoke, que devuelve el mensaje entero.

El texto de la respuesta no se guarda, igual que en el registro de la
lección. Lo que este bloque mide es cuánto tardó y cuánto costó la
consulta, y el contenido de la respuesta es asunto del Bloque 26.

Esto no cambia nada de recuperacion.py. Ese archivo es el entregable
del Bloque 26 y queda tal como está.

Por qué se repite la guarda del índice vacío

La guarda vive en responder_con_citas, no en construir_prompt. Como
se llama a construir_prompt directo, la comprobación se vuelve a
hacer. Un índice vacío no lanza error, devuelve una lista vacía, y
seguir adelante pagaría una generación sobre un contexto en blanco y
guardaría ese registro como si fuera bueno.

Por qué el k se importa y no se escribe

La lección escribe k=3 en su firma. Este archivo importa RECUPERADOS
de recuperacion.py, que hoy vale lo mismo. Escrito a mano quedaría
viejo el día que el k cambie, y entonces la medición de costo diría
un k que la aplicación no usa. Eso ya pasó en el Bloque 27, con el k
escrito en dos archivos a la vez.

La comparación de k=3 contra k=6 que pide la actividad se hace
aparte, abajo, sin tocar el valor del proyecto.

Por qué el modelo entra por parámetro

La misma razón que en recuperacion.py y en cadena_tres_pasos.py.
Creado adentro de la función, no hay forma de correr la lógica con un
modelo falso.

Qué incluye cada etapa medida

embed_y_busqueda cubre la reconexión al índice, el embedding de la
pregunta, la búsqueda y el armado del prompt. Es el mismo corte que
hace la lección, con el armado del texto agregado, que son
microsegundos.

La reconexión al índice entra en esa cuenta, y también el embedding
de la pregunta, que es una llamada por red. Por eso esta etapa no es
comparable con la búsqueda vectorial sola de la lección anterior, que
era local y no salía a ninguna parte.

La primera consulta de una corrida sale más lenta que las siguientes.
Cuánto, y en qué etapa, está medido en docs/limites_bloque28.md.

Las tarifas por token no se escriben en este archivo. Cambian con
el tiempo y
según el modelo, y la propia lección pide no fijarlas de memoria. Lo
que este archivo guarda son los tokens reales de cada llamada, que es
el dato que no se puede reconstruir después.

Por qué el registro guarda el tope y el solape

El registro de la lección guarda el k y no guarda la partición. Con
el k solo no se distingue una corrida de otra cuando la partición
cambió, y este proyecto cambió la suya en el Bloque 28, de
fragmentos de cuatrocientos setenta caracteres a fragmentos de mil
noventa.

La lección advierte que este archivo no debe mezclar corridas sin
poder distinguirlas, porque es para comparar en el futuro. Con el
tope y el solape adentro, cada línea dice con qué configuración se
midió y la comparación se puede hacer años después.
"""

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from indexar_corpus import CARPETA_INDICE, COLECCION, SOLAPE, TOPE
from recuperacion import RECUPERADOS, construir_prompt

load_dotenv()

# Donde se acumulan las corridas. Va al lado de este archivo y no en
# la carpeta desde donde se ejecute, igual que el resultado del
# Bloque 27, para que el registro no se parta en dos según de dónde
# se haya corrido el script.
ARCHIVO_REGISTRO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "registros_latencia_costo.jsonl",
)

# Los dos valores que la actividad pide comparar para mostrar que el k
# mueve el costo. No reemplazan al k del proyecto, que sigue siendo
# RECUPERADOS.
K_BAJO = 3
K_ALTO = 6


@contextmanager
def medir(tiempos, etapa):
    """Guarda en el diccionario cuánto tardó el bloque que envuelve.

    Usa time.perf_counter y no time.time, porque el segundo se mueve
    con los ajustes del reloj del sistema y no sirve para medir
    duraciones cortas.
    """
    inicio = time.perf_counter()
    yield
    tiempos[etapa] = time.perf_counter() - inicio


def registrar_consulta(modelo, pregunta, carpeta=CARPETA_INDICE,
                       coleccion=COLECCION, k=RECUPERADOS):
    """Corre una consulta RAG real y devuelve su registro.

    Mide las dos etapas por separado y saca los tokens de la
    respuesta del modelo, que son los reales de esa llamada y no una
    estimación por caracteres.

    No escribe nada en disco. Devolver el registro y dejar que quien
    llama decida si lo guarda permite correr una consulta de prueba
    sin ensuciar el archivo que después se commitea.

    Args:
        modelo: el modelo de lenguaje ya creado. Entra por parámetro
            para que se pueda correr con uno falso.
    """
    tiempos = {}

    with medir(tiempos, "embed_y_busqueda"):
        prompt, citas = construir_prompt(pregunta, carpeta, coleccion, k)

    if not citas:
        raise ValueError(
            "La recuperación no trajo ningún fragmento y no se llamó "
            "al modelo. El índice está vacío o la colección no es la "
            "que se esperaba. Corre "
            "python src/indexar_corpus.py --verificar"
        )

    with medir(tiempos, "generacion"):
        respuesta = modelo.invoke(prompt)

    uso = getattr(respuesta, "usage_metadata", None)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pregunta": pregunta,
        "k": k,
        "tope": TOPE,
        "solape": SOLAPE,
        "tiempos_ms": {
            etapa: round(segundos * 1000, 2)
            for etapa, segundos in tiempos.items()
        },
        "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
        "tokens": dict(uso) if uso else None,
    }


def guardar(registros, ruta=ARCHIVO_REGISTRO):
    """Agrega los registros al archivo, una línea cada uno.

    Abre en modo de agregar y no de escribir, para que las corridas
    nuevas no pisen las anteriores. Una línea por corrida es lo que
    hace que el archivo se pueda leer de a un registro sin parsearlo
    entero.

    Recibe una lista y no un registro suelto a propósito. Escribiendo
    de a uno, una sesión que se cae en la tercera consulta de cinco
    deja las dos primeras guardadas, y la actividad pide que este
    archivo no mezcle corridas sueltas con corridas buenas. Juntando
    la escritura al final, una sesión incompleta no escribe nada y se
    vuelve a correr sin tener que limpiar el archivo a mano.
    """
    with open(ruta, "a", encoding="utf-8") as archivo:
        for registro in registros:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def tres_preguntas(casos):
    """Elige tres preguntas de distinto largo del conjunto del Bloque 27.

    La lección advierte que una sola consulta no es una muestra y pide
    correr preguntas de distinto largo antes de sacar conclusiones
    sobre el costo. El largo es el criterio, así que se elige por
    largo y no a dedo.

    Quedan fuera las preguntas que el corpus no puede responder,
    porque lo que se mide es una consulta completa.

    Corta si no hay al menos tres. Con menos devolvería alguna
    repetida, y la actividad pide tres preguntas distintas.
    """
    con_respuesta = [caso for caso in casos if caso["frases"]]
    if len(con_respuesta) < 3:
        raise ValueError(
            f"Hacen falta al menos tres preguntas con respuesta en el "
            f"corpus y hay {len(con_respuesta)}. La actividad pide tres "
            "distintas."
        )
    ordenadas = sorted(con_respuesta, key=lambda caso: len(caso["pregunta"]))
    medio = len(ordenadas) // 2
    return (
        ordenadas[0]["pregunta"],
        ordenadas[medio]["pregunta"],
        ordenadas[-1]["pregunta"],
    )


def linea_resumen(registro):
    """Una línea corta por registro, para mirar la corrida de un vistazo."""
    tokens = registro["tokens"]
    entrada = tokens["input_tokens"] if tokens else None
    return (
        f"  k={registro['k']}  entrada={entrada}  "
        f"total={registro['tiempo_total_ms']} ms  "
        f"{registro['pregunta'][:40]}"
    )


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

    # El conjunto de preguntas se importa aquí y no arriba a
    # propósito. leer_registros.py importa la ruta del archivo desde
    # este módulo, y arriba arrastraría también todo el evaluador del
    # Bloque 27 para nada.
    from evaluacion_recuperacion import CASOS

    # La credencial no se pasa por parámetro. La librería la busca
    # sola en GOOGLE_API_KEY y, como respaldo, en GEMINI_API_KEY.
    modelo = ChatGoogleGenerativeAI(model=os.getenv("AI_MODEL"))

    corta, media, larga = tres_preguntas(CASOS)

    print("La configuración")
    print(f"  carpeta      {os.path.abspath(CARPETA_INDICE)}")
    print(f"  colección    {COLECCION}")
    print(f"  k del proyecto   {RECUPERADOS}")
    print(f"  registro     {ARCHIVO_REGISTRO}")
    print()

    # Las corridas que pide la actividad. Tres preguntas distintas
    # con el k del proyecto, y después la del medio con los dos k que
    # la actividad pide comparar.
    #
    # Si alguno de esos dos k coincide con el del proyecto, esa
    # corrida ya está hecha y no se repite. Repetirla pagaría una
    # generación para escribir dos veces la misma línea, y la lección
    # pide que cada línea de este archivo aporte algo.
    corridas = [
        (corta, RECUPERADOS),
        (media, RECUPERADOS),
        (larga, RECUPERADOS),
    ]
    for k in (K_BAJO, K_ALTO):
        if (media, k) not in corridas:
            corridas.append((media, k))
    corridas = tuple(corridas)

    print("=" * 68)
    print("Corriendo")
    print("=" * 68)

    # Nada se escribe hasta que todas terminen. Si alguna falla,
    # el archivo queda como estaba y no hay que limpiarlo a mano.
    registros = []
    for pregunta, k in corridas:
        registro = registrar_consulta(modelo, pregunta, k=k)
        registros.append(registro)
        print(linea_resumen(registro))

    guardar(registros)
    print()

    print("=" * 68)
    print("Las comprobaciones de la actividad")
    print("=" * 68)
    print()

    # La primera. Una línea nueva por cada corrida.
    print(f"  se guardaron {len(registros)} corridas, una línea cada una")

    # La segunda. La misma pregunta con dos k, y los tokens de entrada
    # tienen que haber crecido. Se buscan por su k y no por su
    # posición, para que agregar otra corrida arriba no rompa esto.
    por_k = {
        registro["k"]: registro
        for registro in registros
        if registro["pregunta"] == media
    }
    bajo, alto = por_k.get(K_BAJO), por_k.get(K_ALTO)

    if not bajo or not alto or not bajo["tokens"] or not alto["tokens"]:
        print(f"  no se pudo comparar k={K_BAJO} contra k={K_ALTO}, "
              "falta alguna corrida o sus tokens")
    else:
        entrada_baja = bajo["tokens"]["input_tokens"]
        entrada_alta = alto["tokens"]["input_tokens"]
        print(f"  k={K_BAJO} dio {entrada_baja} tokens de entrada, "
              f"k={K_ALTO} dio {entrada_alta}")
        if entrada_alta > entrada_baja:
            print(f"  crecieron en {entrada_alta - entrada_baja}, "
                  "subir el k sube el costo")
        else:
            print("  NO crecieron, que es lo contrario de lo esperado.")
            print("  Revisa que las dos corridas sean la misma pregunta")

    # La tercera. La generación tiene que ser la etapa más lenta en
    # todas las corridas, no solo en promedio.
    siempre_mas_lenta = all(
        registro["tiempos_ms"]["generacion"]
        > registro["tiempos_ms"]["embed_y_busqueda"]
        for registro in registros
    )
    if siempre_mas_lenta:
        print("  la generación fue la etapa más lenta en las "
              f"{len(registros)} corridas")
    else:
        print("  la generación NO fue la más lenta en todas. Mira el")
        print("  detalle de abajo, porque la reconexión al índice de la")
        print("  primera corrida puede explicarlo")

    print()
    print("=" * 68)
    print("El detalle por etapa")
    print("=" * 68)
    print()
    print(f"  {'k':>3}  {'embed+busq':>11}  {'generacion':>11}  "
          f"{'total':>9}  pregunta")
    print("  " + "-" * 64)
    for registro in registros:
        tiempos = registro["tiempos_ms"]
        print(f"  {registro['k']:>3}  {tiempos['embed_y_busqueda']:>11.2f}  "
              f"{tiempos['generacion']:>11.2f}  "
              f"{registro['tiempo_total_ms']:>9.2f}  "
              f"{registro['pregunta'][:30]}")
    print()
    print(f"Registro guardado en {ARCHIVO_REGISTRO}")
