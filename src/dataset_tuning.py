"""Dataset de tuning para clasificar consultas laborales (Bloque 29).

Qué hace. Construye y valida un dataset de veintidós ejemplos para
personalizar un modelo con PEFT. Cada ejemplo es una consulta de un
trabajador y la salida exacta que el modelo debe producir para ella,
un JSON con dos claves, la materia y si la respuesta necesita un
cálculo.

Este archivo no entrena nada ni llama a la API. El paso que envía el
trabajo de tuning es condicional en la actividad, dice "si tu cuenta
tiene el tuning habilitado", y esta cuenta no lo tiene.

Por qué esta tarea y no otra. La actividad exige un problema de
comportamiento y descarta los de conocimiento, "si tu candidato es el
modelo no sabe X, es un caso para RAG, no para esta actividad".
Clasificar una consulta es comportamiento, porque el modelo ya
entiende el texto y lo que falta es que entregue siempre la misma
estructura.

Los dos pendientes del Bloque 28 quedaron fuera por eso mismo. El de
la pregunta 11, donde el fragmento no llega, es recuperación y por lo
tanto RAG. El del artículo 40 bis D sí es comportamiento, pero cada
ejemplo tendría que arrastrar su contexto completo y los diez serían
sobre la misma regla, que es el error frecuente de las variaciones
mínimas. Ese caso se fundamenta por escrito en el Bloque 30.

De dónde salen las consultas. Quince vienen del conjunto de
evaluación del Bloque 27, en `evaluacion_recuperacion.py`, escritas
antes y sin pensar en este dataset. Siete son nuevas y se escribieron
para cubrir artículos del corpus que ninguna consulta tocaba, el 177
del finiquito, los incisos del 66 que no son el fuero, la letra c del
160 y las dos cláusulas de cálculo del 163. La del aguinaldo del
Bloque 27 quedó fuera porque su materia no existe en el corpus.

Las cinco materias. Salen del alcance actual del corpus, que son once
artículos alrededor de la terminación del contrato. No se tomaron de
la clasificación de la Dirección del Trabajo, aunque dos coinciden
con ella, terminación de contrato y remuneración. Al ampliar el
corpus corresponde revisarlas contra esa clasificación y volver a
correr `chequear_balance`, porque fusionar o partir categorías cambia
las cuentas. Hoy no tendría sentido, porque la mayoría de sus
materias no tiene ni una consulta.

Por qué `termino_contrato` y no `despido`. Tres de sus siete
consultas no son despidos. La 3 pregunta por el contrato que termina
sin que nadie despida, y la 5 y la 6 por un plazo fijo que se vence.
Etiquetarlas `despido` le enseñaría al modelo algo falso, porque el
modelo copia la etiqueta tal como está escrita.

Por qué `acoso` va aparte y no dentro de `termino_contrato`. El
artículo 160 es, por estructura, un artículo de terminación. La
materia clasifica lo que el trabajador está preguntando, no el
artículo que lo responde, y quien consulta por acoso no está
consultando por el fin de su contrato.

Por qué la clave que clasifica es `materia`. `chequear_balance`
cuenta una sola clave y `necesita_calculo` tiene dos valores, con lo
cual no mostraría desbalance aunque lo hubiera. El balance se mide
sobre `materia`, que tiene cinco.

El balance que da. Siete, cinco, cuatro, tres y tres, con razón
máximo sobre mínimo de 2.3x. El dataset del laboratorio de la
plataforma está en 3.0x y su propia lección lo califica de "nada
extremo todavía", así que este queda por debajo de esa referencia.

Lo que estas comprobaciones no atrapan. Una etiqueta bien formada,
bien balanceada y equivocada pasa los tres pasos sin que nada avise.
Una consulta de feriado etiquetada como despido es una categoría
válida, bien escrita y no desbalancea. Esa verificación es de
criterio y se hizo a mano, consulta por consulta.

Diferencias con el laboratorio de la lección anterior. Aquí
`chequear_balance` recibe la clave por parámetro y `validar_dataset`
no trae claves por defecto, como las define la actividad y no como
las define el laboratorio. Las anotaciones de tipos van en todas las
funciones porque la actividad lo pide de forma explícita.
"""

import json
from collections import Counter

from google.genai import types


CLAVES_ESPERADAS: tuple[str, ...] = ("materia", "necesita_calculo")

CLAVE_QUE_CLASIFICA: str = "materia"


# Las consultas numeradas vienen del conjunto de evaluación del
# Bloque 27 y conservan su texto literal. Las marcadas como nuevas se
# escribieron para este dataset. `necesita_calculo` es verdadero solo
# cuando la consulta entrega datos del caso y la respuesta exige
# correr la herramienta de cálculo, no cuando solo nombra dinero.
ejemplos_raw: list[tuple[str, dict]] = [
    # --- terminación del contrato, siete ---
    ("soy subgerente, ¿el despido es distinto para mi cargo?",
     {"materia": "termino_contrato", "necesita_calculo": False}),
    ("¿en qué casos se termina el contrato sin que nadie despida a "
     "nadie?",
     {"materia": "termino_contrato", "necesita_calculo": False}),
    ("me avisaron el despido con una carta común, no certificada, "
     "¿vale igual?",
     {"materia": "termino_contrato", "necesita_calculo": False}),
    ("mi contrato a plazo fijo venció y no me dijeron nada, ¿se "
     "terminó solo?",
     {"materia": "termino_contrato", "necesita_calculo": False}),
    ("mi contrato a plazo fijo venció y yo seguí yendo a trabajar, "
     "¿qué pasa con mi contrato?",
     {"materia": "termino_contrato", "necesita_calculo": False}),
    ("mi empleador no pagó mis cotizaciones y me despidió, ¿qué pasa "
     "con ese despido?",
     {"materia": "termino_contrato", "necesita_calculo": False}),
    ("creo que me despidieron injustamente, ¿qué puedo hacer?",
     {"materia": "termino_contrato", "necesita_calculo": False}),

    # --- indemnización, cinco ---
    ("¿qué se cuenta como sueldo para calcular la indemnización?",
     {"materia": "indemnizacion", "necesita_calculo": False}),
    ("trabajo veinte horas a la semana, ¿cómo se calcula mi "
     "indemnización?",
     {"materia": "indemnizacion", "necesita_calculo": True}),
    ("me despidieron por necesidades de la empresa, ¿a qué tengo "
     "derecho?",
     {"materia": "indemnizacion", "necesita_calculo": False}),
    ("¿en qué consiste la indemnización por años de servicio y qué "
     "incluye?",
     {"materia": "indemnizacion", "necesita_calculo": False}),
    # nueva, por la fracción superior a seis meses del artículo 163
    ("trabajé 4 años y 8 meses y mi sueldo era de 700 mil pesos, "
     "¿me pagan cuatro años o cinco?",
     {"materia": "indemnizacion", "necesita_calculo": True}),

    # --- finiquito, cuatro ---
    ("¿cómo se calcula mi finiquito?",
     {"materia": "finiquito", "necesita_calculo": True}),
    ("¿hay diferencia en el finiquito si mi contrato es indefinido o "
     "a plazo fijo?",
     {"materia": "finiquito", "necesita_calculo": False}),
    # nueva, por el inciso primero del artículo 177
    ("necesito saber qué tiene que pasar para que yo pueda recibir "
     "mi finiquito en mi trabajo",
     {"materia": "finiquito", "necesita_calculo": False}),
    # nueva, por el tope de trescientos treinta días del artículo 163
    ("si yo trabajo 20 años y mi sueldo es de 1.000.000 de pesos, "
     "¿cuánto sería mi finiquito?",
     {"materia": "finiquito", "necesita_calculo": True}),

    # --- fuero y permisos del artículo 66, tres ---
    ("¿en qué casos tengo fuero laboral?",
     {"materia": "fuero", "necesita_calculo": False}),
    # nueva, por el inciso 3, el permiso corre desde el fallecimiento
    ("¿qué pasaría si yo no tomo mi permiso legal inmediatamente "
     "después del fallecimiento de mi madre?",
     {"materia": "fuero", "necesita_calculo": False}),
    # nueva, por el inciso 4, el fuero en un contrato a plazo fijo
    ("mi contrato a plazo fijo vence en 3 días, pero justo hoy "
     "fallece mi familiar, ¿qué pasaría?",
     {"materia": "fuero", "necesita_calculo": False}),

    # --- acoso, tres ---
    ("tengo un conflicto con una compañera que me hostiga y no tengo "
     "pruebas, ¿pueden despedirme por eso?",
     {"materia": "acoso", "necesita_calculo": False}),
    # nueva, el lado de quien es acusado
    ("me acusan de acoso hacia un compañero, pero yo soy inocente y "
     "él no puede comprobarlo, ¿pueden retirarme igual?",
     {"materia": "acoso", "necesita_calculo": False}),
    # nueva, la letra c del 160, vías de hecho, preguntando por el otro
    ("un compañero de trabajo me pegó y no había nadie más, ¿lo "
     "pueden despedir por eso?",
     {"materia": "acoso", "necesita_calculo": False}),
]


# `ensure_ascii=False` deja pasar las tildes y las eñes. Sin eso el
# modelo aprendería a escribir el código de escape en vez de la
# palabra, y todo el corpus está en español.
examples: list[types.TuningExample] = [
    types.TuningExample(
        text_input=texto,
        output=json.dumps(salida, ensure_ascii=False),
    )
    for texto, salida in ejemplos_raw
]


def chequear_balance(
    ejemplos_raw: list[tuple[str, dict]], clave: str
) -> Counter:
    """Cuenta cuántos ejemplos hay por cada valor de `clave`.

    Mira el conjunto, no el ejemplo. Un dataset con el formato
    perfecto pero desbalanceado entrena un modelo que contesta por
    frecuencia y no por contenido.
    """
    categorias = Counter(salida[clave] for _, salida in ejemplos_raw)
    return categorias


def validar_dataset(
    examples: list[types.TuningExample], claves_esperadas: tuple[str, ...]
) -> list[str]:
    """Devuelve la lista de problemas de formato, vacía si no hay.

    Revisa cada ejemplo por separado. No se detiene en el primero que
    encuentra, para que la lista sirva de una sola pasada.
    """
    problemas: list[str] = []
    vistos: set[str] = set()
    for i, ej in enumerate(examples):
        if not ej.text_input or not ej.text_input.strip():
            problemas.append(f"ejemplo {i}: text_input vacio")
        if not ej.output or not ej.output.strip():
            problemas.append(f"ejemplo {i}: output vacio")
            continue
        if ej.text_input in vistos:
            problemas.append(f"ejemplo {i}: text_input duplicado")
        vistos.add(ej.text_input)
        try:
            salida = json.loads(ej.output)
        except json.JSONDecodeError:
            problemas.append(f"ejemplo {i}: output no es JSON valido")
            continue
        for clave in claves_esperadas:
            if clave not in salida:
                problemas.append(
                    f'ejemplo {i}: output no tiene la clave "{clave}"'
                )
    return problemas


def romper_ejemplos(
    examples: list[types.TuningExample],
) -> list[types.TuningExample]:
    """Agrega dos ejemplos malos a propósito, para probar el validador.

    Sin esto solo se sabe que el validador corre. Con esto se sabe que
    detecta. El primero va con el texto vacío y sin una de las claves,
    el segundo repite un texto que ya existe y trae un output que no
    es JSON.
    """
    return examples + [
        types.TuningExample(
            text_input="", output='{"materia": "finiquito"}'
        ),
        types.TuningExample(
            text_input=ejemplos_raw[0][0], output="no es json"
        ),
    ]


if __name__ == "__main__":
    print(f"{len(examples)} ejemplos construidos")
    print(examples[0])

    print()
    print("--- paso 1, balance sobre", CLAVE_QUE_CLASIFICA, "---")
    balance = chequear_balance(ejemplos_raw, CLAVE_QUE_CLASIFICA)
    for categoria, cuenta in balance.most_common():
        print(f"{categoria}: {cuenta}")
    maximo = max(balance.values())
    minimo = min(balance.values())
    print(f"razon max/min: {maximo / minimo:.1f}x")

    # La segunda clave no se mide con chequear_balance porque tiene
    # dos valores y la razon no diria nada util. Se informa aparte.
    calculos = Counter(
        salida["necesita_calculo"] for _, salida in ejemplos_raw
    )
    print(f"necesita_calculo verdadero en {calculos[True]} de "
          f"{len(ejemplos_raw)}")

    print()
    print("--- paso 2, validacion ---")
    problemas = validar_dataset(
        examples, claves_esperadas=CLAVES_ESPERADAS
    )
    print(f"{len(examples)} ejemplos, {len(problemas)} problemas "
          f"encontrados")
    for p in problemas:
        print(" -", p)

    print()
    print("--- paso 3, el validador contra ejemplos rotos ---")
    rotos = romper_ejemplos(examples)
    problemas_rotos = validar_dataset(
        rotos, claves_esperadas=CLAVES_ESPERADAS
    )
    print(f"{len(rotos)} ejemplos, {len(problemas_rotos)} problemas "
          f"encontrados")
    for p in problemas_rotos:
        print(" -", p)
    if not problemas_rotos:
        print("ERROR. El validador no detecto los ejemplos rotos.")
