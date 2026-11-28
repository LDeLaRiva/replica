"""Punto de supervisión humana para desplegar un prompt (paso 2).

Qué hace. Un grafo de tres nodos que propone una versión nueva del
prompt, se detiene a pedir aprobación a una persona, y recién después
la aplica o la rechaza.

Qué se entrega. Este archivo, junto con `registro_prompts.py` y
`matriz_riesgos.py`.

Cómo se corre. `python src/grafo_supervision.py`. No llama a la API y
no necesita la clave. Sí necesita langgraph, `pip install langgraph`.

Por qué este riesgo lleva punto de supervisión. En la matriz, el
riesgo de que las instrucciones y el contexto recuperado compartan el
mismo canal de texto quedó en ALTO, y toda fila ALTA o CRÍTICA
necesita que una persona revise antes de que algo se ejecute. Cambiar
el prompt es exactamente ese momento. Este proyecto ya tiene la
experiencia de dos reescrituras que midieron peor y hubo que
revertir, así que la aprobación no es un trámite.

Las desviaciones del código de la actividad, y por qué cada una.

Primera. El `thread_id` se genera con uuid en vez de escribirse a
mano. El código de la actividad lo escribe fijo, pero la tabla de
errores de la lección de versionado recomienda lo contrario,
"genera un thread_id único para cada solicitud de aprobación (por
ejemplo con uuid) y guárdalo junto a la solicitud". El motivo que da
es que reusar un identificador no siempre da error, a veces el grafo
hace algo distinto sin avisar.

Segunda. `resolver` comprueba que el hilo tenga algo pendiente antes
de reanudar. Sin esa guarda, reanudar un hilo ya resuelto devuelve el
estado final sin ejecutar nada y sin avisar, que es uno de los
errores que la propia actividad describe en su tabla. La guarda lo
convierte en un error con mensaje.

Tercera. Se prueban cuatro caminos y no dos, el de aprobación, el de
rechazo, el de reanudar un hilo ya resuelto y el de aprobar una
versión distinta de la revisada. Los dos últimos demuestran las dos
guardas anteriores.

Cuarta. La ruta. La actividad entrega el archivo en la raíz. Aquí
vive en `src/`, que es donde vive el código de este repositorio.
"""

import uuid
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


# La huella de la versión actual del prompt, tomada de la salida de
# `registro_prompts.py`. Va escrita como texto y no importada, para
# que los dos pasos sigan siendo independientes, como pide la
# actividad. Si el prompt cambia, `registro_prompts.py` avisa.
HUELLA_ACTUAL = "faa337bde6a2"


class EstadoDespliegue(TypedDict):
    """Lo que viaja entre los nodos del grafo."""

    huella_nueva: str
    aprobado: bool


def proponer(estado: EstadoDespliegue) -> dict[str, Any]:
    """Deja constancia de qué versión se quiere activar."""
    print("  propuesta:", estado["huella_nueva"])
    return {}


def supervisar(estado: EstadoDespliegue) -> dict[str, Any]:
    """Detiene el grafo y espera la decisión de una persona.

    `interrupt` guarda el estado y corta la ejecución. Lo que se le
    pasa es lo que verá quien tenga que aprobar, así que lleva el
    motivo y la huella propuesta y no el prompt entero.
    """
    decision = interrupt({
        "motivo": "aprobar nueva version de prompt en produccion",
        "huella_propuesta": estado["huella_nueva"],
    })
    return {"aprobado": decision}


def aplicar(estado: EstadoDespliegue) -> dict[str, Any]:
    """Activa la versión nueva, o deja la anterior en su lugar."""
    if estado["aprobado"]:
        print("  version", estado["huella_nueva"], "activada")
    else:
        print("  version", estado["huella_nueva"],
              "rechazada, se mantiene la anterior")
    return {}


grafo = StateGraph(EstadoDespliegue)
grafo.add_node("proponer", proponer)
grafo.add_node("supervisar", supervisar)
grafo.add_node("aplicar", aplicar)
grafo.add_edge(START, "proponer")
grafo.add_edge("proponer", "supervisar")
grafo.add_edge("supervisar", "aplicar")
grafo.add_edge("aplicar", END)

app_despliegue = grafo.compile(checkpointer=InMemorySaver())


def nueva_config(prefijo: str = "despliegue") -> dict[str, Any]:
    """Un thread_id nuevo para cada ejecución.

    Un hilo que ya terminó no vuelve a pasar por la aprobación, así
    que reusar el mismo identificador haría que la segunda corrida
    de este archivo se comportara distinto de la primera.
    """
    return {"configurable": {
        "thread_id": f"{prefijo}-{uuid.uuid4().hex[:8]}"
    }}


def resolver(config: dict[str, Any], aprobar: bool,
             huella_revisada: str) -> dict[str, Any]:
    """Reanuda un despliegue pendiente con la decisión humana.

    Hace dos comprobaciones antes de reanudar, y las dos salen de la
    tabla de errores de la lección de versionado.

    La primera es que el hilo tenga algo pendiente. Reanudar uno ya
    resuelto devuelve su estado final sin ejecutar ningún nodo y sin
    avisar.

    La segunda es que la versión que está en el hilo sea la que la
    persona revisó. La lección describe el caso, dos solicitudes que
    comparten el `thread_id` y la segunda reemplaza a la primera
    mientras estaba pendiente, de modo que la aprobación termina
    aplicándose a una versión que nadie miró.
    """
    instantanea = app_despliegue.get_state(config)
    if not instantanea.next:
        raise ValueError(
            "este thread_id no tiene ninguna aprobacion pendiente, "
            "el despliegue ya se resolvio"
        )

    en_el_hilo = instantanea.values["huella_nueva"]
    if en_el_hilo != huella_revisada:
        raise ValueError(
            f"la version del hilo cambio desde que se reviso. "
            f"Se reviso {huella_revisada} y en el hilo hay "
            f"{en_el_hilo}"
        )

    return app_despliegue.invoke(Command(resume=aprobar),
                                 config=config)


if __name__ == "__main__":
    print("*** 1, el camino de aprobacion ***")
    config_si = nueva_config("aprueba")
    resultado = app_despliegue.invoke(
        {"huella_nueva": HUELLA_ACTUAL, "aprobado": False},
        config=config_si,
    )
    assert "__interrupt__" in resultado, (
        "el grafo no se detuvo, reviso que el checkpointer y el "
        "thread_id esten bien"
    )
    pendiente = app_despliegue.get_state(config_si).interrupts[0].value
    print("  pendiente:", pendiente)
    assert pendiente["huella_propuesta"] == HUELLA_ACTUAL

    final_si = resolver(config_si, True, HUELLA_ACTUAL)
    assert final_si["aprobado"] is True
    assert "__interrupt__" not in final_si
    print("  estado final:", final_si)

    print()
    print("*** 2, el camino de rechazo, con otro thread_id ***")
    config_no = nueva_config("rechaza")
    app_despliegue.invoke(
        {"huella_nueva": HUELLA_ACTUAL, "aprobado": False},
        config=config_no,
    )
    final_no = resolver(config_no, False, HUELLA_ACTUAL)
    assert final_no["aprobado"] is False
    print("  estado final:", final_no)

    print()
    print("*** 3, reanudar un despliegue ya resuelto ***")
    try:
        resolver(config_si, True, HUELLA_ACTUAL)
    except ValueError as error:
        print("  ValueError:", error)
    else:
        raise AssertionError(
            "reanudar un hilo ya resuelto tenia que dar error"
        )

    print()
    print("*** 4, aprobar una version distinta de la revisada ***")
    config_otra = nueva_config("cambiada")
    app_despliegue.invoke(
        {"huella_nueva": HUELLA_ACTUAL, "aprobado": False},
        config=config_otra,
    )
    try:
        resolver(config_otra, True, "000000000000")
    except ValueError as error:
        print("  ValueError:", error)
    else:
        raise AssertionError(
            "aprobar una version distinta de la revisada tenia que "
            "dar error"
        )

    print()
    print("los cuatro caminos se comportaron como se esperaba")
