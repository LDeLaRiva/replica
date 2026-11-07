"""Agente con herramienta estructurada y memoria (Bloque 22).

Toma el agente del Bloque 21 y le agrega las dos piezas de este
bloque, argumentos estructurados con Pydantic en la herramienta de
cálculo, y memoria entre interacciones.

El del Bloque 21 queda intacto con su propio commit. Este archivo es
el agente vivo del proyecto, el que va a seguir creciendo.

El corpus legal no está en este archivo. Vive en
soporte_corpus_legal.py y se importa, así el texto verificado
existe en un solo lugar.

Las tres piezas que pide la lección van separadas y reconocibles.
La herramienta con args_schema, el agente con su ejecutor, y la
memoria.

Dónde está cada punto del checklist de cierre

    args_schema con descripciones por campo, en las herramientas de
    más de un parámetro
        ArgumentosIndemnizacion, sobre el cálculo
    chat_history antes del mensaje humano y agent_scratchpad
    después
        prompt_agente
    dos turnos en la misma sesión, el segundo usando el primero
        primera prueba del bloque __main__
    dos session_id distintos que no comparten historial
        segunda prueba del bloque __main__

Por qué la búsqueda no lleva args_schema

Recibe un solo parámetro. La lección dice que args_schema "vale la
pena para una herramienta con varios argumentos, pero es un paso de
más para una tan simple" que recibe uno solo, y que en ese caso el
tipo anotado y un docstring claro alcanzan. El checklist pregunta
por las herramientas de más de un parámetro, y esta no lo es.

El cálculo sí lo lleva, porque tiene cuatro.

Nombres explícitos en las dos herramientas

La lección recomienda nombrar la herramienta explícitamente cuando
el nombre de la función no basta por sí solo. En este proyecto
resuelve además un problema medido. En una corrida del Bloque 21 el
modelo invocó buscar_articulo_del_consulta, que no existe,
mezclando el nombre de la herramienta con el de su parámetro. El
nombre nuevo termina en palabras que no se confunden con ningún
argumento. El registro está en docs/limites_bloque21.md.

Lo que se resolvió distinto de la lección

El import de AgentExecutor va dentro de un try, para que el archivo
corra tanto en la versión instalada como en una anterior. La lección
usa solo la ruta nueva.

El ejecutor lleva verbose y return_intermediate_steps. La lección
los pone en su segundo bloque y los omite en su script final, así
que se toma la primera de sus dos formas.

El modelo se lee de AI_MODEL en vez de ir escrito fijo, y el prompt
del sistema conserva las reglas del Bloque 21 sobre cifras y plazos.

Sobre el normalizador

RunnableWithMessageHistory guarda en el historial lo que devuelve el
agente. Los modelos Gemini 3.x devuelven una lista de bloques de
contenido donde la lección supone un texto, así que la salida se
convierte en un mensaje antes de que la memoria la reciba.

Va de entrada y no después de ver si falla, porque el modo de falla
es silencioso. La lección advierte que el agente responde con
normalidad y el historial queda vacío sin avisar. Por eso cada turno
imprime además cuántos mensajes tiene el historial, que es la
comprobación que la lección indica.
"""

import logging
import os
import time

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# La ruta vieja primero y la nueva como respaldo. En la versión
# instalada la primera falla y corre la segunda. El try existe para
# que el archivo también corra en un entorno con LangChain anterior
# a la 1.x, donde la segunda no existe.
try:
    from langchain.agents import (
        AgentExecutor,
        create_tool_calling_agent,
    )
except ImportError:
    from langchain_classic.agents import (
        AgentExecutor,
        create_tool_calling_agent,
    )

from soporte_corpus_legal import buscar_articulos

logger = logging.getLogger(__name__)

# Espera previa al único reintento. Veinte segundos, porque un 503
# UNAVAILABLE responde a una saturación momentánea del proveedor.
ESPERA_REINTENTO = 20


def invocar_con_reintento(agente, entrada, config,
                          espera=ESPERA_REINTENTO):
    """Invoca el agente y reintenta una vez si la primera falla.

    Un 503 UNAVAILABLE del proveedor indica saturación momentánea del
    servicio, no agotamiento de cuota ni error en la solicitud. Sin
    reintento, un fallo así interrumpe la prueba completa, que es lo
    que ocurrió en una corrida del Bloque 21.

    Si el reintento también falla, la excepción se propaga en lugar
    de saltar al turno siguiente. Es la diferencia con la versión del
    Bloque 21, donde los casos eran independientes. En esta prueba
    cada turno
    depende del anterior, de modo que seguir sin el primero no
    probaría nada.

    El manejo no oculta el error. logger.exception registra el
    traceback completo antes de reintentar.
    """
    try:
        return agente.invoke({"entrada": entrada}, config)
    except Exception:
        logger.exception(
            "Falló la invocación del agente, se reintenta una vez "
            "en %s segundos", espera
        )
        time.sleep(espera)
        return agente.invoke({"entrada": entrada}, config)


def texto_de_la_respuesta(salida):
    """Deja la respuesta del agente como texto plano.

    Maneja las tres formas en que puede llegar. Un objeto de mensaje,
    del que se toma el contenido. Una lista de bloques, que es lo que
    devuelven los modelos Gemini 3.x y que impresa sin procesar queda
    ilegible. Y un texto, que se devuelve tal cual.

    La versión del Bloque 21 no contemplaba el objeto de mensaje,
    porque ahí nada lo producía. En este archivo sí, porque el
    normalizador envuelve la salida antes de guardarla en el
    historial.
    """
    if hasattr(salida, "content"):
        salida = salida.content

    if isinstance(salida, str):
        return salida

    if isinstance(salida, list):
        return "\n".join(
            bloque.get("text", "")
            for bloque in salida
            if isinstance(bloque, dict) and bloque.get("type") == "text"
        )

    return str(salida)


def normalizar_para_historial(resultado):
    """Convierte la salida del agente en un mensaje, para el historial.

    RunnableWithMessageHistory guarda lo que el agente devuelve. Con
    una lista de bloques de contenido no tiene un mensaje que guardar,
    y el historial puede quedar vacío sin que nada avise.

    Reutiliza texto_de_la_respuesta en vez de repetir la extracción,
    así la lógica de las formas de salida vive en un solo lugar.
    """
    return {
        **resultado,
        "output": AIMessage(
            content=texto_de_la_respuesta(resultado["output"])
        ),
    }


# *** Las herramientas ***


@tool("buscar_articulo_del_codigo_del_trabajo")
def buscar_articulo(consulta: str) -> str:
    """Indica en qué artículo del Código del Trabajo chileno está
    regulado un tema y entrega el texto de ese artículo.

    Usar cuando la persona pregunta dónde está regulado algo, qué dice
    la ley sobre una materia, o cuántos días o plazos corresponden en
    una situación laboral. No usar para calcular montos de dinero.
    """
    return buscar_articulos(consulta)


class ArgumentosIndemnizacion(BaseModel):
    """Los cuatro datos que necesita el cálculo del artículo 163.

    Cada campo lleva su propia descripción porque el docstring de la
    función describe la herramienta completa y no dice nada sobre un
    argumento en particular. Con cuatro, el modelo necesita saber qué
    representa cada uno para armar bien la llamada.
    """

    anos_completos: int = Field(
        description=(
            "Años completos que la persona trabajó para ese "
            "empleador, sin contar los meses sueltos."
        ),
    )
    meses_adicionales: int = Field(
        description=(
            "Meses sueltos además de esos años completos. Para "
            "cinco años y ocho meses, va 8."
        ),
    )
    sueldo_mensual: float = Field(
        description=(
            "Última remuneración mensual bruta, en pesos chilenos, "
            "sin separadores de miles."
        ),
    )
    horas_semanales: int = Field(
        default=0,
        description=(
            "Jornada semanal en horas. Pásalo solo si la persona "
            "menciona su jornada, porque las de treinta horas o "
            "menos se rigen además por el artículo 40 bis D y la "
            "respuesta cambia. Si no la menciona, déjalo en cero y "
            "no inventes un valor."
        ),
    )


@tool(
    "calcular_indemnizacion_por_anos_de_servicio",
    args_schema=ArgumentosIndemnizacion,
)
def calcular_indemnizacion(
    anos_completos: int,
    meses_adicionales: int,
    sueldo_mensual: float,
    horas_semanales: int = 0,
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
        horas = int(horas_semanales)
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
            "vigente un año o más, y el tuyo alcanzó "
            f"{total_meses} meses."
        )

    anos = total_meses // 12
    meses = total_meses % 12

    # "por cada año de servicio y fracción superior a seis meses".
    # Seis meses exactos no suman, porque el artículo dice superior.
    computables = anos + (1 if meses > 6 else 0)

    # "límite máximo de trescientos treinta días", es decir once años.
    topado = min(computables, 11)
    monto = topado * sueldo

    aviso_tope = ""
    if computables > 11:
        aviso_tope = (
            f" Se computaron {computables} años, pero se aplicó el "
            "tope legal de once años, equivalente a trescientos "
            "treinta días."
        )

    # Redactadas como se le dirían a quien consulta, y no como nota
    # interna del cálculo. El modelo puede reproducir la observación
    # textualmente en su respuesta final, de modo que una expresión
    # referida a la herramienta misma llegaría al destinatario sin
    # referente.
    supuestos = (
        " Este monto supone que el término fue por el artículo 161, "
        "necesidades de la empresa o desahucio, que es el único caso "
        "en que esta indemnización procede. No se aplica a contratos "
        "por obra o faena, a trabajadores de casa particular, a la "
        "liquidación concursal, ni cuando lo pactado en el contrato "
        "es superior a la indemnización legal, porque en ese caso se "
        "paga lo pactado."
    )

    # Jornada parcial. El artículo 40 bis la define como treinta horas
    # semanales o menos, y el 40 bis D manda calcular sobre el
    # promedio de las remuneraciones reajustadas por IPC.
    #
    # Ese promedio no se puede calcular en este módulo, porque
    # necesita el historial del IPC de hasta once años. Pero el
    # mismo artículo cierra diciendo que si la del 163 resulta
    # superior se aplica
    # ésa, así que el monto del 163 es un piso garantizado y eso sí
    # se puede afirmar.
    #
    # La primera oración nombra el 163 antes que el 40 bis D, porque
    # el 163 es la norma que regula la indemnización y el 40 bis D
    # solo modifica qué se entiende por última remuneración. En el
    # orden inverso, la observación induce a presentar el 40 bis D
    # como la norma que la regula.
    #
    # Se mantiene como oración independiente y no unida a la
    # siguiente. Unirlas trasladaría la regla de los treinta días al
    # interior de la oración referida a la jornada parcial, que es
    # justamente el caso donde el 40 bis D modifica la base de ese
    # cálculo. Una oración extensa mal comprimida afirma algo
    # incorrecto, y una oración breve omitida solo pierde
    # información.
    if 0 < horas <= 30:
        return (
            "La indemnización por años de servicio la regula el "
            "artículo 163. "
            f"Con una jornada parcial de {horas} horas semanales se "
            "aplica además el artículo 40 bis D, que no cambia la "
            "regla de los treinta días por año, sino qué se entiende "
            "por última remuneración. Manda tomar el promedio de las "
            "remuneraciones percibidas durante toda la vigencia del "
            "contrato, o de sus últimos once años, reajustada cada "
            "una por el IPC entre el mes anterior a su pago y el mes "
            "anterior al término del contrato. Ese promedio no se "
            "puede obtener con los datos de esta consulta, porque "
            "necesita el historial del IPC."
            f" Lo que sí está determinado es un piso de ${monto:,.0f}, "
            "porque el propio artículo 40 bis D dispone que si la "
            "indemnización del artículo 163 resulta superior, se "
            "aplica ésa. Ese "
            f"monto sale de {topado} años a razón de treinta días de "
            f"${sueldo:,.0f} por año."
            f"{aviso_tope}"
            f"{supuestos}"
        )

    # Si no informaron la jornada, no se supone cuál es. Se avisa.
    aviso_parcial = ""
    if horas == 0:
        aviso_parcial = (
            " Si la jornada fuera parcial, de treinta horas semanales "
            "o menos, aplicaría además el artículo 40 bis D y este "
            "monto pasaría a ser un piso y no el total."
        )

    return (
        f"La indemnización por años de servicio es de ${monto:,.0f}. "
        f"Se calculó sobre {topado} años, a razón de treinta días de "
        f"la última remuneración mensual (${sueldo:,.0f}) por año, "
        "según el artículo 163 del Código del Trabajo."
        f"{aviso_tope}"
        f"{supuestos}"
        f"{aviso_parcial}"
    )


herramientas = [
    buscar_articulo,
    calcular_indemnizacion,
]


# *** El agente y su ejecutor ***

# Los dos MessagesPlaceholder cumplen roles distintos y el orden
# importa. chat_history trae lo que se dijo en interacciones
# anteriores, y va antes del mensaje humano. agent_scratchpad trae el
# razonamiento de la interacción actual, y va después.
prompt_agente = ChatPromptTemplate.from_messages([
    (
        "system",
        "Eres un asistente de consultas laborales de Chile. "
        "Respondes usando las herramientas disponibles cuando las "
        "necesites. Si una herramienta te dice que algo no "
        "corresponde o que no lo encontró, dilo así en tu respuesta, "
        "sin suponer el dato que falta. Cuando una herramienta te "
        "entregue cifras, plazos o números de artículo, repítelos "
        "exactamente como llegaron, sin agrupar casos distintos en "
        "uno solo. "
        "Cuando respondas sobre un artículo, di cuál es y qué "
        "establece en lo que viene al caso, con los plazos y las "
        "cifras que trae. No transcribas el artículo completo. "
        "Escribe en texto plano, sin markdown ni asteriscos. Si "
        "enumeras, usa un guion al inicio de cada línea.",
    ),
    MessagesPlaceholder("chat_history"),
    ("human", "{entrada}"),
    MessagesPlaceholder("agent_scratchpad"),
])


# *** La memoria entre interacciones ***

# Un historial por session_id. Es lo que separa una conversación de
# otra, de modo que dos personas distintas no se vean los mensajes.
#
# Vive en memoria del proceso, así que se pierde al reiniciar. Para
# un servicio real habría que guardarlo en una base de datos, y el
# diseño ya lo permite, porque basta cambiar obtener_historial por
# una versión que lea y escriba en otra parte sin tocar nada más.
historiales = {}


def obtener_historial(session_id):
    """Devuelve el historial de esa sesión, y lo crea si no existe."""
    if session_id not in historiales:
        historiales[session_id] = InMemoryChatMessageHistory()
    return historiales[session_id]


def cerrar_sesion(session_id):
    """Borra el historial de una sesión terminada.

    Sin esto, un servicio de larga duración acumula un historial por
    cada session_id que haya visto, sin ningún límite. Nada se vacía
    solo, el historial solo crece hasta que se borra con esta función.

    pop con valor por defecto no falla si la sesión ya no existe, así
    que es seguro llamarlo más de una vez.
    """
    historiales.pop(session_id, None)


def construir_agente_con_memoria(ejecutor):
    """Envuelve el ejecutor con el historial de conversación.

    Entre el ejecutor y la memoria va el normalizador, para que lo
    que se guarde sea un mensaje y no una lista de bloques.

    output_messages_key le dice a la memoria cuál de las claves del
    resultado contiene la respuesta. La lección no lo pasa, pero
    en este caso hay un paso intermedio y conviene ser explícita.
    """
    normalizado = ejecutor | RunnableLambda(normalizar_para_historial)
    return RunnableWithMessageHistory(
        normalizado,
        obtener_historial,
        input_messages_key="entrada",
        history_messages_key="chat_history",
        output_messages_key="output",
    )


def responder(agente, entrada, session_id):
    """Un turno de conversación.

    Devuelve la respuesta en texto, las herramientas que el agente
    usó, y cuántos mensajes quedaron en el historial de esa sesión.

    Ese último número es la comprobación que indica la lección. Si no
    crece después de cada turno, el historial no se está guardando, y
    ese fallo no se manifiesta de ninguna otra forma.
    """
    config = {"configurable": {"session_id": session_id}}
    resultado = invocar_con_reintento(agente, entrada, config)
    usadas = tuple(dict.fromkeys(
        accion.tool
        for accion, _ in resultado.get("intermediate_steps", [])
    ))
    return (
        texto_de_la_respuesta(resultado["output"]),
        usadas,
        len(obtener_historial(session_id).messages),
    )


if __name__ == "__main__":
    from contraste import *                               # noqa: F403

    logging.basicConfig(level=logging.WARNING, force=True)
    for ruidosa in ("httpx", "google_genai"):
        logging.getLogger(ruidosa).setLevel(logging.WARNING)

    load_dotenv()

    modelo = ChatGoogleGenerativeAI(
        model=os.getenv("AI_MODEL"),
    )

    agente = create_tool_calling_agent(
        modelo, herramientas, prompt_agente
    )

    ejecutor_agente = AgentExecutor(
        agent=agente,
        tools=herramientas,
        verbose=True,
        return_intermediate_steps=True,
    )

    agente_con_memoria = construir_agente_con_memoria(ejecutor_agente)

    def mostrar_turno(entrada, sesion):
        """Corre un turno, lo imprime y devuelve su respuesta y el
        largo del historial."""
        titulofn(f"\n\n  sesión {sesion}")
        notabn(f"\n{entrada}\n")
        texto, usadas, cuantos = responder(
            agente_con_memoria, entrada, sesion
        )
        notabn(f"\n  herramientas   {', '.join(usadas) or 'ninguna'}")
        notabn(f"  historial      {cuantos} mensajes")
        notabn("\n  respuesta")
        exitobn(texto)
        return texto, cuantos

    # *** Primera prueba, dos turnos en la misma sesión ***
    #
    # El segundo turno no repite la antigüedad. Si la memoria funciona,
    # el agente la toma del primero y vuelve a llamar al cálculo. Si no
    # funciona, no tiene con qué calcular y lo va a decir.
    titulobn("\n\n*** Primera prueba, dos turnos en la misma sesión ***")

    SESION = "consulta_001"
    largo_inicial = len(obtener_historial(SESION).messages)

    mostrar_turno(
        "Me despidieron por necesidades de la empresa después de 5 "
        "años y 8 meses, mi último sueldo fue de 850000 pesos. "
        "¿Cuánto me corresponde?",
        SESION,
    )
    _, largo_final = mostrar_turno(
        "¿Y si mi sueldo hubiera sido 1200000?",
        SESION,
    )

    if largo_final > largo_inicial:
        exitobn(
            f"\n  el historial creció de {largo_inicial} a "
            f"{largo_final} mensajes, "
            "la memoria está guardando"
        )
    else:
        avisofn(
            f"\n  el historial quedó en {largo_final} mensajes, no está "
            "guardando. Revisar input_messages_key y el normalizador"
        )

    # *** Segunda prueba, dos sesiones que no se mezclan ***
    #
    # Lo que viaja en este historial es el despido de una persona, su
    # sueldo y su antigüedad. Que no se filtre a otra sesión no es un
    # detalle de implementación.
    #
    # Los datos de consulta_002 son distintos de los de consulta_001 a
    # propósito. Con la misma antigüedad y el mismo sueldo en las dos
    # sesiones, una filtración no se puede atribuir a ninguna, y si
    # las cifras coinciden tampoco se nota.
    titulobn("\n\n*** Segunda prueba, dos sesiones que no se mezclan ***")

    mostrar_turno(
        "Me despidieron por necesidades de la empresa después de 12 "
        "años y 3 meses, mi último sueldo fue de 640000 pesos. "
        "¿Cuánto me corresponde?",
        "consulta_002",
    )
    respuesta_003, _ = mostrar_turno(
        "¿Cuántos años te dije que trabajé y cuál era mi sueldo?",
        "consulta_003",
    )

    largo_002 = len(obtener_historial("consulta_002").messages)
    largo_003 = len(obtener_historial("consulta_003").messages)
    notabn(f"\n  historial de consulta_002   {largo_002} mensajes")
    notabn(f"  historial de consulta_003   {largo_003} mensajes")

    # Las cifras de cada sesión, en las formas en que el modelo las
    # puede escribir. consulta_003 no recibió ningún dato, así que
    # cualquiera de estas en su respuesta viene de otro historial. Se
    # verificó que ninguna aparece en el texto de los artículos, de
    # modo que una cita del corpus no las gatilla.
    marcas_por_sesion = {
        "consulta_001": (
            "850.000", "850000", "850,000",
            "1.200.000", "1200000", "1,200,000",
        ),
        "consulta_002": (
            "640.000", "640000", "640,000",
            "12 años", "doce años",
        ),
    }
    filtradas = tuple(
        f"{sesion} ({marca})"
        for sesion, marcas in marcas_por_sesion.items()
        for marca in marcas
        if marca in respuesta_003
    )

    # Que no haya marcas no prueba que no hubo filtración, porque el
    # modelo podría parafrasear las cifras en vez de escribirlas. Lo
    # que atrapa es el caso en que las escribe, que es el que el ojo
    # se puede saltar dentro de una respuesta larga.
    if filtradas:
        avisofn(
            "\n  consulta_003 nombró datos de otra sesión, "
            + ", ".join(filtradas)
        )
    else:
        exitobn(
            "\n  consulta_003 no escribió el sueldo ni la antigüedad "
            "de ninguna otra sesión"
        )

    # El historial se limpia al terminar, como indica la lección.
    for sesion in ("consulta_001", "consulta_002", "consulta_003"):
        cerrar_sesion(sesion)
    exitobn(
        f"\n  sesiones cerradas, quedan {len(historiales)} "
        "en memoria"
    )
