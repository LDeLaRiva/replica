"""Registro de versiones del prompt de sistema (Bloque 32, paso 1).

Qué hace. Guarda las versiones por las que pasó el prompt de este
proyecto, cada una con su huella, su autor, su fecha y la nota de qué
cambió. Y muestra el diff entre las dos, para ver el cambio exacto.

Qué se entrega. Este archivo, junto con `grafo_supervision.py` y
`matriz_riesgos.py`.

Cómo se corre. `python src/registro_prompts.py`. No llama a la API y
no necesita la clave.

Las versiones registradas son reales. No son un ejemplo. La v1 es la
plantilla que este proyecto usó hasta el Bloque 28, y la v2 es la que
está en producción hoy. El motivo del cambio está medido y escrito en
`docs/limites_bloque28.md`, en la sección sobre la plantilla de tres
salidas.

Las desviaciones del código de la actividad, y por qué cada una.

Primera. La v2 no se escribe a mano, se importa de
`src/recuperacion.py`. Un registro de versiones que copia el texto del
prompt empieza a mentir el día que alguien cambia el prompt y se
olvida de actualizar la copia. Importándolo, la versión registrada es
siempre la que de verdad corre.

Segunda. Hay una huella esperada escrita como constante, y el archivo
falla si no coincide con la del prompt vivo. Esa comprobación es el
punto entero del versionado. Si alguien edita `PROMPT_TEMPLATE` sin
registrar una versión nueva, esto lo detecta en vez de dejar el
registro desactualizado en silencio.

Tercera. La v1 sí va escrita a mano, porque ya no existe en el código.
Se recuperó del historial del repositorio.

Cuarta. Cada versión guarda además el modelo contra el que se validó.
No está en el código de la actividad, pero la lección de versionado lo
pide de forma explícita, "versionar el prompt sin registrar contra qué
modelo se validó pierde información relevante para el día que cambie
el modelo". El nombre sale de la variable de entorno `AI_MODEL`, que
es de donde lo toma el resto del proyecto, para que el registro no
pueda nombrar un modelo distinto del que de verdad corre.

Quinta. La ruta. La actividad entrega el archivo en la raíz. Aquí vive
en `src/`, que es donde vive el código de este repositorio.

Sexta. La fecha de cada versión va escrita y no se calcula con
`date.today()`. La primera versión de este archivo la calculaba, de
modo que las dos versiones mostraban el día en que se ejecutaba el
registro y no el día en que cada una empezó a correr. Un registro de
versiones cuyo campo de fecha dice siempre hoy no registra nada. La
fecha de la v1 es la del commit que trajo `src/recuperacion.py` al
repositorio, y la de la v2 sale de
`src/registros_latencia_costo.jsonl`, donde las corridas del 17 de
noviembre son de la plantilla anterior y las del 18 de la actual.
"""

import difflib
import hashlib
import os
from datetime import date

from recuperacion import PROMPT_TEMPLATE


NOMBRE_DEL_PROMPT = "prompt_rag_legal"

# La huella de la versión que hoy corre en `recuperacion.py`. Si el
# prompt cambia y nadie registra la versión nueva, la comprobación
# del final falla. Para actualizarla, agrega la versión nueva al
# registro y pega aquí la huella que imprime.
HUELLA_ESPERADA_ACTUAL = "faa337bde6a2"


def huella_prompt(texto: str) -> str:
    """Devuelve los primeros 12 caracteres del sha256 del texto."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def diff_prompts(anterior: str, nueva: str) -> list[str]:
    """Devuelve el diff palabra por palabra entre dos versiones.

    Se compara por palabras y no por líneas porque estas plantillas
    traen continuaciones de línea, y un diff por líneas marcaría como
    cambiado todo el párrafo cuando solo se movió una palabra.
    """
    return list(difflib.unified_diff(
        anterior.split(), nueva.split(),
        fromfile="version_anterior", tofile="version_nueva",
        lineterm="",
    ))


class RegistroDePrompts:
    """Guarda las versiones de uno o más prompts, en orden."""

    def __init__(self) -> None:
        self.versiones: list[dict[str, str]] = []

    def registrar(self, nombre: str, texto: str, autor: str,
                  nota: str, modelo: str,
                  fecha: str | None = None) -> dict[str, str]:
        """Agrega una versión y la devuelve.

        El modelo va en el registro porque un prompt ajustado contra
        un modelo no se comporta igual en otro. La lección lo dice,
        "versionar el prompt sin registrar contra qué modelo se
        validó pierde información relevante para el día que cambie
        el modelo".

        La fecha entra por parámetro porque es la del día en que
        esa versión empezó a correr, y no la del día en que se
        ejecuta este archivo. Sin ella, las dos versiones dirían
        hoy y el registro no registraría nada.
        """
        version = {
            "nombre": nombre,
            "huella": huella_prompt(texto),
            "texto": texto,
            "autor": autor,
            "fecha": fecha or str(date.today()),
            "modelo": modelo,
            "nota": nota,
        }
        self.versiones.append(version)
        return version

    def ultima(self, nombre: str) -> dict[str, str] | None:
        """Devuelve la versión más reciente de ese prompt."""
        candidatas = [v for v in self.versiones if v["nombre"] == nombre]
        return candidatas[-1] if candidatas else None


# *** Las dos versiones reales de este proyecto ***

# La plantilla que este proyecto usó hasta el Bloque 28. Daba las tres
# salidas en párrafos sueltos, sin numerar, y envolvía la frase de
# abstención entre comillas. Ya no está en el código, se recuperó del
# historial del repositorio.
PROMPT_V1 = """Responde la pregunta usando SOLO el contexto de abajo. \
Cita la fuente de cada afirmacion con su numero entre corchetes, como \
[1].

Si el contexto responde solo una parte de la pregunta, responde esa \
parte y despues di con claridad que parte no se puede responder con \
este contexto.

Si el contexto no responde ninguna parte de la pregunta, responde \
exactamente esta frase y nada mas.

"El contexto disponible no alcanza para responder esta consulta."

Contexto:
{contexto}

Pregunta: {pregunta}

Respuesta:"""


# La fecha en que cada version empezo a correr, no la de hoy.
# La v1 es la del commit que trajo recuperacion.py al repositorio.
# La v2 sale del registros_latencia_costo.jsonl, cuyas corridas del
# 17 son de la plantilla anterior y las del 18 de la actual.
FECHA_V1 = "2026-11-13"
FECHA_V2 = "2026-11-18"

registro = RegistroDePrompts()

# El modelo contra el que se validó cada versión. Sale de la misma
# variable de entorno que usa el resto del proyecto, para que el
# registro no pueda nombrar un modelo distinto del que de verdad
# corre.
MODELO = os.getenv("AI_MODEL", "sin AI_MODEL en el entorno")

registro.registrar(
    NOMBRE_DEL_PROMPT,
    PROMPT_V1,
    "Lorena De La Riva",
    "version original, las tres salidas en parrafos sin numerar",
    MODELO,
    fecha=FECHA_V1,
)
registro.registrar(
    NOMBRE_DEL_PROMPT,
    PROMPT_TEMPLATE,
    "Lorena De La Riva",
    "enumera las tres salidas y saca las comillas de la frase de "
    "abstencion, porque la tercera salida se filtraba a la respuesta "
    "(Bloque 28)",
    MODELO,
    fecha=FECHA_V2,
)


if __name__ == "__main__":
    print("*** las versiones registradas ***")
    for v in registro.versiones:
        print(v["huella"], "-", v["nota"])
        print(f"   {v['autor']}, {v['fecha']}, validada contra "
              f"{v['modelo']}")

    v1, v2 = registro.versiones
    print()
    print("huellas distintas:", v1["huella"] != v2["huella"])
    print("largos:", len(v1["texto"]), "y", len(v2["texto"]))

    ultima = registro.ultima(NOMBRE_DEL_PROMPT)
    print("ultima version activa:", ultima["huella"])

    print()
    print("*** el diff entre las dos ***")
    for linea in diff_prompts(v1["texto"], v2["texto"]):
        print(linea)

    # *** La comprobacion que le da sentido al registro ***
    #
    # Si alguien edita PROMPT_TEMPLATE y no registra la version
    # nueva, el registro quedaria mintiendo sin avisar. Esto lo
    # detecta.
    print()
    print("*** el registro contra el prompt que corre hoy ***")
    viva = huella_prompt(PROMPT_TEMPLATE)
    print("huella del prompt vivo   ", viva)
    print("huella de la ultima      ", ultima["huella"])
    print("huella esperada          ", HUELLA_ESPERADA_ACTUAL)

    assert viva == ultima["huella"], (
        "la ultima version registrada no es la que corre"
    )
    assert viva == HUELLA_ESPERADA_ACTUAL, (
        f"el prompt cambio y nadie registro la version nueva. "
        f"Ahora vale {viva}. Registra la version y actualiza "
        f"HUELLA_ESPERADA_ACTUAL."
    )
    print()
    print("el registro esta al dia")
