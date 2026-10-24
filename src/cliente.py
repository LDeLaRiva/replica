"""Cliente del proyecto. Una sola puerta de entrada al modelo.

pra hacer una consulta había que llamar a las funciones
de src.consumir_gemini en el orden correcto y saber qué podía fallar
en cada una. Este archivo envuelve todo eso en consultar_modelo, que
recibe una pregunta y devuelve la respuesta ya lista.

al usar este cliente no se necesita saber que por dentro hay un
reintento, ni cuántas veces se reintentó, ni qué código de estado
respondió el servicio.

Los errores llegan ya clasificados desde src.consumir_gemini. Los que
se resuelven esperando se reintentan aquí. Los que no, pasan de largo
sin que este archivo los toque.
"""

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
    armar_peticion,
    enviar_peticion,
    extraer_texto,
    parsear_respuesta_json,
)

INTENTOS = 3
ESPERA_SEGUNDOS = 2


def con_reintento(
    funcion: Callable[[], Any],
    intentos: int = INTENTOS,
    espera_segundos: int = ESPERA_SEGUNDOS,
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
        espera_segundos: cuánto se espera entre un intento y el
            siguiente.
        avisar: cómo se informa cada reintento. Por defecto print,
            pero quien llame puede entregar otra cosa, porque este
            módulo no decide cómo se muestran las cosas.

    Returns:
        Lo que devuelva la función en el primer intento que resulte.

    Raises:
        TimeoutError: si se agotan todos los intentos. Lo vuelve a
            lanzar tal cual para que el error no quede escondido.
    """
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            # En el último intento se deja pasar el error en vez de
            # taparlo. Sin esta salida el bucle reintentaría siempre y
            # nadie se enteraría de que algo sigue mal.
            if intento == intentos:
                raise
            avisar(f"Intento {intento} de {intentos} falló por límite "
                   f"de uso o error de conexión. Reintentando...")
            time.sleep(espera_segundos)


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
            del .env, o si la credencial no es válida. Ninguno de los
            tres se arregla reintentando.
        RuntimeError: si se agotaron los reintentos, o si la respuesta
            del servicio no tiene la forma esperada.
    """
    url, headers, body = armar_peticion(
        pregunta, system_instruction, response_schema)

    try:
        respuesta = con_reintento(
            lambda: enviar_peticion(url, headers, body))

    # con_reintento ya agotó sus intentos y volvió a lanzar el
    # TimeoutError original. Quien usa el cliente no tiene por qué
    # conocer ese detalle interno, así que se traduce a un error
    # propio con un mensaje pensado para él.
    except TimeoutError as fallo:
        raise RuntimeError(
            "[usuario] El servicio no respondió después de varios "
            "intentos. Intenta más tarde.\n"
            f"[técnico] Se agotaron los {INTENTOS} intentos. {fallo}")

    # El ValueError de la credencial no se toca. Sigue propagándose
    # tal cual, porque ya trae un mensaje claro desde enviar_peticion.

    texto = extraer_texto(respuesta)

    if response_schema is None:
        return texto
    return parsear_respuesta_json(texto, claves_esperadas or [])


if __name__ == "__main__":
    # El módulo no usa colores, solo esta prueba.
    from src.contraste import *                         # noqa: E402, F403

    # Los tres escenarios que se piden:
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
        notabn("\nProceso terminado.")

    except ValueError as fallo:
        avisofn(f"\nError de configuración.\n{fallo}")

    except RuntimeError as fallo:
        avisofn(f"\n{fallo}")

    except Exception as fallo:
        errorfn(f"\nError inesperado. {type(fallo).__name__}")
        avisofn(f"\n{fallo}")