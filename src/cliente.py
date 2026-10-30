"""Cliente del proyecto. Una sola puerta de entrada al modelo.

Para hacer una consulta había que llamar a las funciones
de src.consumir_gemini en el orden correcto y saber qué podía fallar
en cada una. Este archivo envuelve todo eso en consultar_modelo, que
recibe una pregunta y devuelve la respuesta ya lista.

Al usar este cliente no se necesita saber que por dentro hay un
reintento, ni cuántas veces se reintentó, ni qué código de estado
respondió el servicio.

Los errores llegan ya clasificados desde src.consumir_gemini. Los que
se resuelven esperando se reintentan aquí. Los que no, pasan de largo
sin que este archivo los toque.
"""

import random
import sys
import time
from pathlib import Path
from typing import Any, Callable

# La raíz se agrega a la ruta de búsqueda para que el archivo corra
# tanto con el botón como con python -m desde la raíz.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.consumir_gemini import (                       # noqa: E402
    PRECIO_ENTRADA,
    PRECIO_SALIDA,
    armar_peticion,
    calcular_costo_peticion,
    enviar_peticion,
    extraer_texto,
    parsear_respuesta_json,
)

INTENTOS = 3
# La espera parte en ESPERA_BASE y se duplica en cada intento, hasta
# ESPERA_MAXIMA. El techo existe para que la espera no se dispare si
# algún día se suben los intentos, porque con base 2 y seis intentos
# el quinto reintento ya esperaría 32 segundos.
ESPERA_BASE = 2
ESPERA_MAXIMA = 30

# La marca con que src.consumir_gemini separa el detalle para quien
# programa del mensaje para el usuario.
MARCA_TECNICA = "[técnico] "

# Lo que lleva gastado esta corrida. Se reinicia en cada ejecución,
# porque es el total de la sesión y no un registro permanente.
costo_total_sesion = 0.0


def _linea_tecnica(fallo: Exception) -> str:
    """Saca el detalle técnico de un error de dos partes.

    La línea se busca por su marca, recorriendo el mensaje de abajo
    hacia arriba, en vez de tomar la última a ciegas. Un mensaje que
    termine en salto de línea deja esa última vacía, y entonces el
    detalle se perdía sin que nada avisara.

    El guion bajo del nombre indica que es de uso interno, igual que
    en src.contraste.

    Args:
        fallo: la excepción de la que se quiere el detalle.

    Returns:
        El texto que sigue a la marca técnica, o una cadena vacía si
        el error no trae esa línea.
    """
    for linea in reversed(str(fallo).split("\n")):
        if linea.startswith(MARCA_TECNICA):
            return linea[len(MARCA_TECNICA):].strip()
    return ""


def con_reintento(
    funcion: Callable[[], Any],
    intentos: int = INTENTOS,
    espera_base: float = ESPERA_BASE,
    espera_maxima: float = ESPERA_MAXIMA,
    avisar: Callable[[str], None] = print,
) -> Any:
    """Repite una operación mientras falle por algo momentáneo.

    Solo atrapa TimeoutError, que es el tipo que src.consumir_gemini
    reserva para lo que se resuelve esperando, como el límite de uso o
    una caída del proveedor. Un ValueError, por ejemplo una credencial
    inválida, pasa de largo sin reintentarse, porque insistir en algo
    que no es momentáneo solo gasta tiempo y peticiones.

    Args:
        funcion: lo que hay que intentar, sin argumentos.
        intentos: cuántas veces se intenta en total.
        espera_base: desde cuántos segundos parte la espera. Se
            duplica en cada intento.
        espera_maxima: hasta cuánto puede crecer esa espera.
        avisar: cómo se informa cada reintento. Por defecto print,
            pero quien llame puede entregar otra cosa, porque este
            módulo no decide cómo se muestran las cosas.

    Returns:
        Lo que devuelva la función en el primer intento que resulte.

    Raises:
        ValueError: si intentos es menor que 1. Sin al menos un
            intento no hay nada que ejecutar.
        TimeoutError: si se agotan todos los intentos. Lo vuelve a
            lanzar tal cual para que el error no quede escondido.
    """
    # Con cero o menos, el bucle no corre ninguna vez y la función
    # devolvería None sin avisar. Río abajo ese None reaparece como
    # un TypeError confuso, lejos de donde está el problema real.
    if intentos < 1:
        raise ValueError(
            "[usuario] No pudimos completar tu consulta. Intenta "
            "nuevamente en unos minutos.\n"
            f"{MARCA_TECNICA}intentos debe ser 1 o más, llegó "
            f"{intentos}.")

    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError as fallo:
            # En el último intento se deja pasar el error en vez de
            # taparlo. Sin esta salida el bucle reintentaría siempre y
            # nadie se enteraría de que algo sigue mal.
            if intento == intentos:
                raise
            # TimeoutError cubre cuatro casos, el 429, una caída del
            # proveedor, la falta de conexión y que el servicio no
            # conteste. El aviso dice cuál fue, tomándolo de la línea
            # técnica del propio error, que ya lo trae. Sin esto el
            # aviso diría algo genérico y el error final diría otra
            # cosa, que es justo lo que confunde al leer.
            causa = _linea_tecnica(fallo).split(". ")[0].strip(" .")
            # Si el error llegara sin línea técnica, o con una vacía,
            # el aviso saldría con dos puntos seguidos y sin decir
            # nada. El nombre del tipo es poco, pero no es un hueco.
            if not causa:
                causa = type(fallo).__name__
            # La espera se duplica en cada intento en vez de ser
            # siempre la misma. Si el proveedor frenó por exceso de
            # uso, volver a los 2 segundos cae dentro de la misma
            # ventana y topa el límite otra vez. El azar del final
            # evita que varias corridas que fallaron juntas vuelvan
            # todas en el mismo segundo.
            espera = min(espera_base * (2 ** (intento - 1)),
                         espera_maxima)
            espera_con_jitter = espera + random.uniform(0, espera * 0.1)
            avisar(f"Intento {intento} de {intentos} falló. {causa}. "
                   f"Reintentando en {espera_con_jitter:.1f}s...")
            time.sleep(espera_con_jitter)


def registrar_costo(respuesta: dict) -> float:
    """Calcula lo que costó una respuesta y lo suma al total.

    El cálculo lo hace calcular_costo_peticion, que vive en
    src.consumir_gemini porque los precios dependen del proveedor y
    distinguen los tokens que se envían de los que se generan. Aquí
    solo se acumula, que es lo que le importa al cliente.

    No imprime nada, igual que el resto del módulo. Devuelve el costo
    para que quien llame decida si lo muestra y cómo.

    Args:
        respuesta: la respuesta del servicio, ya convertida en
            diccionario.

    Returns:
        El costo en dólares de esa respuesta.

    Raises:
        RuntimeError: el que lanza calcular_costo_peticion si a la
            respuesta le falta el bloque usageMetadata.
    """
    global costo_total_sesion
    costo = calcular_costo_peticion(
        respuesta, PRECIO_ENTRADA, PRECIO_SALIDA)
    costo_total_sesion += costo
    return costo


def consultar_modelo(
    pregunta: str,
    system_instruction: str = "",
    response_schema: dict = None,
    claves_esperadas: list = None,
) -> Any:
    """Hace una consulta al modelo y devuelve la respuesta lista.

    Es el único punto de entrada del cliente. Arma la petición, la
    envía con reintento, saca el texto y, si se pidió una estructura,
    la valida antes de devolverla.

    Args:
        pregunta: lo que se quiere preguntar.
        system_instruction: la instrucción de comportamiento, que
            viaja en un campo aparte de la pregunta.
        response_schema: la forma que debe tener el JSON de respuesta.
            Si no se entrega, la respuesta vuelve como texto libre.
        claves_esperadas: las claves que ese JSON debe traer. Solo se
            usa cuando se entregó un esquema.

    Returns:
        El texto generado, o el diccionario ya validado si se entregó
        un esquema.

    Raises:
        ValueError: si la pregunta no sirve, si falta la configuración
            del .env, si la credencial no es válida o si el modelo no
            existe. Ninguno se arregla reintentando.
        RuntimeError: si se agotaron los reintentos, o si la respuesta
            del servicio no tiene la forma esperada.
    """
    url, headers, body = armar_peticion(
        pregunta, system_instruction, response_schema)

    try:
        respuesta = con_reintento(
            lambda: enviar_peticion(url, headers, body))

    # con_reintento ya agotó sus intentos y volvió a lanzar el
    # TimeoutError original. Aquí cambia de tipo a RuntimeError para
    # que quien llame distinga lo que ya no se arregla solo de lo que
    # todavía se podía reintentar.
    except TimeoutError as fallo:
        # Las dos partes del error original se separan y se vuelven a
        # armar. La de usuario se conserva tal cual, porque ya dice
        # qué pasó, sea la conexión o el límite de uso, y porque el
        # reintento es un detalle interno que a él no le sirve. La
        # cuenta de intentos va en la parte técnica, que es de quien
        # programa. Pegar el mensaje entero dejaría un [usuario]
        # metido adentro de un [técnico] y el bloque pasaría a tres
        # líneas, rompiendo el formato de dos partes.
        usuario = str(fallo).split("\n")[0].replace("[usuario] ", "")
        detalle = _linea_tecnica(fallo)
        # El detalle se pega solo si vino. Si no, el mensaje queda en
        # la cuenta de intentos, que ya es algo, y no con un espacio
        # suelto al final.
        tecnico = f"Se agotaron los {INTENTOS} intentos."
        if detalle:
            tecnico = f"{tecnico} {detalle}"
        raise RuntimeError(f"[usuario] {usuario}\n"
                           f"{MARCA_TECNICA}{tecnico}")

    # El ValueError de la credencial no se toca. Sigue propagándose
    # tal cual, porque ya trae un mensaje claro desde enviar_peticion.

    # El costo se registra recién aquí, después de que la respuesta
    # llegó bien. Si se registrara antes del try se contarían
    # operaciones que en realidad fallaron y nunca gastaron tokens.
    registrar_costo(respuesta)

    texto = extraer_texto(respuesta)

    if response_schema is None:
        return texto
    return parsear_respuesta_json(texto, claves_esperadas or [])


if __name__ == "__main__":
    # El módulo no usa colores, solo esta prueba.
    from src.contraste import *                         # noqa: E402, F403

    # Los tres escenarios que pide la actividad.
    #   1. consulta normal, es la que corre abajo
    #   2. credencial inválida, se prueba cambiando AI_API_KEY en el
    #      .env por cualquier cosa y volviendo a correr este archivo.
    #      Debe fallar de inmediato, sin reintentar
    #   3. reintentos agotados, se prueba lanzando varias corridas
    #      seguidas hasta topar el límite del plan gratuito
    try:
        titulobn("\nConsulta a través del cliente")
        respuesta = consultar_modelo(
            "¿Cuál es la capital de Chile?",
            "Responde en una sola oración y en español.")
        salbn(f"\n{respuesta}")
        notabn(f"\nCosto acumulado de la sesión  "
               f"{costo_total_sesion:.8f} USD")
        notabn("\nProceso terminado.")

    except ValueError as fallo:
        avisofn(f"\nError de configuración.\n{fallo}")

    except RuntimeError as fallo:
        avisofn(f"\n{fallo}")

    except Exception as fallo:
        avisofn(f"\nError inesperado. {type(fallo).__name__}")
        avisofn(f"\n{fallo}")
