"""Enrutamiento condicional de la miniaplicación de consultas laborales.

La cadena del Bloque 18 hacía siempre los mismos tres pasos. aquí la
entrada decide el camino. Un paso de clasificación mira qué llegó, y la
bifurcación manda ese texto a la ruta que corresponde.

Las cuatro rutas son

    consulta   una pregunta escrita por una persona
    clausula   un trozo suelto de un contrato de trabajo
    contrato   un contrato de trabajo completo
    ley        el texto de un artículo de una ley

Son cuatro y no tres como el ejemplo de la lección, que propone
agregar una cuarta categoría como ejercicio de cierre del Bloque 19.

consulta es la ruta por defecto. Si la clasificación devuelve algo que
ninguna condición reconoce, la entrada cae ahí sin lanzar error. Se
eligió esa porque las otras tres suponen que llegó un documento, y sin
documento responderían sobre algo que no está.

El Bloque 20 agrega dos redes de seguridad, de distinto alcance.

    with_fallbacks   protege una ruta puntual, aquí la de consulta
    try/except       protege el flujo completo, pase lo que pase

Las dos dejan registro con logger antes de responder. Un fallo que se
atiende sin anotarse en ninguna parte es un fallo que nadie va a
encontrar después.

Las plantillas quedan en el módulo porque no necesitan el modelo. Todo
lo que sí lo necesita vive en el bloque de main, con el mismo criterio
del Bloque 18. Así pytest importa este archivo sin clave y sin gastar
ninguna llamada.
"""

import logging
import os
import textwrap

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)


# getLogger solo crea el objeto, no configura nada ni imprime. La
# configuración va en el bloque de main, para que importar este archivo
# siga sin tener efectos.
logger = logging.getLogger(__name__)


# Las cuatro categorías van sin tilde a propósito. El .strip().lower()
# de más abajo limpia espacios y mayúsculas, pero no saca tildes, así
# que "Cláusula" nunca coincidiría con "clausula" y la entrada se iría
# a la ruta por defecto sin avisar.
plantilla_clasificacion = PromptTemplate.from_template(
    "Clasifica la siguiente entrada en una sola palabra. "
    "consulta si es una pregunta escrita por una persona. "
    "clausula si es un trozo suelto de un contrato de trabajo. "
    "contrato si es un contrato de trabajo completo. "
    "ley si es el texto de un articulo de una ley. "
    "Responde solo con esa palabra, sin tilde y sin punto final."
    "\n\n{mensaje}"
)

plantilla_consulta = PromptTemplate.from_template(
    "Eres un asistente de consultas laborales de Chile. "
    "Responde la siguiente consulta en tres oraciones como máximo, "
    "solo lo que se pregunta, sin agregar información que no se "
    "haya pedido. Básate únicamente en el Código del Trabajo "
    "chileno y en los dictámenes de la Dirección del Trabajo. "
    "Indica la fuente exacta, por ejemplo Código del Trabajo "
    "artículo 67 o Dictamen 5641/2015 de la Dirección del Trabajo. "
    "Si no estás seguro de un dato o no puedes identificar la "
    "fuente, di que no lo sabes en lugar de suponerlo. "
    "Escribe en texto plano, sin markdown ni asteriscos."
    "\n\n{mensaje}"
)

plantilla_clausula = PromptTemplate.from_template(
    "Eres un asistente de consultas laborales de Chile. "
    "Lee la siguiente cláusula de un contrato de trabajo e indica "
    "qué materia regula y qué cantidad fija. No opines si cumple o "
    "no la ley, esa comparación la hace el programa. "
    "Escribe en texto plano, sin markdown ni asteriscos. Si "
    "enumeras, usa un guion al inicio de cada línea."
    "\n\n{mensaje}"
)

plantilla_contrato = PromptTemplate.from_template(
    "Eres un asistente de consultas laborales de Chile. "
    "Lee el siguiente contrato de trabajo y enumera la fecha de "
    "inicio, el cargo, la jornada, la remuneración y el plazo. "
    "Usa solo lo que aparece en el texto. "
    "Si un dato no aparece, dilo. "
    "Escribe en texto plano, sin markdown ni asteriscos. Si "
    "enumeras, usa un guion al inicio de cada línea."
    "\n\n{mensaje}"
)

plantilla_ley = PromptTemplate.from_template(
    "Eres un asistente de consultas laborales de Chile. "
    "Explica el siguiente texto legal en palabras simples, para una "
    "persona sin formación jurídica. Usa solo lo que aparece en el "
    "texto, sin agregar nada que no esté en él. "
    "Escribe en texto plano, sin markdown ni asteriscos. Si "
    "enumeras, usa un guion al inicio de cada línea."
    "\n\n{mensaje}"
)


# Los dos textos de emergencia. Son distintos a propósito. El primero
# es para cuando la ruta de consulta falló, o sea el flujo llegó a
# responder y no pudo. El segundo es para cuando falló cualquier otra
# cosa y ni siquiera se alcanzó a elegir una ruta.
#
# Ninguno de los dos se parece a una respuesta legal, y ninguno promete
# que alguien va a contestar después. Decir que no se pudo es honesto.
# Insinuar que la consulta quedó registrada no lo sería.
#
# Empiezan con palabras distintas a propósito, para que se vea de un
# vistazo cuál de las dos redes actuó sin tener que compararlos letra
# por letra.
#
# Las pruebas buscan "responder tu consulta" y "procesar tu mensaje".
# Esas dos frases son lo único que no se puede tocar sin actualizar
# también los assert de test_orquestacion.py. El resto del texto se
# puede reescribir libremente.
MENSAJE_RESPALDO = (
    "Tuvimos un problema al responder tu consulta. Inténtalo "
    "nuevamente en unos minutos. Si es urgente, puedes consultar "
    "directamente en la Dirección del Trabajo."
)

MENSAJE_SEGURO = (
    "No podemos procesar tu mensaje en este momento. Inténtalo "
    "nuevamente en unos minutos. Si es urgente, puedes consultar "
    "directamente en la Dirección del Trabajo."
)


def avisar_y_responder(entrada):
    """Devuelve el texto de respaldo, y antes deja registro.

    El argumento llega porque with_fallbacks le pasa la misma entrada
    que recibió la ruta que falló. aquí no se usa, el texto es fijo.

    La línea del logger es el motivo de que esto sea una función y no
    una lambda que solo devuelve texto. with_fallbacks atrapa la
    excepción por su cuenta y no anota nada, así que sin esta línea el
    fallo quedaría invisible. El Bloque 20 insiste en que manejar un
    error no es lo mismo que taparlo.
    """
    logger.error(
        "La ruta de consulta falló, se entregó la respuesta de respaldo"
    )
    return MENSAJE_RESPALDO


respuesta_generica = RunnableLambda(avisar_y_responder)


def construir_paso_clasificacion(modelo):
    """Arma el paso que decide la categoría de la entrada.

    Es igual a cualquier otro paso del Bloque 18, una plantilla, el
    modelo y el parser. Lo que cambia es para qué se usa su salida.

    El lambda del final limpia el texto antes de que las condiciones de
    la bifurcación lo comparen. Sin él, un "Consulta " con mayúscula y
    espacio no coincide con "consulta" y la entrada se va a la ruta por
    defecto en silencio, sin ningún error que avise.
    """
    return (
        plantilla_clasificacion
        | modelo
        | StrOutputParser()
        | (lambda texto: texto.strip().lower())
    )


def construir_cadena_consulta_segura(cadena_consulta):
    """Envuelve la ruta de consulta con su respuesta de respaldo.

    Si la ruta falla, LangChain ejecuta respuesta_generica en su lugar
    y quien llamó recibe un texto útil, no una excepción.

    Se protege esta ruta y no las otras tres por dos razones. Es la
    ruta por defecto, así que recibe todo lo que no se clasificó. Y es
    la única que responde sin un documento delante, de modo que si se
    cae, la persona queda sin nada.

    Las otras tres quedan cubiertas por el try/except de
    procesar_mensaje_seguro, que es lo que el checklist del Bloque 20
    permite cuando dice "su propio with_fallbacks o el try/except
    general".

    Va un solo respaldo, y no el de dos niveles que muestra la lección,
    que antes del texto fijo reintenta con un modelo más simple. En una
    mesa de soporte ese segundo intento es mejor que un texto fijo. aquí
    no. Esta ruta responde de memoria, sin documento delante, y un
    modelo más chico contestando sobre la ley inventa más. Una
    respuesta legal equivocada hace más daño que decir que no se pudo.

    Si algún día se quiere el respaldo con modelo secundario, el lugar
    son las rutas de clausula, contrato y ley, que leen un texto que ya
    les llegó y no dependen de lo que el modelo recuerde.
    """
    return cadena_consulta.with_fallbacks([respuesta_generica])


def construir_cadena_con_enrutamiento(
    paso_clasificacion,
    cadena_clausula=None,
    cadena_contrato=None,
    cadena_ley=None,
    cadena_consulta=None,
):
    """Conecta la clasificación con las cuatro rutas.

    Cada ruta que no se reciba se reemplaza por un RunnablePassthrough,
    que no se ejecuta si la bifurcación no la elige. Por eso en las
    pruebas alcanza con pasar la ruta que se quiere verificar.

    RunnablePassthrough.assign agrega la clave categoria al diccionario
    de entrada sin descartar las que ya traía. Eso importa porque cada ruta
    usa el {mensaje} original en su propio prompt.

    RunnableBranch evalúa las condiciones de arriba hacia abajo y se
    queda con la primera verdadera. La última, sin condición, es la
    ruta por defecto.
    """
    cadena_clausula = cadena_clausula or RunnablePassthrough()
    cadena_contrato = cadena_contrato or RunnablePassthrough()
    cadena_ley = cadena_ley or RunnablePassthrough()
    cadena_consulta = cadena_consulta or RunnablePassthrough()

    bifurcacion = RunnableBranch(
        (lambda x: x["categoria"] == "clausula", cadena_clausula),
        (lambda x: x["categoria"] == "contrato", cadena_contrato),
        (lambda x: x["categoria"] == "ley", cadena_ley),
        cadena_consulta,
    )

    return (
        RunnablePassthrough.assign(categoria=paso_clasificacion)
        | bifurcacion
    )


def procesar_mensaje_seguro(cadena, mensaje):
    """Punto de entrada. Garantiza que siempre salga una respuesta.

    Recibe la cadena como parámetro y no la lee del módulo, para que
    una prueba pueda inyectar una cadena falsa. Es el mismo criterio de
    construir_cadena_con_enrutamiento.

    El except es ancho a propósito. aquí el objetivo no es distinguir
    tipos de error como en el cliente del Módulo 2, es que ningún fallo
    deje a la persona sin ninguna respuesta.

    Ancho no quiere decir mudo. El logger registra el error real antes
    de devolver el texto, porque si no, este try/except estaría
    escondiendo el problema en vez de manejarlo.

    Se usa exception y no error. El ejemplo de la lección muestra
    error, pero su propio troubleshooting recomienda cambiarlo por
    exception cuando el try/except pueda estar tapando el error real,
    porque guarda además el camino completo hasta la línea que falló.

    Con seis piezas en la cadena, saber cuál se cayó vale más que
    saber que algo se cayó. Un KeyError, por ejemplo, con error se
    registra como 'mensaje' a secas, y así no se encuentra nunca.

    La persona recibe exactamente el mismo texto. El detalle va al
    registro, no a la respuesta.
    """
    try:
        return cadena.invoke({"mensaje": mensaje})
    except Exception as error:
        logger.exception(f"Error procesando mensaje: {error}")
        return MENSAJE_SEGURO


# Banco para la revisión manual que pide la primera pregunta del
# checklist de cierre. Dos entradas por categoría, con la categoría que
# debería salir anotada al lado. Sobre cada una se corre solo la
# clasificación, que es una llamada por mensaje.
BANCO_DE_MENSAJES = [
    (
        "consulta",
        "Hola, falleció mi hermano el jueves. Mi jefe me dijo que me "
        "tocan tres días y una compañera me dijo que cuatro. "
        "¿Cuántos días me corresponden?",
    ),
    (
        "consulta",
        "¿En qué plazo debe el empleador pagar el finiquito?",
    ),
    (
        "clausula",
        "La jornada ordinaria de trabajo será de 48 horas semanales, "
        "distribuidas en seis días.",
    ),
    (
        "clausula",
        "El trabajador percibirá una remuneración mensual bruta de "
        "$650.000, pagadera el último día hábil de cada mes.",
    ),
    (
        "contrato",
        "CONTRATO DE TRABAJO. Entre Comercial Andes Limitada, RUT "
        "76.123.456-7, en adelante el empleador, y don Juan Pérez "
        "Soto, RUT 15.987.654-3, en adelante el trabajador, se "
        "celebra el siguiente contrato. PRIMERO. El trabajador se "
        "desempeñará como vendedor en el local de Avenida "
        "Providencia 1234, comuna de Providencia. SEGUNDO. La "
        "jornada será de 42 horas semanales. TERCERO. La "
        "remuneración mensual será de $650.000. CUARTO. El presente "
        "contrato rige a contar del 3 de marzo de 2025 y es de plazo "
        "indefinido.",
    ),
    (
        "contrato",
        "CONTRATO DE TRABAJO A PLAZO FIJO. En Santiago, a 2 de enero "
        "de 2026, entre Servicios Austral SpA y doña Marta Rojas "
        "Díaz se conviene lo siguiente. PRIMERO. La trabajadora "
        "prestará servicios como asistente administrativa. SEGUNDO. "
        "La jornada será de 30 horas semanales de lunes a viernes. "
        "TERCERO. La remuneración será de $480.000 mensuales. "
        "CUARTO. El contrato vence el 30 de junio de 2026.",
    ),
    (
        # Texto literal del artículo, tomado del corpus. No se
        # resume ni se parafrasea, porque la ruta ley lo recibe tal
        # cual y lo tiene que explicar.
        "ley",
        "Artículo 66.- En caso de muerte de un hijo, todo trabajador "
        "tendrá derecho a diez días corridos de permiso pagado. En "
        "caso de la muerte del cónyuge o conviviente civil, todo "
        "trabajador tendrá derecho a un permiso similar, por siete "
        "días corridos. En ambos casos, este permiso será adicional "
        "al feriado anual, independientemente del tiempo de "
        "servicio. Igual permiso se aplicará, por siete días "
        "hábiles, en el caso de muerte de un hijo en período de "
        "gestación. En el caso de muerte de un hermano, del padre o "
        "de la madre del trabajador, dicho permiso se extenderá por "
        "cuatro días hábiles. Estos permisos deberán hacerse "
        "efectivos a partir del día del respectivo fallecimiento. "
        "No obstante, tratándose de una defunción fetal, el permiso "
        "se hará efectivo desde el momento de acreditarse la "
        "muerte, con el respectivo certificado de defunción fetal. "
        "El trabajador al que se refiere el inciso primero gozará "
        "de fuero laboral por el periodo de un mes a partir del día "
        "del respectivo fallecimiento. Si se trata de trabajadores "
        "cuyos contratos de trabajo sean a plazo fijo, o por obra o "
        "servicio determinado, el fuero establecido en el presente "
        "artículo se mantendrá vigente por el mismo periodo o hasta "
        "el término de dicho contrato. Los días de permiso "
        "consagrados en este artículo no podrán ser compensados en "
        "dinero.",
    ),
    (
        "ley",
        "Artículo 177. El finiquito deberá ser otorgado por el "
        "empleador y puesto su pago a disposición del trabajador "
        "dentro de diez días hábiles contados desde la separación "
        "del trabajador.",
    ),
]


if __name__ == "__main__":
    from contraste import *                               # noqa: F403

    # basicConfig toca el registro global, así que se llama aquí y no
    # arriba. Al importar el archivo desde pytest no se configura nada,
    # y el logger igual avisa, porque Python manda los mensajes de
    # nivel ERROR a la salida de errores aunque nadie lo configure.
    #
    # Va en WARNING y no en INFO como el ejemplo de la lección, porque
    # el nivel es global. En INFO, httpx y google_genai narran cada
    # llamada y ensucian la salida hasta dejarla ilegible. aquí solo se
    # registra con logger.error, que es más alto que WARNING, así que
    # no se pierde ningun aviso del módulo.
    #
    # Lleva force porque basicConfig no hace nada, y sin avisar, si el
    # registro ya tiene un manejador puesto. Las librerías de Google lo
    # ponen al importarse, o sea antes de que se llegue aquí.
    logging.basicConfig(level=logging.WARNING, force=True)

    # Y además hay que bajárselo a cada una por su nombre, porque
    # fijan su propio nivel y entonces el de la raíz no las filtra.
    for ruidosa in ("httpx", "google_genai"):
        logging.getLogger(ruidosa).setLevel(logging.WARNING)

    load_dotenv()

    modelo = ChatGoogleGenerativeAI(
        model=os.getenv("AI_MODEL"),
    )

    paso_clasificacion = construir_paso_clasificacion(modelo)

    # La ruta de consulta sale envuelta en su respaldo. Las otras tres
    # van sueltas, cubiertas por el try/except de abajo.
    cadena_consulta = construir_cadena_consulta_segura(
        plantilla_consulta | modelo | StrOutputParser()
    )
    cadena_clausula = plantilla_clausula | modelo | StrOutputParser()
    cadena_contrato = plantilla_contrato | modelo | StrOutputParser()
    cadena_ley = plantilla_ley | modelo | StrOutputParser()

    cadena_con_enrutamiento = construir_cadena_con_enrutamiento(
        paso_clasificacion=paso_clasificacion,
        cadena_clausula=cadena_clausula,
        cadena_contrato=cadena_contrato,
        cadena_ley=cadena_ley,
        cadena_consulta=cadena_consulta,
    )

    # Primera pregunta del checklist. Se corre la clasificación sola
    # sobre el banco, sin la bifurcación, porque para verificar que la
    # categoría es la esperada no hace falta la respuesta.
    titulobn("\n\n*** El clasificador sobre el banco de mensajes ***")
    notabn("\n  esperada   obtenida   entrada")

    aciertos = 0
    for esperada, mensaje in BANCO_DE_MENSAJES:
        obtenida = paso_clasificacion.invoke({"mensaje": mensaje})

        # shorten corta en la palabra anterior y pone los puntos
        # suspensivos, en vez de cortar a la mitad de una letra.
        recorte = textwrap.shorten(mensaje, width=44, placeholder="...")

        linea = f"  {esperada:<10} {obtenida:<10} {recorte}"
        if obtenida == esperada:
            aciertos += 1
            exitobn(linea)
        else:
            avisofn(linea)

    total = len(BANCO_DE_MENSAJES)
    if aciertos == total:
        exitobn(f"\n  {aciertos}/{total} cayeron donde debían")
    else:
        avisofn(f"\n  {aciertos}/{total} cayeron donde debían")

    # Tercera pregunta del checklist. Una entrada por cada ruta, de
    # punta a punta, para leer las cuatro respuestas seguidas y
    # confirmar que cada prompt produce algo realmente distinto. Se
    # toma la primera entrada de cada categoría del banco de arriba,
    # para no repetir textos.
    #
    # Todo pasa por procesar_mensaje_seguro, que es el punto de entrada
    # del Bloque 20, y no por la cadena directamente.
    titulobn("\n\n*** Una entrada por ruta, de punta a punta ***")

    vistas = set()
    for categoria, mensaje in BANCO_DE_MENSAJES:
        if categoria in vistas:
            continue
        vistas.add(categoria)

        titulofn(f"\n\n  ruta {categoria}")
        notabn(f"\n{mensaje}\n")
        respuesta = procesar_mensaje_seguro(
            cadena_con_enrutamiento, mensaje
        )
        exitobn(respuesta)
