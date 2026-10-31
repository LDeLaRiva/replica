"""Revisión manual de una muestra de resultados, Bloque 17.

La muestra junta los cinco F1 más bajos y los cinco más altos. Los
bajos muestran dónde el cliente falla de verdad. Los altos confirman
que un puntaje casi perfecto significa una respuesta casi perfecta, y
no un falso positivo. Revisar solo los bajos dejaría sin ver justo los
casos que más confianza indebida generan, porque el número dice que
todo está bien.


Se corre con el botón de ejecutar, o desde la terminal con
`python src/revision_manual.py`
"""

import json
from pathlib import Path

# Los dos archivos quedan al lado de este script. Con el nombre a
# solo, se guardarían en la carpeta donde está la terminal, que no siempre es esta.
CARPETA = Path(__file__).resolve().parent
RUTA_RESULTADOS = CARPETA / "resultados_metricas.json"
RUTA_REVISION = CARPETA / "revision_manual.json"


CORTE = 5
# Cuántos casos se toman de cada punta. Cinco y cinco dan los diez que
# pide la actividad. Es una constante y no un 5 escrito dos veces,
# porque con menos de diez resultados hay
# que bajarlo a tres para que la muestra no repita casos del medio.


# La rúbrica. Las dos primeras aceptan "si", "no" o "parcialmente".
# La tercera acepta solo "si" o "no", porque una respuesta contradice
# o no contradice, no hay término medio.
#
# Ante la duda conviene "parcialmente" antes que forzar un "si". Y la
# nota importa tanto como las tres respuestas, porque un "no" sin
# explicación no sirve de nada al volver a leer esto en unas semanas.
#
# Esta lista se llena a mano, leyendo cada caso que imprime este
# script. Una entrada por caso revisado, con esta forma:
#
#     {
#         "consulta": "...",
#         "f1": 0.00,
#         "correccion_factual": "si",
#         "completitud": "si",
#         "contradiccion": "no",
#         "nota": "por qué quedó así",
#     },
revision_manual = [
    {
        "consulta": ("¿Cuántos días de permiso da el Código del "
                     "Trabajo chileno por matrimonio o acuerdo de "
                     "unión civil?"),
        "f1": 0.304,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("respuesta completa y correcta, incluido el detalle "
                 "de cuándo usar los días. saca el F1 más bajo de los "
                 "veinte solo por ser larga, con precisión 0.184"),
    },
    {
        "consulta": ("¿Se pueden pactar horas extraordinarias de "
                     "forma permanente en Chile?"),
        "f1": 0.320,
        "correccion_factual": "si",
        "completitud": "parcialmente",
        "contradiccion": "no",
        "nota": ("contesta bien que no se puede de forma permanente, "
                 "pero habla del límite diario cuando la referencia "
                 "habla del pacto. omite los tres meses y la "
                 "renovación, y pone en su lugar el máximo de dos "
                 "horas al día, que también es correcto"),
    },
    {
        "consulta": ("¿Cuántos días de permiso por fallecimiento de "
                     "un hijo establece el Código del Trabajo "
                     "chileno?"),
        "f1": 0.353,
        "correccion_factual": "si",
        "completitud": "parcialmente",
        "contradiccion": "no",
        "nota": ("el número está bien, pero se come que el permiso es "
                 "pagado y que es adicional al feriado anual. aquí la "
                 "cobertura de 0.400 sí refleja una respuesta "
                 "incompleta, la métrica acertó"),
    },
    {
        "consulta": ("¿Cuántas horas semanales dura la jornada "
                     "ordinaria de trabajo en Chile?"),
        "f1": 0.385,
        "correccion_factual": "no",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("dice que la jornada es de 44 horas. desde el 26 de "
                 "abril de 2026 son 42. describe el tramo de 2024 "
                 "como si fuera el vigente y se salta el actual. el "
                 "mismo error escrito con las palabras de la "
                 "referencia habría sacado 0.944"),
    },
    {
        "consulta": ("¿Se pueden compensar en dinero los días de "
                     "permiso por fallecimiento de un familiar?"),
        "f1": 0.385,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("respuesta correcta y completa, con el motivo "
                 "incluido. precisión 0.250 solo por el largo, igual "
                 "que el caso del matrimonio. segundo caso donde la "
                 "métrica castiga una respuesta sin errores"),
    },
    {
        "consulta": ("¿Cuántas semanas dura el descanso prenatal en "
                     "Chile?"),
        "f1": 0.667,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("prácticamente idéntica a la referencia y sin ningún "
                 "error. el 0.667 es el techo real de este pipeline, "
                 "porque pierde puntos solo por decir en Chile y "
                 "fecha estimada"),
    },
    {
        "consulta": ("¿Cuántos días de feriado anual corresponden a "
                     "un trabajador con más de un año de servicio?"),
        "f1": 0.698,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("correcta, y las dos cosas que agrega también lo "
                 "son. el feriado es con remuneración íntegra y es un "
                 "mínimo, porque el progresivo suma días con la "
                 "antigüedad"),
    },
    {
        "consulta": ("¿Con qué recargo mínimo se pagan las horas "
                     "extraordinarias en Chile?"),
        "f1": 0.732,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("correcta y con la misma cifra, pero la escribe 50% "
                 "donde la referencia dice 50 por ciento. "
                 "limpiar_texto borra el símbolo y se pierden las "
                 "palabras por y ciento. con el mismo formato la "
                 "cobertura sería 1.000 en vez de 0.882"),
    },
    {
        "consulta": ("¿Cuántas horas extraordinarias como máximo se "
                     "pueden trabajar en un día en Chile?"),
        "f1": 0.750,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("correcta y casi palabra por palabra. la única "
                 "diferencia de contenido es pactar contra trabajar, "
                 "y la Dirección del Trabajo usa las dos. pierde 0.15 "
                 "de F1 por el preámbulo que sale de la instrucción"),
    },
    {
        "consulta": ("¿En qué plazo debe el empleador pagar el "
                     "finiquito?"),
        "f1": 0.824,
        "correccion_factual": "si",
        "completitud": "si",
        "contradiccion": "no",
        "nota": ("la mejor respuesta de los veinte, casi palabra por "
                 "palabra. lo único que falta es pagarse contra "
                 "pagar. es el único caso donde referencia y "
                 "respuesta escriben la cifra igual, 10 en dígitos"),
    },
]



if __name__ == "__main__":
    # El módulo no usa colores, solo esta salida. contraste.py está en
    # esta misma carpeta, así que se importa directo.
    from contraste import *                               # noqa: F403

    titulobn("\nRevisión manual de una muestra, Bloque 17")

    resultados = []
    try:
        with open(RUTA_RESULTADOS, encoding="utf-8") as archivo:
            resultados = json.load(archivo)
    except FileNotFoundError:
        errorbn(f"\nNo se encontró {RUTA_RESULTADOS.name}.")
        avisofn("\nEste archivo no genera los resultados, los lee. Hay "
                "que correr\nprimero pipeline_texto.py.")

    if resultados:
        # Ordenadas de peor a mejor, igual que en pipeline_texto.py.
        peores_casos = sorted(resultados, key=lambda r: r["f1"])
        muestra_para_revisar = peores_casos[:CORTE] + peores_casos[-CORTE:]

        notabn(f"\nSobre {len(resultados)} respuestas ya calculadas, "
               f"sin consultar al modelo.")

        if len(resultados) < CORTE * 2:
            # Con menos de diez, las puntas se solapan y los casos del
            # medio salen contados dos veces.
            avisobn(f"\nHay menos de {CORTE * 2} resultados, así que la "
                    f"muestra repite\ncasos del medio. Conviene bajar "
                    f"CORTE o generar más respuestas.")

        for numero, caso in enumerate(muestra_para_revisar, 1):
            if numero == 1:
                titulofn(f"\nLos {CORTE} de F1 más bajo")
            if numero == CORTE + 1:
                titulofn(f"\nLos {CORTE} de F1 más alto")

            titulobn(f"\nCaso {numero} de {len(muestra_para_revisar)}")
            salbn(f"\n  Pregunta\n    {caso['consulta']}")
            salbn(f"\n  Referencia, escrita a mano\n    "
                  f"{caso['referencia']}")
            exitobn(f"\n  Respuesta del modelo\n    {caso['respuesta']}")
            lilabn(f"\n  Precisión {caso['precision']:.3f}    "
                   f"Cobertura {caso['cobertura']:.3f}    "
                   f"F1 {caso['f1']:.3f}")

        titulofn("\nLas tres preguntas de la rúbrica")
        salfn("  Corrección factual   ¿todo dato verificable coincide "
              "con la\n                       referencia? si, no o "
              "parcialmente")
        salfn("  Completitud          ¿cubre todo lo que cubre la "
              "referencia,\n                       o falta algo "
              "importante? si, no o parcialmente")
        salfn("  Contradicción        ¿afirma lo contrario de algo, "
              "aunque sea\n                       en una sola palabra? "
              "si o no")

        # ===== El archivo ============================================
        #
        # El JSON se genera con json.dump y no se escribe a mano. La
        # coma final de la lista de arriba es válida en Python y
        # rompería un .json. ensure_ascii=False deja las tildes y la ñ
        # legibles en vez de guardarlas como códigos de escape.

        if revision_manual:
            with open(RUTA_REVISION, "w", encoding="utf-8") as archivo:
                json.dump(revision_manual, archivo, indent=2, ensure_ascii=False)
            exitobn(f"\nRevisión guardada en {RUTA_REVISION.name}, con "
                    f"{len(revision_manual)} de "
                    f"{len(muestra_para_revisar)} casos calificados.")
        else:
            avisobn("\nTodavía no hay calificaciones. Van en la lista "
                    "revision_manual\nde más arriba, una por cada caso "
                    "leído.")

    titulobn("\nFin de la revisión")
