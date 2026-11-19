"""Verificación de la generación con la configuración adoptada (Bloque 28).

Qué verifica. La partición por inciso del Bloque 28 cambió qué llega
al modelo, y eso puede arreglar o romper cosas que la evaluación de
la recuperación no mide. Precisión y recall dicen si el fragmento
etiquetado llegó, no si la respuesta quedó bien.

Las dos reglas con alcance. El promedio de los últimos once años es
el artículo 40 bis D y rige solo para la jornada parcial de treinta
horas o menos. El aporte del empleador con su rentabilidad es la
letra b) del inciso 5 del artículo 163 y rige solo para los
trabajadores de casa particular. Con la partición anterior el modelo
presentó las dos como reglas generales, porque el fragmento que las
traía llegaba sin la condición que las limita.

Cómo se comprueba. Se busca en la respuesta la palabra que identifica
cada regla, y si está, se busca también la palabra de su condición.
Una regla nombrada sin su condición es el error que se quiere
detectar.

Ese chequeo tiene un límite que conviene saber. Si el modelo no
nombra la regla, el chequeo se queda callado, y callado no es lo
mismo que correcto. Por eso la respuesta se imprime completa.

Los controles. La consulta de fuera del corpus tiene que recibir la
frase de abstención, que es un criterio del Bloque 26. La pregunta
compuesta y la del acoso tienen que seguir respondiendo, y cada una
se arregló por un camino distinto.

La compuesta la arregló la plantilla de tres salidas. Con dos salidas
se abstenía entera, cuatro corridas de cuatro.

La del acoso la arregló el tope, y eso se pudo separar. Una corrida
de registro_rag.py la mostró con diez tokens de salida, que es el
largo de la frase de abstención. Con la plantilla nueva y el índice
del tope 1500 seguía dando diez. Con el tope de 1300 pasó a
responder. La tabla de los tres estados está en la sección 14 del
docs/limites_bloque28.md, y el mecanismo es el ruido por fragmento,
que esa misma sección había propuesto antes de poder medirlo.

Por eso las dos están en esta lista, y por eso la del acoso es la que
primero se rompe si la partición vuelve a cambiar.

La compuesta se agregó al elegir el tope de 1300. Hasta entonces el
chequeo de alcance nunca la había tocado, porque probaba la consulta
del cálculo, que está escrita de otra manera. Al correrla salió que
la regla del artículo 40 bis D llega sin su condición en una corrida
de tres, con esta plantilla y con la anterior. Es un error
preexistente y de generación, no de recuperación, porque la
condición sí llega al contexto. Queda anotado como pendiente en la
sección 18 del docs/limites_bloque28.md.

De ahí sale una advertencia sobre este mismo archivo. Lo que no está
en CASOS no se revisa, y durante dos bloques esta consulta no estuvo.

Apunta a la colección de producción, no a una de prueba, porque lo
que hay que verificar es lo que se entrega.

Qué cuesta. Cinco generaciones y sus embeddings.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from indexar_corpus import CARPETA_INDICE, COLECCION, SOLAPE, TOPE
from recuperacion import (
    RECUPERADOS,
    SIN_CONTEXTO,
    fuentes_citadas,
    responder_con_citas,
)

load_dotenv()

# Cada regla con la palabra que la identifica en una respuesta y la
# palabra de la condición que la limita. Si la respuesta nombra la
# regla y no la condición, la está presentando como general.
REGLAS = (
    ("el promedio de los últimos once años",
     ("promedio de las remuneraciones", "promedio de la"),
     ("parcial", "treinta horas")),
    ("el aporte del empleador con su rentabilidad",
     ("aporte",),
     ("casa particular",)),
)

# Cada caso con su pregunta y si tiene que abstenerse o responder.
CASOS = (
    ("la del calculo, la que traia los dos errores",
     "¿cómo se calcula la indemnización por años de servicio?",
     False),
    ("la del acoso, que mostro diez tokens de salida",
     "tengo un conflicto con una compañera que me hostiga y no "
     "tengo pruebas, ¿pueden despedirme por eso?",
     False),
    ("control, fuera del corpus",
     "¿cuál es la receta del pastel de choclo?",
     True),
    ("la que sigue pendiente, la #11",
     "me despidieron por necesidades de la empresa, "
     "¿a qué tengo derecho?",
     False),
    ("la compuesta, donde la regla se suelta",
     "¿en qué consiste la indemnización por años de servicio y "
     "qué incluye?",
     False),
)

ANCHO = 64


def envolver(texto, ancho=ANCHO):
    """Parte el texto en líneas cortas para que se lea en pantalla."""
    lineas, actual = [], ""
    for palabra in texto.split():
        if actual and len(actual) + 1 + len(palabra) > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        lineas.append(actual)
    return lineas


def revisar_alcance(respuesta):
    """Dice qué reglas nombró la respuesta y si trajo su condición.

    Devuelve las que quedaron sin condición, que son las que estarían
    presentadas como si valieran para cualquier trabajador.
    """
    bajo = respuesta.lower()
    hallazgos, sueltas = [], []
    for nombre, marcas, condiciones in REGLAS:
        if not any(m.lower() in bajo for m in marcas):
            continue
        con = [c for c in condiciones if c.lower() in bajo]
        hallazgos.append((nombre, con))
        if not con:
            sueltas.append(nombre)
    return hallazgos, sueltas


def correr(modelo, etiqueta, pregunta, debe_abstenerse):
    """Hace la consulta contra producción y la informa."""
    print("\n" + "=" * 70)
    print(f"  {etiqueta.upper()}")
    print("=" * 70)
    for linea in envolver(pregunta):
        print(f"  {linea}")

    _, respuesta, citas = responder_con_citas(modelo, pregunta)
    se_abstuvo = SIN_CONTEXTO in respuesta
    citadas = fuentes_citadas(respuesta, citas)

    print(f"\n  {'SE ABSTUVO' if se_abstuvo else 'respondió'}, "
          f"{len(respuesta)} caracteres, {len(citadas)} fuentes citadas")
    for numero, fuente in citadas:
        print(f"      [{numero}]  {fuente}")

    print("\n  La respuesta")
    for linea in envolver(respuesta):
        print(f"      {linea}")

    hallazgos, sueltas = revisar_alcance(respuesta)
    if hallazgos:
        print("\n  Reglas con alcance que nombró")
        for nombre, con in hallazgos:
            estado = (f"con su condicion, {', '.join(con)}" if con
                      else "SIN SU CONDICION")
            print(f"      {nombre}")
            print(f"          {estado}")

    correcto = se_abstuvo == debe_abstenerse
    esperado = "abstenerse" if debe_abstenerse else "responder"
    print(f"\n  esperado {esperado}, {'BIEN' if correcto else 'MAL'}")
    return correcto, sueltas


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY") or not os.getenv("AI_MODEL"):
        raise SystemExit(
            'Falta GEMINI_API_KEY o AI_MODEL en tu archivo ".env".'
        )

    modelo = ChatGoogleGenerativeAI(model=os.getenv("AI_MODEL"))
    print(f"\n  modelo      {os.getenv('AI_MODEL')}")
    print(f"  coleccion   {COLECCION}")
    print(f"  carpeta     {os.path.abspath(CARPETA_INDICE)}")
    print(f"  tope {TOPE}, solape {SOLAPE}, k {RECUPERADOS}")

    bien, sueltas_totales = 0, []
    for etiqueta, pregunta, debe_abstenerse in CASOS:
        correcto, sueltas = correr(
            modelo, etiqueta, pregunta, debe_abstenerse)
        bien += correcto
        sueltas_totales.extend(sueltas)

    print("\n" + "=" * 70)
    print("  QUE SALIO")
    print("=" * 70)
    print(f"\n  casos que se comportaron como se esperaba   "
          f"{bien} de {len(CASOS)}")
    print(f"  reglas nombradas sin su condicion           "
          f"{len(sueltas_totales)}")
    for nombre in sueltas_totales:
        print(f"      {nombre}")
    print()

    if bien == len(CASOS) and not sueltas_totales:
        print("  La configuracion adoptada se comporta como se espera.")
        print("  Ninguna regla con alcance llego sin su condicion, la")
        print("  abstencion funciona donde corresponde, y las preguntas")
        print("  que la plantilla de tres salidas arreglo siguen")
        print("  respondiendo.")
    elif sueltas_totales:
        print("  Hay reglas que llegan sin su condicion. La particion")
        print("  por inciso no las cubre y hay que mirarlas una por una.")
    else:
        print("  Hay casos que no se comportaron como se esperaba. Lee")
        print("  cada respuesta de arriba antes de dar esto por bueno.")
    print()
