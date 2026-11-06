"""Agente con herramientas propias, del dominio laboral (Bloque 21).

Hasta el Bloque 20 el camino lo escribíamos nosotras. La clasificación
elegía entre cuatro rutas que estaban programadas de antemano.

Acá se invierte. El modelo decide, en cada consulta, qué herramienta
usar o si no usa ninguna. Nosotras solo le damos las herramientas.

Las dos herramientas son

    buscar_articulo_del_codigo   dice en qué artículo está un tema
    calcular_indemnizacion       calcula un monto con reglas de Python

Son a propósito de naturalezas distintas, una busca y la otra calcula,
para que el agente nunca dude entre las dos. La actividad advierte que
dos herramientas parecidas hacen que el agente elija de forma
inconsistente.

El cálculo vive en Python y no en el modelo. Eso no es una decisión de
hoy, viene de la declaración del proyecto en el Módulo 1, donde quedó
escrito que los cálculos van "con reglas programadas en vez de dejarle
la aritmética al modelo".

Fuentes del contenido legal. El texto de los artículos 66, 159 a 163 y
174 a 178 se tomó del Código del Trabajo publicado por la Biblioteca
del Congreso Nacional. Las reglas de cálculo se contrastaron además
con dos consultas de la Dirección del Trabajo.
"""

import os
import textwrap
import unicodedata

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import (
    AgentExecutor,
    create_tool_calling_agent,
)


def texto_de_la_respuesta(salida):
    """Deja la respuesta final del agente como texto plano.

    La lección hace print(resultado["output"]) dando por hecho que es
    un string. Con los modelos Gemini 3.x no lo es, viene como una
    lista de bloques, cada uno un diccionario con su type y su text,
    más metadatos internos. Impreso tal cual queda ilegible.

    Esto arma el texto juntando los bloques de tipo text, y si alguna
    vez llega un string lo devuelve tal cual, para que sirva con las
    dos formas.
    """
    if isinstance(salida, str):
        return salida

    if isinstance(salida, list):
        return "\n".join(
            bloque.get("text", "")
            for bloque in salida
            if isinstance(bloque, dict) and bloque.get("type") == "text"
        )

    return str(salida)


def sin_tildes(texto):
    """Deja el texto en minúsculas y sin tildes, para poder comparar.

    Sin esto, buscar "indemnizacion" dentro de "indemnización" da falso,
    porque la i con tilde y la i sin tilde son caracteres distintos. Es
    la misma trampa de las categorías del Bloque 19, y acá pega más
    fuerte porque las personas escriben con tilde y a veces sin ella.
    """
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(
        c for c in descompuesto if not unicodedata.combining(c)
    )


# Cada entrada son las claves que la disparan y el texto que devuelve.
#
# Las claves van sin tilde y como raíces, no como palabras completas.
# "despid" calza con despido, despidieron y despedida. Si fuera
# "despido" a secas, no calzaría con "me despidieron".
ARTICULOS = (
    (
        ("fallecimiento", "muerte", "luto", "duelo"),
        "Artículo 66 del Código del Trabajo, permiso pagado por "
        "fallecimiento de un familiar. Diez días corridos por la "
        "muerte de un hijo, siete días corridos por la del cónyuge o "
        "conviviente civil, siete días hábiles por un hijo en período "
        "de gestación, y cuatro días hábiles por un hermano, el padre "
        "o la madre. El trabajador del inciso primero goza además de "
        "fuero laboral por un mes. Estos días no se pueden compensar "
        "en dinero.",
    ),
    (
        ("probidad", "acoso", "abandono", "incumplimiento grave",
         "sin derecho a indemnizacion"),
        "Artículo 160 del Código del Trabajo, causales por las que el "
        "contrato termina sin derecho a indemnización alguna. Entre "
        "ellas la falta de probidad, el acoso sexual, las vías de "
        "hecho, las injurias, la conducta inmoral, el acoso laboral, "
        "las inasistencias injustificadas, el abandono del trabajo y "
        "el incumplimiento grave de las obligaciones del contrato.",
    ),
    (
        ("necesidades de la empresa", "desahucio", "despid"),
        "Artículo 161 del Código del Trabajo, término por necesidades "
        "de la empresa, establecimiento o servicio, como las derivadas "
        "de racionalización, modernización, bajas de productividad o "
        "cambios del mercado. Contempla también el desahucio escrito "
        "del empleador para quienes tienen facultades generales de "
        "administración y para trabajadores de casa particular. No se "
        "puede invocar contra quien está con licencia médica.",
    ),
    (
        ("indemnizacion", "anos de servicio", "años de servicio"),
        "Artículo 163 del Código del Trabajo, indemnización por años "
        "de servicio. Procede si el contrato estuvo vigente un año o "
        "más y el término fue por el artículo 161. A falta de pacto "
        "superior, equivale a treinta días de la última remuneración "
        "mensual devengada por cada año de servicio y fracción "
        "superior a seis meses, con un límite máximo de trescientos "
        "treinta días.",
    ),
    (
        ("finiquito",),
        "Artículo 177 del Código del Trabajo, finiquito. Debe constar "
        "por escrito y ser otorgado por el empleador, con su pago a "
        "disposición del trabajador dentro de diez días hábiles "
        "contados desde la separación. Las partes pueden pactar el "
        "pago en cuotas.",
    ),
)


@tool
def buscar_articulo_del_codigo(consulta: str) -> str:
    """Indica en qué artículo del Código del Trabajo chileno está
    regulado un tema, y resume qué dice ese artículo.

    Usar cuando la persona pregunta dónde está regulado algo, qué dice
    la ley sobre una materia, o cuántos días o plazos corresponden en
    una situación laboral. No usar para calcular montos de dinero.
    """
    pregunta = sin_tildes(consulta)

    # Devuelve todas las coincidencias y no solo la primera, porque un
    # mismo tema puede estar repartido en varios artículos. Preguntar
    # por el despido toca el 160 y el 161 a la vez.
    encontrados = [
        texto
        for claves, texto in ARTICULOS
        if any(sin_tildes(clave) in pregunta for clave in claves)
    ]

    if not encontrados:
        return (
            "No encontré un artículo sobre ese tema en los que tengo "
            "cargados."
        )

    return "\n\n".join(encontrados)


@tool
def calcular_indemnizacion_anos_servicio(
    anos_completos: int,
    meses_adicionales: int,
    sueldo_mensual: float,
) -> str:
    """Calcula el monto de la indemnización legal por años de servicio
    según el artículo 163 del Código del Trabajo chileno.

    Usar cuando la persona pregunta cuánto dinero le corresponde de
    indemnización y entrega su antigüedad y su sueldo. No usar para
    preguntas sobre qué dice la ley, ni si no hay cifras en la
    pregunta.
    """
    try:
        # Se normaliza por si llegan doce meses o más como meses
        # adicionales, que sería la misma antigüedad mal repartida.
        total_meses = int(anos_completos) * 12 + int(meses_adicionales)
        sueldo = float(sueldo_mensual)
    except (TypeError, ValueError):
        return (
            "No pude calcular la indemnización porque la antigüedad o "
            "el sueldo no llegaron como números."
        )

    if total_meses < 0 or sueldo < 0:
        return (
            "No pude calcular la indemnización porque la antigüedad o "
            "el sueldo llegaron en negativo."
        )

    # Primer requisito del artículo 163, contrato vigente un año o más.
    if total_meses < 12:
        return (
            "No corresponde indemnización por años de servicio. El "
            "artículo 163 la reconoce solo si el contrato estuvo "
            "vigente un año o más, y acá son "
            f"{total_meses} meses."
        )

    anos = total_meses // 12
    meses = total_meses % 12

    # "por cada año de servicio y fracción superior a seis meses".
    # Seis meses exactos no suman, porque el artículo dice superior.
    computables = anos + (1 if meses > 6 else 0)

    # "límite máximo de trescientos treinta días", o sea once años.
    topado = min(computables, 11)
    monto = topado * sueldo

    aviso_tope = ""
    if computables > 11:
        aviso_tope = (
            f" Se computaron {computables} años, pero se aplicó el "
            "tope legal de once años, equivalente a trescientos "
            "treinta días."
        )

    return (
        f"La indemnización por años de servicio es de ${monto:,.0f}. "
        f"Se calculó sobre {topado} años, a razón de treinta días de "
        f"la última remuneración mensual (${sueldo:,.0f}) por año, "
        "según el artículo 163 del Código del Trabajo."
        f"{aviso_tope}"
        " Este cálculo supone que el término fue por el artículo 161, "
        "necesidades de la empresa o desahucio, que es el único caso "
        "en que esta indemnización procede. No cubre contratos por "
        "obra o faena, trabajadores de casa particular, liquidación "
        "concursal, ni indemnizaciones pactadas superiores a la legal."
    )


herramientas = [
    buscar_articulo_del_codigo,
    calcular_indemnizacion_anos_servicio,
]


prompt_agente = ChatPromptTemplate.from_messages([
    (
        "system",
        "Eres un asistente de consultas laborales de Chile. "
        "Respondes usando las herramientas disponibles cuando las "
        "necesites. Si una herramienta te dice que algo no "
        "corresponde o que no lo encontró, dilo así en tu respuesta, "
        "sin suponer el dato que falta. Cuando una herramienta te "
        "entregue cifras o plazos, repítelos exactamente como "
        "llegaron, sin agrupar casos distintos en uno solo. "
        "Escribe en texto plano, sin markdown ni asteriscos. Si "
        "enumeras, usa un guion al inicio de cada línea.",
    ),
    ("human", "{entrada}"),
    MessagesPlaceholder("agent_scratchpad"),
])


# Las comprobaciones manuales del Paso 3. Cada caso son las
# herramientas que el agente debería elegir y la entrada que las
# dispara. La actividad pide dos como mínimo, acá van cuatro.
#
# Las dos primeras prueban una ruta cada una. La tercera espera que no
# use ninguna, que es el caso que la lección pide confirmar aparte. La
# cuarta prueba que sepa encadenar las dos, que es la sección "cuando
# el agente encadena más de una herramienta" de la lección anterior.
CASOS = (
    (
        ("buscar_articulo_del_codigo",),
        "¿En qué artículo del Código del Trabajo está el permiso por "
        "fallecimiento de un familiar?",
    ),
    (
        ("calcular_indemnizacion_anos_servicio",),
        "Me despidieron por necesidades de la empresa después de 5 "
        "años y 8 meses, y mi último sueldo fue de 850000 pesos. "
        "¿Cuánto me corresponde de indemnización?",
    ),
    (
        (),
        "¿Qué significa la sigla AFP?",
    ),
    (
        (
            "buscar_articulo_del_codigo",
            "calcular_indemnizacion_anos_servicio",
        ),
        "¿En qué artículo está regulada la indemnización por años de "
        "servicio, y cuánto me corresponde si trabajé 5 años y 8 "
        "meses con un sueldo de 850000 pesos?",
    ),
)


if __name__ == "__main__":
    from contraste import *                               # noqa: F403

    load_dotenv()

    modelo = ChatGoogleGenerativeAI(
        model=os.getenv("AI_MODEL"),
    )

    agente = create_tool_calling_agent(
        modelo, herramientas, prompt_agente
    )

    # verbose imprime la traza mientras ocurre.
    # return_intermediate_steps la deja además disponible en el
    # resultado, que es lo que pide la actividad para poder verificar.
    #
    # max_iterations se deja en su valor por defecto, que son quince.
    # Una iteración es una vuelta de elegir y llamar una herramienta,
    # y las consultas de acá usan cero, una o dos. O sea que el tope
    # no se alcanza nunca en uso normal, solo si el agente se traba
    # llamando herramientas sin llegar a responder.
    #
    # Conviene bajarlo, por ejemplo a cinco, si el agente empieza a
    # trabarse seguido, o si algún día hay muchas más herramientas y
    # se quiere acotar lo que cuesta el peor caso. Con quince, un
    # agente trabado gasta unas dieciséis llamadas en una sola
    # consulta. Con cinco, unas seis.
    ejecutor_agente = AgentExecutor(
        agent=agente,
        tools=herramientas,
        verbose=True,
        return_intermediate_steps=True,
    )

    titulobn("\n\n*** Paso 3, qué herramienta eligió el agente ***")

    aciertos = 0
    for esperadas, entrada in CASOS:
        titulofn(f"\n\n  entrada")
        notabn(f"\n{entrada}\n")

        resultado = ejecutor_agente.invoke({"entrada": entrada})

        # Cada elemento de intermediate_steps es un par, la acción que
        # decidió el agente y lo que esa herramienta devolvió. Si la
        # lista viene vacía, no usó ninguna.
        #
        # dict.fromkeys saca las repetidas y conserva el orden, por si
        # el agente llama dos veces a la misma herramienta.
        pasos = resultado["intermediate_steps"]
        obtenidas = tuple(
            dict.fromkeys(accion.tool for accion, _ in pasos)
        )

        linea = (
            f"\n  esperadas  {', '.join(esperadas) or 'ninguna'}"
            f"\n  obtenidas  {', '.join(obtenidas) or 'ninguna'}"
        )

        # Se comparan como conjuntos y no en orden, porque cuál
        # herramienta usa primero es decisión suya y las dos órdenes
        # serían correctas.
        if set(obtenidas) == set(esperadas):
            aciertos += 1
            exitobn(linea)
        else:
            avisofn(linea)

        # La traza completa, como la muestra la lección. Cada paso es
        # la acción que decidió el agente, con qué argumentos, y la
        # observación que devolvió la herramienta.
        notabn("\n  traza")
        if not pasos:
            notabn("    sin pasos intermedios, respondió directo")
        for accion, observacion in pasos:
            notabn(f"    {accion.tool}  {accion.tool_input}")
            notabn(
                "      -> "
                + textwrap.shorten(
                    str(observacion), width=66, placeholder="..."
                )
            )

        notabn("\n  respuesta final")
        exitobn(texto_de_la_respuesta(resultado["output"]))

    total = len(CASOS)
    if aciertos == total:
        exitobn(f"\n\n  {aciertos}/{total} eligió bien")
    else:
        avisofn(f"\n\n  {aciertos}/{total} eligió bien")
