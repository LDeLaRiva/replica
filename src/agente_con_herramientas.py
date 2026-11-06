"""Agente con herramientas propias para consultas laborales (Bloque 21).

En el Bloque 19 las rutas estaban programadas de antemano. Ahora no hay
camino fijo. El modelo decide en cada consulta qué herramienta usar, o
si contesta sin usar ninguna.

Las dos son de naturalezas deliberadamente distintas, una busca y la
otra calcula, para que no compitan por la misma pregunta. La actividad
advierte que dos herramientas parecidas producen una elección
inconsistente.

    buscar_articulo_del_codigo
        dice en qué artículo está regulado un tema y entrega su texto
    calcular_indemnizacion_anos_servicio
        calcula el monto del artículo 163 con reglas programadas

El cálculo se hace en Python y no en el modelo, como quedó establecido
en la declaración del proyecto del Módulo 1.

El texto de los artículos 66, 160, 161, 163 y 177 viene del Código del
Trabajo que publica la Biblioteca del Congreso Nacional. Va literal,
con los incisos separados y numerados entre corchetes, y no resumido,
porque un resumen aplana la estructura y los artículos se remiten a
sus propios incisos. Sobre un texto plano esas remisiones quedan sin
referente. Lo que aparece entre [nota: ...] es agregado de este
proyecto y no texto legal, y resuelve justamente esas remisiones. Las
reglas de cálculo se contrastaron además con dos consultas de la
Dirección del Trabajo.

Los tres pasos que pide la actividad están en las dos herramientas con
@tool, en el AgentExecutor del bloque __main__ con
return_intermediate_steps=True, y en CASOS, que trae cuatro
comprobaciones donde el mínimo son dos. El tercer caso es el que
confirma que el agente no invoca herramienta cuando no corresponde, y
el manejo de error dentro de la herramienta está en el try/except del
cálculo y en el retorno sin excepción de la búsqueda.

Hay cuatro cosas que la actividad no pide y que se agregan.
texto_de_la_respuesta existe porque los modelos Gemini 3.x devuelven
una lista de bloques donde la lección supone un string, y sin eso la
salida queda ilegible. invocar_con_reintento y el try/except del bucle
traen el patrón del Bloque 20 al bucle de casos, porque un 503 del
proveedor interrumpía la verificación y dejaba los casos siguientes
sin correr. El modelo se lee de AI_MODEL en vez de ir fijo. Y la
elección de herramienta se confirma con un recuento en lugar del
assert del ejemplo, porque un assert corta en el primer fallo y los
casos siguientes quedarían sin verificar.

El registro de las ejecuciones y de las conductas observadas del
modelo está en docs/limites_bloque21.md, fechado y referido a cada
ejecución.
"""

import logging
import os
import textwrap
import time
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

# A nivel de módulo y sin configurar nada, igual que en
# enrutamiento.py. Pedir el logger no tiene efectos, así que importar
# este archivo no le cambia el logging a quien lo importe. La
# configuración vive en el bloque de abajo, que solo corre cuando se
# ejecuta este archivo directamente.
logger = logging.getLogger(__name__)

# Espera previa al único reintento. Veinte segundos, porque un 503
# UNAVAILABLE responde a una saturación momentánea del proveedor.
ESPERA_REINTENTO = 20


def invocar_con_reintento(ejecutor, entrada, espera=ESPERA_REINTENTO):
    """Invoca el agente y reintenta una vez si la primera falla.

    Un 503 UNAVAILABLE del proveedor indica saturación momentánea
    del servicio. No es agotamiento de cuota, que se reporta como 429
    RESOURCE_EXHAUSTED, ni error en la solicitud. Sin reintento, ese
    fallo interrumpe la verificación completa.

    Se reintenta una sola vez. Un error de autenticación o una
    solicitud mal formada no se resuelven reintentando, y un
    reintento en bucle consumiría llamadas sin resultado. Si la
    segunda invocación también falla, la excepción se propaga y la
    resuelve quien llamó.

    El manejo no oculta el error. logger.exception registra el
    traceback completo, de modo que la causa queda visible, con la
    diferencia de que el programa sigue.
    """
    try:
        return ejecutor.invoke({"entrada": entrada})
    except Exception:
        logger.exception(
            "Falló la invocación del agente, se reintenta una vez "
            "en %s segundos", espera
        )
        time.sleep(espera)
        return ejecutor.invoke({"entrada": entrada})


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
    la misma trampa de las categorías del Bloque 19, y aquí tiene
    más efecto, porque las personas escriben con tilde y a veces
    sin ella.
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
# El texto de cada artículo va literal, copiado del Código del
# Trabajo que publica la Biblioteca del Congreso Nacional, con los
# incisos separados por salto de línea y numerados entre corchetes.
#
# No va resumido, y la razón es concreta. Un resumen aplana la
# estructura del artículo, y los artículos se refieren a su propia
# estructura. El 66 dice "el trabajador al que se refiere el inciso
# primero gozará de fuero laboral", y sobre un texto plano eso queda
# apuntando a nada, así que el modelo lo resolvía suponiendo. Atribuyó
# el fuero solo a la muerte del hijo, cuando el inciso primero cubre
# también a la del cónyuge o conviviente civil.
#
# El 160 no lleva corchetes porque el artículo se numera solo, del
# 1.- al 7.-, y esa numeración es la que hay que conservar.
#
# Del 177 va solo el inciso primero, que es el que trae el plazo de
# diez días hábiles. El artículo sigue con doce incisos de
# procedimiento, y van anunciados en una línea para que el inciso
# primero no se lea como si fuera el artículo completo.
#
# Lo que va entre [nota: ...] es anotación de este proyecto y no
# texto legal. Son cinco y resuelven las remisiones que un artículo
# hace a sus propios incisos, una en el 66, una en el 161 y tres en
# el 163.
#
# Se insertan dentro de la oración y no como nota al margen. Si el
# modelo reproduce la oración, la aclaración va incorporada y no
# puede quedar atrás. Así la respuesta tampoco llega al destinatario
# con la expresión "el trabajador del inciso primero", que carece de
# referente para quien no tiene el artículo a la vista.
#
# No se tocaron las referencias que no son ambiguas. "Este artículo"
# y "el presente artículo" se explican solos, y las que dicen "el
# inciso segundo del artículo 161" ya traen el número del artículo.
ARTICULOS = (
    (
        ("fallecimiento", "muerte", "luto", "duelo"),
        "[1] Artículo 66.- En caso de muerte de un hijo, todo "
        "trabajador tendrá derecho a diez días corridos de permiso "
        "pagado. En caso de la muerte del cónyuge o conviviente "
        "civil, todo trabajador tendrá derecho a un permiso "
        "similar, por siete días corridos. En ambos casos, este "
        "permiso será adicional al feriado anual, "
        "independientemente del tiempo de servicio.\n"
        "[2] Igual permiso se aplicará, por siete días hábiles, en "
        "el caso de muerte de un hijo en período de gestación. En "
        "el caso de muerte de un hermano, del padre o de la madre "
        "del trabajador, dicho permiso se extenderá por cuatro días "
        "hábiles.\n"
        "[3] Estos permisos deberán hacerse efectivos a partir del "
        "día del respectivo fallecimiento. No obstante, tratándose "
        "de una defunción fetal, el permiso se hará efectivo desde "
        "el momento de acreditarse la muerte, con el respectivo "
        "certificado de defunción fetal.\n"
        "[4] El trabajador al que se refiere el inciso primero "
        "[nota: es el inciso 1, es decir quien sufre la muerte de un "
        "hijo o la del cónyuge o conviviente civil] "
        "gozará de fuero laboral por el periodo de un mes a partir "
        "del día del respectivo fallecimiento. Si se trata de "
        "trabajadores cuyos contratos de trabajo sean a plazo fijo, "
        "o por obra o servicio determinado, el fuero establecido en "
        "el presente artículo se mantendrá vigente por el mismo "
        "periodo o hasta el término de dicho contrato.\n"
        "[5] Los días de permiso consagrados en este artículo no "
        "podrán ser compensados en dinero."
    ),
    (
        ("probidad", "acoso", "abandono", "incumplimiento grave",
         "sin derecho a indemnizacion"),
        "Art. 160. El contrato de trabajo termina sin derecho a "
        "indemnización alguna cuando el empleador le ponga término "
        "invocando una o más de las siguientes causales:\n"
        "1.- Alguna de las conductas indebidas de carácter grave, "
        "debidamente comprobadas, que a continuación se señalan:\n"
        "a) Falta de probidad del trabajador en el desempeño de sus "
        "funciones;\n"
        "b) Conductas de acoso sexual;\n"
        "c) Vías de hecho ejercidas por el trabajador en contra del "
        "empleador o de cualquier trabajador que se desempeñe en la "
        "misma empresa;\n"
        "d) Injurias proferidas por el trabajador al empleador;\n"
        "e) Conducta inmoral del trabajador que afecte a la empresa "
        "donde se desempeña, y\n"
        "f) Conductas de acoso laboral.\n"
        "2.- Negociaciones que ejecute el trabajador dentro del "
        "giro del negocio y que hubieren sido prohibidas por "
        "escrito en el respectivo contrato por el empleador.\n"
        "3.- No concurrencia del trabajador a sus labores sin causa "
        "justificada durante dos días seguidos, dos lunes en el mes "
        "o un total de tres días durante igual período de tiempo; "
        "asimismo, la falta injustificada, o sin aviso previo de "
        "parte del trabajador que tuviere a su cargo una actividad, "
        "faena o máquina cuyo abandono o paralización signifique "
        "una perturbación grave en la marcha de la obra.\n"
        "4.- Abandono del trabajo por parte del trabajador, "
        "entendiéndose por tal:\n"
        "a) la salida intempestiva e injustificada del trabajador "
        "del sitio de la faena y durante las horas de trabajo, sin "
        "permiso del empleador o de quien lo represente, y\n"
        "b) la negativa a trabajar sin causa justificada en las "
        "faenas convenidas en el contrato.\n"
        "5.- Actos, omisiones o imprudencias temerarias que afecten "
        "a la seguridad o al funcionamiento del establecimiento, a "
        "la seguridad o a la actividad de los trabajadores, o a la "
        "salud de éstos.\n"
        "6.- El perjuicio material causado intencionalmente en las "
        "instalaciones, maquinarias, herramientas, útiles de "
        "trabajo, productos o mercaderías.\n"
        "7.- Incumplimiento grave de las obligaciones que impone el "
        "contrato."
    ),
    (
        ("necesidades de la empresa", "desahucio", "despid"),
        "[1] Art. 161. Sin perjuicio de lo señalado en los "
        "artículos precedentes, el empleador podrá poner término al "
        "contrato de trabajo invocando como causal las necesidades "
        "de la empresa, establecimiento o servicio, tales como las "
        "derivadas de la racionalización o modernización de los "
        "mismos, bajas en la productividad, cambios en las "
        "condiciones del mercado o de la economía, que hagan "
        "necesaria la separación de uno o más trabajadores. La "
        "eventual impugnación de las causales señaladas, se regirá "
        "por lo dispuesto en el artículo 168.\n"
        "[2] En el caso de los trabajadores que tengan poder para "
        "representar al empleador, tales como gerentes, "
        "subgerentes, agentes o apoderados, siempre que, en todos "
        "estos casos, estén dotados, a lo menos, de facultades "
        "generales de administración, y en el caso de los "
        "trabajadores de casa particular, el contrato de trabajo "
        "podrá, además, terminar por desahucio escrito del "
        "empleador, el que deberá darse con treinta días de "
        "anticipación, a lo menos, con copia a la Inspección del "
        "Trabajo respectiva. Sin embargo, no se requerirá esta "
        "anticipación cuando el empleador pagare al trabajador, al "
        "momento de la terminación, una indemnización en dinero "
        "efectivo equivalente a la última remuneración mensual "
        "devengada. Regirá también esta norma tratándose de cargos "
        "o empleos de la exclusiva confianza del empleador, cuyo "
        "carácter de tales emane de la naturaleza de los mismos.\n"
        "[3] Las causales señaladas en los incisos anteriores "
        "[nota: son el inciso 1, necesidades de la empresa, y el "
        "inciso 2, desahucio] no "
        "podrán ser invocadas con respecto a trabajadores que gocen "
        "de licencia por enfermedad común, accidente del trabajo o "
        "enfermedad profesional, otorgada en conformidad a las "
        "normas legales vigentes que regulan la materia."
    ),
    (
        ("indemnizacion", "anos de servicio", "años de servicio"),
        "[1] Art. 163. Si el contrato hubiere estado vigente un año "
        "o más y el empleador le pusiere término en conformidad al "
        "artículo 161, deberá pagar al trabajador, la indemnización "
        "por años de servicio que las partes hayan convenido "
        "individual o colectivamente, siempre que ésta fuere de un "
        "monto superior a la establecida en el inciso siguiente "
        "[nota: es el inciso 2, la indemnización legal de treinta "
        "días de la última remuneración por año de servicio].\n"
        "[2] A falta de esta estipulación, entendiéndose además por "
        "tal la que no cumpla con el requisito señalado en el "
        "inciso precedente [nota: es el inciso 1, que exige que lo "
        "pactado sea de un monto superior], el empleador deberá "
        "pagar al trabajador "
        "una indemnización equivalente a treinta días de la última "
        "remuneración mensual devengada por cada año de servicio y "
        "fracción superior a seis meses, prestados continuamente a "
        "dicho empleador. Esta indemnización tendrá un límite "
        "máximo de trescientos treinta días de remuneración.\n"
        "[3] Si el contrato celebrado para una obra o faena "
        "determinada hubiere estado vigente por un mes o más, el "
        "empleador podrá ponerle término en forma justificada en "
        "tanto pague al trabajador, en el momento de su "
        "terminación, una indemnización equivalente a dos y medio "
        "días de remuneración por cada mes trabajado y fracción "
        "superior a quince días, en la forma y modalidad señalada "
        "en el artículo 23 transitorio de este Código. Esta "
        "indemnización será calculada en conformidad a lo "
        "establecido en el artículo 172, y le será aplicable lo "
        "dispuesto en el inciso segundo del artículo 13 de la ley "
        "N° 19.728. Sólo corresponderá el pago de la prestación "
        "antes señalada, si se pusiere término al contrato por la "
        "causal contemplada en el número 5 del artículo 159. El "
        "ejercicio del derecho establecido en este inciso por parte "
        "del trabajador es incompatible con las acciones derivadas "
        "de la aplicación del inciso primero del artículo 168, sin "
        "perjuicio de las acciones señaladas en el artículo 485 de "
        "este Código.\n"
        "[4] La indemnización a que se refiere este artículo será "
        "compatible con la sustitutiva del aviso previo que "
        "corresponda al trabajador, según lo establecido en el "
        "inciso segundo del artículo 161 y en el inciso cuarto del "
        "artículo 162 de este Código.\n"
        "[5] Lo dispuesto en los incisos anteriores "
        "[nota: son los incisos 1 a 4, la indemnización común] "
        "no se aplicará "
        "en el caso de terminación del contrato de los trabajadores "
        "de casa particular, respecto de los cuales regirán las "
        "siguientes normas:\n"
        "a) Tendrán derecho, cualquiera que sea la causa que "
        "origine la terminación del contrato, a una indemnización a "
        "todo evento que se financiará con un aporte del empleador, "
        "equivalente al 1,11% de la remuneración mensual imponible, "
        "la que se regirá, en cuanto corresponda, por las "
        "disposiciones de los artículos 165 y 166 de este Código, y\n"
        "b) La obligación de efectuar el aporte tendrá una duración "
        "de once años en relación con cada trabajador, plazo que se "
        "contará desde el 1º de enero de 1991, o desde la fecha de "
        "inicio de la relación laboral, si ésta fuere posterior. El "
        "monto de la indemnización quedará determinado por los "
        "aportes correspondientes al período respectivo, más la "
        "rentabilidad que se haya obtenido de ellos."
    ),
    (
        ("finiquito",),
        "[1] Art. 177. El finiquito, la renuncia y el mutuo acuerdo "
        "deberán constar por escrito. El instrumento respectivo que "
        "no fuere firmado por el interesado y por el presidente del "
        "sindicato o el delegado sindical respectivos, o que no "
        "fuere ratificado por el trabajador ante el inspector del "
        "trabajo, no podrá ser invocado por el empleador. El "
        "finiquito deberá ser otorgado por el empleador y puesto su "
        "pago a disposición del trabajador dentro de diez días "
        "hábiles, contados desde la separación del trabajador. Las "
        "partes podrán pactar el pago en cuotas de conformidad con "
        "los artículos 63 bis y 169.\n"
        "[nota: el artículo continúa con doce incisos más, que "
        "regulan quiénes pueden actuar como ministro de fe, el "
        "finiquito electrónico ante la Dirección del Trabajo, la "
        "reserva de derechos y la acreditación del pago de las "
        "cotizaciones]"
    ),
)


@tool
def buscar_articulo_del_codigo(consulta: str) -> str:
    """Indica en qué artículo del Código del Trabajo chileno está
    regulado un tema y entrega el texto de ese artículo.

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

    # El encabezado va una vez por respuesta y no una vez por
    # artículo, para no repetirlo cuando calcen varios.
    return (
        "Texto del Código del Trabajo de Chile. Los números entre "
        "corchetes marcan los incisos del artículo.\n\n"
        + "\n\n".join(encontrados)
    )


@tool
def calcular_indemnizacion_anos_servicio(
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

    horas_semanales es opcional. Pásalo solo si la persona menciona su
    jornada, porque las de treinta horas o menos se rigen además por
    el artículo 40 bis D y la respuesta cambia. Si no la menciona,
    déjalo en cero y no inventes un valor.
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
    # necesita el historial del IPC de hasta once años. Pero el mismo artículo
    # cierra diciendo que si la del 163 resulta superior se aplica
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
    buscar_articulo_del_codigo,
    calcular_indemnizacion_anos_servicio,
]


# Sobre la frase "di cuál es y qué establece en lo que viene al
# caso". Corresponde al cambio de ARTICULOS a texto literal, que hizo
# que la herramienta devolviera prosa legal en lugar de prosa simple.
#
# Pide las dos cosas, cuál es el artículo y qué establece, y acota el
# alcance con "en lo que viene al caso". Una instrucción que solo
# prohibiera transcribir deja al modelo respondiendo de forma
# literal, y una entrada de una sola parte, como "¿en qué artículo
# está el permiso por fallecimiento?", admite entonces una respuesta
# de una línea que omite los plazos.
#
# El control sobre las cifras lo ejerce la frase anterior, la que
# manda repetirlas tal como llegaron.
#
# No se pide que explique el artículo en palabras simples, porque esa
# instrucción equivale a reescribirlo completo. Una paráfrasis por
# respuesta queda visible en la traza y no se acumula, a diferencia
# de un resumen fijado en el corpus, que se reutiliza en todas las
# consultas sin quedar a la vista.
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
        "Cuando respondas sobre un artículo, di cuál es y qué "
        "establece en lo que viene al caso, con los plazos y las "
        "cifras que trae. No transcribas el artículo completo. "
        "Escribe en texto plano, sin markdown ni asteriscos. Si "
        "enumeras, usa un guion al inicio de cada línea.",
    ),
    ("human", "{entrada}"),
    MessagesPlaceholder("agent_scratchpad"),
])


# Las comprobaciones manuales del Paso 3. Cada caso son las
# herramientas que el agente debería elegir y la entrada que las
# dispara. La actividad exige dos como mínimo y se incluyen cuatro.
#
# Las dos primeras prueban una ruta cada una. La tercera espera que no
# use ninguna, que es el caso que la lección pide confirmar aparte. La
# cuarta prueba que sepa encadenar las dos, que es la sección "cuando
# el agente encadena más de una herramienta" de la lección anterior.
#
# El segundo y el cuarto usan la misma herramienta de cálculo, pero
# entran por ramas distintas. El segundo menciona la jornada, así que
# el agente tiene que pasar horas_semanales y la herramienta responde
# por el artículo 40 bis D. El cuarto no la menciona, así que entra
# por la rama de jornada completa. Eso cubre las dos salidas del
# cálculo sin agregar un quinto caso.
#
# Ojo con qué alcanza a verificar la aserción de abajo. Compara
# nombres de herramientas, no argumentos, así que el segundo caso
# pasaría igual si el agente llamara al cálculo olvidando la jornada.
# Lo que confirma que la pasó es la traza, donde sale el argumento
# tal cual lo armó el modelo.
CASOS = (
    (
        ("buscar_articulo_del_codigo",),
        "¿En qué artículo del Código del Trabajo está el permiso por "
        "fallecimiento de un familiar?",
    ),
    (
        ("calcular_indemnizacion_anos_servicio",),
        "Me despidieron por necesidades de la empresa después de 5 "
        "años y 8 meses, mi último sueldo fue de 500000 pesos y mi "
        "jornada es part time, de 20 horas semanales. ¿Cuánto me "
        "corresponde de indemnización?",
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

    # Lo mismo que en enrutamiento.py y por lo mismo. force=True
    # porque las librerías de Google instalan su propio handler al
    # importarse, y sin force basicConfig no hace nada. Después se
    # bajan por nombre las dos que inundan la consola, para que los
    # logger.exception de este módulo se alcancen a leer.
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

    # verbose imprime la traza mientras ocurre.
    # return_intermediate_steps la deja además disponible en el
    # resultado, que es lo que pide la actividad para poder verificar.
    #
    # max_iterations se deja en su valor por defecto, que son quince.
    # Una iteración es una vuelta de elegir y llamar una herramienta,
    # y las consultas de este módulo usan cero, una o dos, así que el tope
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
    fallidos = 0
    for esperadas, entrada in CASOS:
        titulofn(f"\n\n  entrada")
        notabn(f"\n{entrada}\n")

        # Patrón de manejo de error del Bloque 20 aplicado al bucle.
        # Sin él, un fallo del proveedor en un caso interrumpe el
        # script completo, los casos siguientes no se ejecutan y las
        # llamadas ya consumidas quedan sin verificación. Con él, el
        # caso que falla queda registrado con su traceback y los
        # demás continúan.
        try:
            resultado = invocar_con_reintento(
                ejecutor_agente, entrada
            )
        except Exception:
            logger.exception("El caso quedó sin resultado")
            avisofn(
                "\n  este caso no se pudo ejecutar, el error "
                "completo quedó impreso arriba"
            )
            fallidos += 1
            continue

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

    # El denominador son los casos que de verdad corrieron, no los que
    # había. Decir 2/4 cuando dos murieron por un 503 daría a entender
    # que el agente eligió mal dos veces, y no fue eso lo que pasó.
    # Los que no corrieron se informan aparte.
    total = len(CASOS)
    corridos = total - fallidos
    if not corridos:
        avisofn(
            f"\n\n  ninguno de los {total} casos se pudo ejecutar, "
            "los errores quedaron impresos arriba"
        )
    elif fallidos:
        avisofn(
            f"\n\n  {aciertos}/{corridos} eligió bien, y {fallidos} "
            f"de {total} no se pudieron ejecutar"
        )
    elif aciertos == corridos:
        exitobn(f"\n\n  {aciertos}/{corridos} eligió bien")
    else:
        avisofn(f"\n\n  {aciertos}/{corridos} eligió bien")
