"""Supervisión humana y registro de las decisiones del agente.

Tres funciones para dos cosas distintas. Pedir una aprobación antes
de ejecutar algo que no se puede deshacer, y dejar por escrito qué
se decidió en cada interacción.

Están aparte del agente por el mismo criterio del corpus legal y
por la misma retroalimentación del Gate 1, que pidió continuar
desacoplando las funciones auxiliares hacia módulos de soporte para
mantener conciso el punto de entrada. Ninguna de las tres sabe nada
de agentes ni de modelos.

Por qué la espera va en un hilo

La forma habitual de esperar una respuesta por teclado con límite de
tiempo es select.select(). En Windows no funciona sobre la entrada
estándar, solo sobre sockets, y este proyecto se desarrolla en
Windows.

Así que la espera va en un hilo aparte con un Event, que se cumple
cuando llega la respuesta o cuando se agota el tiempo. La función
conserva el nombre, los parámetros, el tipo de retorno y el
resultado seguro ante un vencimiento. Lo único distinto es cómo
espera por dentro, y de paso queda funcionando igual en los tres
sistemas operativos.

Un límite conocido de esta forma

Si la espera vence, el hilo queda detenido en la lectura del
teclado. Con una segunda aprobación en la misma ejecución habría dos
hilos leyendo la misma entrada, y cuál de los dos recibe el texto no
está definido. En este proyecto no ocurre, porque cada aprobación se
contesta antes de seguir, pero un servicio que atienda varias a la
vez necesitaría otra cosa.

Por qué esta es la única función del proyecto que imprime

El resto de los módulos no imprime nunca. Lanzan o devuelven, y
quien muestra es el archivo que se ejecuta. Esta es la excepción,
porque su trabajo es la conversación con la consola. Separar la
pregunta de la lectura dejaría dos mitades que no sirven por
separado.
"""

import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

# El archivo de trazas queda en la misma carpeta que este módulo.
# Con el nombre a solas se guardaría en la carpeta donde está parada
# la terminal, que no siempre es esta. Es el mismo criterio de
# revision_manual.py.
#
# Por eso el archivo se revisa apuntando a la carpeta, con
# wc -l src/trazas_agente.jsonl.
CARPETA = Path(__file__).resolve().parent
RUTA_TRAZAS = CARPETA / "trazas_agente.jsonl"

# Segundos de espera antes de dar la aprobación por no recibida.
ESPERA_APROBACION = 300

# Las decisiones de aprobación de esta ejecución. Vive en memoria y
# se pierde al terminar, igual que los historiales del agente. Un
# servicio real lo guardaría en una base de datos.
registro_aprobaciones = []

# Las decisiones que la próxima traza se va a llevar al archivo.
#
# Sin esta lista, la aprobación solo existiría en memoria y moriría
# con el proceso. Quien revise las trazas después vería la
# herramienta de riesgo alto ejecutada y no tendría forma de saber si
# alguien la autorizó, que es justo lo que hay que poder responder.
#
# El guion bajo indica que es de uso interno, igual que en
# src.contraste. Quien revisa usa registro_aprobaciones.
_aprobaciones_pendientes = []


def esperar_aprobacion(
    mensaje: str,
    tiempo_limite_segundos: int = ESPERA_APROBACION,
) -> bool:
    """Pregunta por consola y devuelve si la persona aprobó.

    Devuelve True solo si la respuesta es la letra s. Cualquier otra
    cosa, y también que no llegue respuesta dentro del tiempo
    límite, devuelven False.

    Que el vencimiento devuelva False no es un detalle. Para una
    acción irreversible, no aprobado es la opción segura. Un
    vencimiento que ejecutara la acción anularía el sentido de pedir
    supervisión.

    Args:
        mensaje: lo que se le muestra a quien aprueba. Tiene que
            decir qué se va a hacer y por qué no se puede deshacer.
        tiempo_limite_segundos: cuánto se espera antes de darla por
            no aprobada.

    Returns:
        True si la respuesta fue s dentro del plazo, False en
        cualquier otro caso.
    """
    print(mensaje)

    # La respuesta viaja en una lista y no en una variable suelta
    # porque el hilo no puede asignar sobre una variable de la
    # función que lo creó. Una lista sí se puede modificar desde
    # adentro, y lo que importa es su contenido, no el nombre.
    respuesta = []
    recibida = threading.Event()

    def leer_del_teclado() -> None:
        try:
            respuesta.append(sys.stdin.readline())
        except Exception:
            # Sin entrada estándar conectada la lectura falla. Se
            # deja pasar y el aviso de abajo se encarga, porque la
            # lista queda vacía y eso cuenta como no aprobado.
            pass
        recibida.set()

    # daemon=True permite que el programa termine aunque el hilo
    # siga detenido en la lectura. Sin eso, un vencimiento dejaría
    # el proceso esperando para siempre a un hilo que nadie va a
    # desbloquear.
    hilo = threading.Thread(target=leer_del_teclado, daemon=True)
    hilo.start()

    # wait devuelve True si el evento se cumplió, y False si se
    # agotó el tiempo. Ese False es el vencimiento.
    if not recibida.wait(tiempo_limite_segundos):
        print("\nNo llegó respuesta a tiempo. La acción no se ejecuta.")
        return False

    if not respuesta:
        return False

    return respuesta[0].strip().lower() == "s"


def registrar_aprobacion(
    herramienta: str,
    argumentos: dict,
    aprobado: bool,
) -> None:
    """Guarda una decisión de aprobación, sea cual sea el resultado.

    Se registran las dos, la que aprueba y la que rechaza. Sin el
    rechazo no habría forma de responder después por qué una acción
    no se ejecutó.

    La decisión queda en dos listas. registro_aprobaciones las junta
    todas para revisarlas al terminar la corrida, y
    _aprobaciones_pendientes guarda las que la próxima traza se va a
    llevar al archivo.

    Args:
        herramienta: el nombre de la que pidió la aprobación.
        argumentos: con qué iba a ejecutarse.
        aprobado: lo que devolvió esperar_aprobacion.
    """
    decision = {
        "herramienta": herramienta,
        "argumentos": argumentos,
        "aprobado": aprobado,
        "momento": datetime.now().isoformat(),
    }
    registro_aprobaciones.append(decision)
    _aprobaciones_pendientes.append(decision)


def registrar_traza(
    session_id: str,
    entrada: str,
    resultado: dict,
) -> None:
    """Escribe una interacción como una línea del archivo de trazas.

    Guarda qué se preguntó, qué herramientas se usaron y con qué
    argumentos, qué respondió el agente, y si un humano autorizó las
    acciones de riesgo alto. Es el mismo criterio de registrar_costo,
    aplicado a decisiones en vez de a costos.

    El archivo es .jsonl, no .json. Cada línea es un objeto JSON
    completo e independiente, sin corchetes que los envuelvan ni
    comas entre ellos. Ese formato permite agregar al final sin
    leer y reescribir el archivo entero, que es lo que hace el modo
    "a" del open.

    La respuesta se toma con .content y no directa. Lo que trae el
    resultado no es un texto sino un objeto de mensaje, porque la
    salida pasa antes por el normalizador del agente, y json.dumps no
    sabe guardar ese objeto. Falla con TypeError.

    Eso significa que esta función da por hecho que el normalizador
    está en la cadena. Es la condición que el archivo del agente
    documenta como obligatoria.

    Args:
        session_id: la sesión a la que pertenece la interacción.
        entrada: lo que la persona escribió.
        resultado: lo que devolvió el agente, del que se leen los
            pasos intermedios y la respuesta final.
    """
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "entrada": entrada,
        "acciones": [
            {
                "herramienta": accion.tool,
                "argumentos": accion.tool_input,
                "observacion": observacion,
            }
            # Con .get y no con corchetes. Si el ejecutor no se armó
            # con return_intermediate_steps=True, esa clave no
            # existe y el acceso directo lanzaría KeyError. Así la
            # lista queda vacía y el registro igual se escribe.
            for accion, observacion in resultado.get(
                "intermediate_steps", [])
        ],
        "aprobaciones": list(_aprobaciones_pendientes),
        "respuesta_final": resultado["output"].content,
    }

    # Se vacía después de copiarlas, para que la traza siguiente no
    # repita las mismas decisiones. clear() sobre la misma lista y no
    # una asignación, porque el nombre está importado en otros
    # archivos y reasignarlo dejaría esas copias apuntando a la lista
    # vieja.
    _aprobaciones_pendientes.clear()

    # encoding utf-8 explícito. Sin eso, en Windows el archivo se
    # abre con la codificación del sistema y las tildes fallan.
    with open(RUTA_TRAZAS, "a", encoding="utf-8") as archivo:
        archivo.write(
            json.dumps(registro, ensure_ascii=False) + "\n"
        )


if __name__ == "__main__":
    # Prueba de esperar_aprobacion sola, sin agente y sin gastar
    # ninguna llamada al modelo. Sirve para confirmar que el hilo
    # funciona en este sistema operativo antes de montar nada
    # encima.
    #
    # El tiempo límite va en diez segundos y no en los trescientos
    # de siempre, para no tener que esperar cinco minutos en la
    # tercera prueba.
    LIMITE = 10

    print("Prueba de esperar_aprobacion")
    print(f"Tiempo límite reducido a {LIMITE} segundos para la prueba.")

    print("\n1 de 3. Responde la letra s y presiona Enter.")
    uno = esperar_aprobacion("¿Aprobar? (s/n): ", LIMITE)
    print(f"   devolvió {uno}, se esperaba True")

    print("\n2 de 3. Responde la letra n y presiona Enter.")
    dos = esperar_aprobacion("¿Aprobar? (s/n): ", LIMITE)
    print(f"   devolvió {dos}, se esperaba False")

    print(f"\n3 de 3. No escribas nada. Espera los {LIMITE} segundos.")
    tres = esperar_aprobacion("¿Aprobar? (s/n): ", LIMITE)
    print(f"   devolvió {tres}, se esperaba False")

    registrar_aprobacion("prueba", {"caso": "manual"}, uno)
    registrar_aprobacion("prueba", {"caso": "manual"}, dos)
    registrar_aprobacion("prueba", {"caso": "manual"}, tres)

    bien = uno is True and dos is False and tres is False
    print(f"\nResultado  {'las tres pasaron' if bien else 'revisar'}")
    print(f"Se registraron {len(registro_aprobaciones)} decisiones.")
    for linea in registro_aprobaciones:
        print(f"   aprobado {linea['aprobado']}   {linea['momento']}")
