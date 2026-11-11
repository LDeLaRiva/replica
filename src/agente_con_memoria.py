"""Agente de consultas laborales, memoria y límites (Bloques 22 y 23).

Es el agente vivo del proyecto. A agente_con_herramientas.py le
agrega
memoria entre interacciones, argumentos estructurados con Pydantic y
una herramienta que no se puede deshacer, que por eso pide
aprobación humana antes de ejecutarse. El anterior queda intacto con
su propio commit.

El corpus legal y las funciones de supervisión no están en este
archivo. Viven en soporte_corpus_legal.py y en
soporte_supervision.py, siguiendo la retroalimentación del Gate 1,
que pidió continuar desacoplando las funciones auxiliares hacia
módulos de soporte para mantener conciso el punto de entrada.

A quién atiende

A las dos partes. Al área de recursos humanos de una empresa y a los
trabajadores que quieran consultar por su cuenta. Las dos preguntan
sobre lo mismo desde lados opuestos, así que una respuesta correcta
para una puede no convenirle a la otra.

De ahí sale la única separación de acceso que el proyecto necesita,
que el envío del aviso corresponde solo a recursos humanos. Esa
separación no está implementada. No hay inicio de sesión, y hoy lo
único que cumple esa función es que una persona tenga que aprobar el
envío. Está documentado en docs/limites_autonomia_agente.md.

Las tres herramientas

    buscar_articulo_del_codigo_del_trabajo        riesgo bajo
    calcular_indemnizacion_por_anos_de_servicio   riesgo bajo
    enviar_aviso_de_termino_de_contrato           riesgo alto

Las dos primeras leen y calculan, y lo peor que puede pasar si el
agente las usa mal es una respuesta equivocada. La tercera notifica
a una persona que su contrato termina, y eso no se retira. Por eso
es la única que pide aprobación. Pedirla también en las otras dos la
volvería costumbre, y quien aprueba por costumbre no lee lo que
aprueba.

Por qué este archivo no reintenta las invocaciones

agente_con_herramientas.py reintenta una vez, porque una caída
momentánea del proveedor cortó una corrida completa. Este no, y la
razón es la herramienta de riesgo alto.

Reintentar una invocación rehace el turno entero. Si la falla llega
después de que el supervisor aprobó y el aviso ya salió, el
reintento vuelve a pedir la aprobación y vuelve a enviar. Lo probé
con un fallo puesto justo en ese punto y quedaron dos envíos
registrados.

Repetir una lectura no cuesta nada. Repetir algo que escribe, sí.
Así que los reintentos quedan en la llamada al modelo, donde no
vuelven a ejecutar ninguna herramienta, y una falla que no se
resuelve esperando se propaga en vez de esconderse.

Por qué la salida pasa por un normalizador

La memoria guarda lo que el agente devuelve. Los modelos Gemini 3.x
devuelven una lista de bloques de contenido donde se espera un
texto, y sin un mensaje que guardar el historial queda vacío.

Lo peligroso es que no avisa. El agente responde con normalidad y la
memoria no guarda nada. Por eso el normalizador va puesto de entrada
y no después de ver si falla, y por eso cada turno imprime cuántos
mensajes tiene el historial.

Por qué los nombres de las herramientas van escritos

En agente_con_herramientas.py la búsqueda se llamaba
buscar_articulo_del_codigo y su parámetro se llamaba consulta. En
una corrida el modelo la invocó como buscar_articulo_del_consulta,
cambiando la última palabra del nombre por el nombre del parámetro.
Esa herramienta no existe, así que la llamada falló.

El nombre terminaba en del_codigo, que se lee como un hueco
esperando que le pongan algo, y el modelo le puso lo único que tenía
a mano. El nombre de ahora termina en del_trabajo, que completa el
nombre del Código del Trabajo y no deja una palabra final suelta.
El registro está en docs/limites_bloque21.md.

Por qué solo dos llevan args_schema

La búsqueda recibe un parámetro y le alcanza con el tipo anotado y
su docstring. El cálculo y el envío reciben cuatro cada uno, y con
cuatro el modelo necesita saber qué representa cada campo para armar
bien la llamada.

Dónde queda el registro de lo que hizo

Cada turno se escribe en trazas_agente.jsonl, en esta misma
carpeta. Se escribe dentro de responder y no en cada prueba, porque
es el único lugar por el que pasan todas las interacciones. Una
traza que haya que acordarse de escribir es una traza que alguna vez
falta.

Cada línea guarda qué se preguntó, qué herramientas se usaron y con
qué argumentos, si un humano autorizó el envío, y qué se respondió.
"""

import logging
import os
from typing import Any

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
from soporte_supervision import (
    RUTA_TRAZAS,
    esperar_aprobacion,
    registrar_aprobacion,
    registrar_traza,
    registro_aprobaciones,
)

def texto_de_la_respuesta(salida: Any) -> str:
    """Deja la respuesta del agente como texto plano.

    Maneja las tres formas en que puede llegar. Un objeto de mensaje,
    del que se toma el contenido. Una lista de bloques, que es lo que
    devuelven los modelos Gemini 3.x y que impresa sin procesar queda
    ilegible. Y un texto, que se devuelve tal cual.

    La versión anterior de esta función no contemplaba el objeto de
    mensaje, porque nada lo producía. Ahora sí, porque el normalizador
    envuelve la salida antes de guardarla en el historial.
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


def normalizar_para_historial(resultado: dict) -> dict:
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


def en_lista(partes: list) -> str:
    """Une varios textos con comas y una y al final.

    Con tres o más, una y repetida entre todos se lee mal. Esto deja
    "el nombre, la causal y el monto" en vez de encadenarlos.
    """
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + " y " + partes[-1]


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

    # Los obligatorios llevan valor por defecto por el mismo motivo
    # que en ArgumentosAvisoTermino. Un campo que el modelo olvide
    # haría que Pydantic rechace la llamada antes de entrar a la
    # función, y ese rechazo corta la corrida en vez de dejar que la
    # herramienta diga qué falta.
    anos_completos: int = Field(
        default=0,
        description=(
            "Años completos que la persona trabajó para ese "
            "empleador, sin contar los meses sueltos."
        ),
    )
    meses_adicionales: int = Field(
        default=0,
        description=(
            "Meses sueltos además de esos años completos. Para "
            "cinco años y ocho meses, va 8."
        ),
    )
    sueldo_mensual: float = Field(
        default=0.0,
        description=(
            "Obligatorio. Última remuneración mensual bruta, en "
            "pesos chilenos y sin separadores de miles."
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

    # Los tipos ya vienen validados. args_schema convierte y rechaza
    # antes de entrar aquí, de modo que un sueldo que llegue como
    # texto no numérico no alcanza esta línea. Lo que sigue revisa
    # solo lo que el schema no puede expresar, que son los valores
    # negativos y el requisito de antigüedad del artículo 163.
    #
    # Se normaliza por si llegan doce meses o más como meses
    # adicionales, que sería la misma antigüedad mal repartida.
    total_meses = anos_completos * 12 + meses_adicionales
    sueldo = sueldo_mensual
    horas = horas_semanales

    if total_meses < 0 or sueldo < 0:
        return (
            "No pude calcular la indemnización porque la antigüedad o "
            "el sueldo llegaron en negativo."
        )

    # Un dato que no llegó queda en cero, y eso no es lo mismo que un
    # sueldo de cero. Se nombra cuál falta, porque si no la respuesta
    # diría que no corresponde indemnización cuando lo que pasó es
    # que faltó el dato.
    faltantes = []
    if sueldo == 0:
        faltantes.append("el sueldo mensual")
    if total_meses == 0:
        faltantes.append("la antigüedad")

    if faltantes:
        return (
            "No pude calcular la indemnización porque falta "
            + en_lista(faltantes)
            + ". Vuelve a llamar la herramienta con ese dato."
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
        "necesidades de la empresa o desahucio. Si fue por otra "
        "causal y un tribunal la declara injustificada, indebida o "
        "improcedente, el artículo 168 ordena pagar esta misma "
        "indemnización con un recargo de entre el treinta y el "
        "ochenta por ciento. No se aplica a los contratos por obra o "
        "faena, que tienen la suya propia en el inciso tercero del "
        "artículo 163, ni a los trabajadores de casa particular, ni "
        "cuando lo pactado en el contrato es superior a la "
        "indemnización legal, porque en ese caso se paga lo pactado."
        " Hay además un tope que este cálculo no aplica. El inciso "
        "tercero del artículo 172 limita a noventa unidades de "
        "fomento la remuneración con que se calcula, y el valor de "
        "la UF no está disponible en esta consulta, de modo que si "
        "el sueldo supera ese tope el monto real es menor que el "
        "indicado."
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


class ArgumentosAvisoTermino(BaseModel):
    """Los datos que el artículo 162 exige que el aviso contenga.

    Los cuatro campos no son una elección de diseño. El inciso
    primero del 162 exige expresar la causal invocada cuando el
    término es por los artículos 159 o 160. El inciso cuarto exige
    el plazo de treinta días de anticipación y el monto total a
    pagar, cuando la causal es la del inciso primero del artículo
    161. Y el aviso se dirige siempre a una persona determinada.
    """

    # Los tres primeros son obligatorios y aun así llevan un valor
    # por defecto. No es un descuido.
    #
    # Sin el valor por defecto, un campo que el modelo olvide hace
    # que Pydantic rechace la llamada antes de entrar a la función, y
    # ese rechazo sube como excepción y corta la corrida. Pasó en una
    # corrida real, el modelo omitió el nombre del trabajador y el
    # programa se cayó antes de llegar a pedir la aprobación.
    #
    # Con el valor por defecto la llamada entra, la función revisa
    # qué falta y devuelve un mensaje diciéndolo. Ese mensaje vuelve
    # al modelo como observación, y el modelo puede llamar de nuevo
    # con el dato que le faltaba. La descripción de cada campo dice
    # que es obligatorio, y quien lo exige de verdad es la función.
    nombre_trabajador: str = Field(
        default="",
        description=(
            "Obligatorio. Nombre de la persona a la que se dirige el "
            "aviso, tal como aparece en su contrato."
        ),
    )
    causal: str = Field(
        default="",
        description=(
            "Obligatorio. Causal de término invocada, por ejemplo "
            "necesidades de la empresa. El artículo 162 exige "
            "nombrarla en el aviso."
        ),
    )
    monto_indemnizacion: float = Field(
        default=0.0,
        description=(
            "Obligatorio. El monto de la indemnización por años de "
            "servicio, en pesos chilenos y sin separadores de miles. "
            "Pasa el número que devolvió la herramienta de cálculo, "
            "tal cual y sin sumarle nada. La sustitutiva del aviso "
            "previo no va incluida, el aviso la nombra aparte."
        ),
    )
    dias_de_aviso: int = Field(
        default=0,
        description=(
            "Días de anticipación con que se da el aviso. Si son "
            "menos de treinta, corresponde además la indemnización "
            "sustitutiva del aviso previo. Déjalo en cero si la "
            "persona no lo menciona."
        ),
    )


@tool(
    "enviar_aviso_de_termino_de_contrato",
    args_schema=ArgumentosAvisoTermino,
)
def enviar_aviso_de_termino(
    nombre_trabajador: str,
    causal: str,
    monto_indemnizacion: float,
    dias_de_aviso: int = 0,
) -> str:
    """Envía al trabajador el aviso de término de contrato que exige
    el artículo 162 del Código del Trabajo chileno.

    Usar solo cuando el área de recursos humanos pide expresamente
    que se notifique un término de contrato y entrega el nombre, la
    causal y el monto. No usar para responder consultas, ni para
    explicar cómo se hace, ni a petición del propio trabajador.

    Es una acción irreversible y requiere aprobación humana antes de
    ejecutarse. Una vez enviado, el trabajador queda notificado. Si
    la causal es la del inciso primero del artículo 161, el artículo
    169 considera ese aviso una oferta irrevocable de pago. Y el
    inciso noveno del artículo 162 establece que los errores u
    omisiones no invalidan la terminación del contrato, salvo los que
    tengan relación con el pago íntegro de las cotizaciones
    previsionales.

    El envío está simulado. Esta versión del proyecto no se conecta
    a ningún servicio de correo ni a la Inspección del Trabajo.
    """

    # args_schema ya convirtió los tipos. Lo que sigue revisa que los
    # datos obligatorios hayan llegado y que tengan sentido, y nombra
    # cuál falta para que el modelo pueda corregir y llamar de nuevo.
    monto = monto_indemnizacion
    dias = dias_de_aviso

    if monto < 0 or dias < 0:
        return (
            "No preparé el aviso y no se envió nada, porque el monto "
            "o los días de anticipación llegaron en negativo."
        )

    faltantes = []
    if not nombre_trabajador.strip():
        faltantes.append("el nombre del trabajador")
    if not causal.strip():
        faltantes.append("la causal invocada")
    if monto == 0:
        faltantes.append("el monto de la indemnización")

    if faltantes:
        return (
            "No preparé el aviso y no se envió nada, porque falta "
            + en_lista(faltantes)
            + ". El artículo 162 exige los tres datos en el aviso. "
            "Vuelve a llamar la herramienta con lo que falta."
        )

    # Artículo 162 inciso cuarto. Con menos de treinta días de
    # anticipación no se omite el aviso, se paga además la
    # sustitutiva. Se dice en la pregunta porque cambia lo que la
    # empresa va a desembolsar.
    if dias >= 30:
        nota_plazo = f"con {dias} días de anticipación"
    else:
        nota_plazo = (
            "sin los treinta días de anticipación, de modo que "
            "corresponde pagar además la indemnización sustitutiva "
            "del aviso previo, equivalente a la última remuneración "
            "mensual devengada y que no está incluida en el monto "
            "indicado"
        )

    # El aviso dice qué se va a hacer y por qué no se puede deshacer,
    # con los dos artículos que lo respaldan. Una pregunta que solo
    # dijera si aprobar o no se contesta sin leerla.
    mensaje = (
        f"\nEl agente quiere enviar un aviso de término de contrato "
        f"a {nombre_trabajador}, por {causal}, {nota_plazo}, con una "
        f"indemnización de ${monto:,.0f}.\n"
        f"Una vez enviado, el trabajador queda notificado. Si la "
        f"causal es la del inciso primero del artículo 161, el "
        f"artículo 169 considera este aviso una oferta irrevocable "
        f"de pago.\n"
        f"El inciso noveno del artículo 162 establece que los "
        f"errores u omisiones no invalidan la terminación, salvo los "
        f"que tengan relación con el pago íntegro de las "
        f"cotizaciones previsionales, y que esos errores igual se "
        f"sancionan con multa administrativa.\n"
        f"¿Aprobar? (s/n): "
    )

    aprobado = esperar_aprobacion(mensaje)

    # Se registra la decisión antes de actuar y cualquiera sea el
    # resultado. Sin el rechazo no habría cómo responder después por
    # qué un aviso no se envió.
    registrar_aprobacion(
        herramienta="enviar_aviso_de_termino_de_contrato",
        argumentos={
            "nombre_trabajador": nombre_trabajador,
            "causal": causal,
            "monto_indemnizacion": monto,
            "dias_de_aviso": dias,
        },
        aprobado=aprobado,
    )

    if not aprobado:
        return (
            "El aviso de término no se envió, porque el supervisor "
            "humano no lo aprobó. El contrato sigue vigente y no se "
            "notificó nada al trabajador."
        )

    return (
        f"Se envió a {nombre_trabajador} el aviso de término de "
        f"contrato por {causal}, {nota_plazo}, indicando una "
        f"indemnización de ${monto:,.0f}. La notificación ya no se "
        "puede retirar."
    )


herramientas = [
    buscar_articulo,
    calcular_indemnizacion,
    enviar_aviso_de_termino,
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


def obtener_historial(session_id: str) -> InMemoryChatMessageHistory:
    """Devuelve el historial de esa sesión, y lo crea si no existe."""
    if session_id not in historiales:
        historiales[session_id] = InMemoryChatMessageHistory()
    return historiales[session_id]


def cerrar_sesion(session_id: str) -> None:
    """Borra el historial de una sesión terminada.

    Sin esto, un servicio de larga duración acumula un historial por
    cada session_id que haya visto, sin ningún límite. Nada se vacía
    solo, el historial solo crece hasta que se borra con esta función.

    pop con valor por defecto no falla si la sesión ya no existe, así
    que es seguro llamarlo más de una vez.
    """
    historiales.pop(session_id, None)


def construir_agente_con_memoria(
    ejecutor: Any,
) -> RunnableWithMessageHistory:
    """Envuelve el ejecutor con el historial de conversación.

    Entre el ejecutor y la memoria va el normalizador, para que lo
    que se guarde sea un mensaje y no una lista de bloques.

    output_messages_key le dice a la memoria cuál de las claves del
    resultado contiene la respuesta. Con un paso intermedio en medio
    conviene decirlo y no dejarlo a que lo adivine.
    """
    normalizado = ejecutor | RunnableLambda(normalizar_para_historial)
    return RunnableWithMessageHistory(
        normalizado,
        obtener_historial,
        input_messages_key="entrada",
        history_messages_key="chat_history",
        output_messages_key="output",
    )


def responder(agente: Any, entrada: str, session_id: str) -> tuple:
    """Un turno de conversación.

    Devuelve la respuesta en texto, las herramientas que el agente
    usó, y cuántos mensajes quedaron en el historial de esa sesión.

    Ese último número es la forma de comprobar la memoria. Si no
    crece después de cada turno, el historial no se está guardando, y
    ese fallo no se manifiesta de ninguna otra forma.

    Cada turno queda además escrito en el archivo de trazas. Va aquí
    y no en cada prueba del bloque de abajo, porque este es el único
    lugar por el que pasan todas las interacciones. Una traza que
    hubiera que acordarse de escribir es una traza que alguna vez
    falta.

    La invocación es directa y no pasa por ningún reintento. La
    cabecera explica por qué.
    """
    config = {"configurable": {"session_id": session_id}}
    resultado = agente.invoke({"entrada": entrada}, config)

    registrar_traza(session_id, entrada, resultado)

    texto = texto_de_la_respuesta(resultado["output"])
    usadas = tuple(dict.fromkeys(
        accion.tool
        for accion, _ in resultado.get("intermediate_steps", [])
    ))
    return (
        texto,
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

    # return_intermediate_steps tiene que ir en True. Sin eso el
    # resultado no trae los pasos que el agente dio, y la traza
    # quedaría con la pregunta y la respuesta pero sin ninguna de las
    # herramientas que se usaron en medio.
    ejecutor_agente = AgentExecutor(
        agent=agente,
        tools=herramientas,
        verbose=True,
        return_intermediate_steps=True,
    )

    agente_con_memoria = construir_agente_con_memoria(ejecutor_agente)

    def mostrar_turno(entrada: str, sesion: str) -> tuple:
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

    # *** Tercera prueba, los dos niveles de riesgo ***
    #
    # Las dos pruebas de arriba son de la memoria y no tocan la
    # herramienta nueva. Esta prueba los dos niveles de riesgo, con
    # una entrada que dispara una herramienta de cada uno.
    #
    # El primer turno es del lado del trabajador y solo consulta.
    # El segundo es del lado de recursos humanos y encadena dos
    # herramientas, el cálculo de riesgo bajo alimentando al envío
    # de riesgo alto, porque el artículo 162 exige que el aviso
    # indique el monto a pagar.
    titulobn("\n\n*** Tercera prueba, los dos niveles de riesgo ***")
    avisofn(
        "\n  El segundo turno va a pedir una aprobación por consola. "
        "Responde la\n  letra s y Enter para aprobar el envío, o la "
        "letra n para rechazarlo."
    )

    mostrar_turno(
        "¿En qué artículo está regulado el aviso de término de "
        "contrato y con cuánta anticipación hay que darlo?",
        "consulta_004",
    )
    mostrar_turno(
        "Soy del área de recursos humanos. Hay que dar aviso de "
        "término de contrato a Juan Pérez por necesidades de la "
        "empresa. Lleva 5 años y 8 meses y su último sueldo fue de "
        "850000 pesos. No alcanzamos a avisar con treinta días.",
        "rrhh_001",
    )

    notabn(f"\n  decisiones de aprobación registradas   "
           f"{len(registro_aprobaciones)}")
    for decision in registro_aprobaciones:
        notabn(f"    {decision['herramienta']}")
        notabn(f"      aprobado  {decision['aprobado']}")
        notabn(f"      momento   {decision['momento']}")

    notabn(f"\n  las trazas quedaron en {RUTA_TRAZAS.name}, "
           "en esta misma carpeta")

    # El historial se limpia al terminar. Nada lo vacía solo, y un
    # proceso largo acumularía uno por cada sesión que haya visto.
    for sesion in ("consulta_001", "consulta_002", "consulta_003",
                   "consulta_004", "rrhh_001"):
        cerrar_sesion(sesion)
    exitobn(
        f"\n  sesiones cerradas, quedan {len(historiales)} "
        "en memoria"
    )
