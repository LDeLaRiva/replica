"""Matriz de riesgos del proyecto (Bloque 32, paso 3).

Qué hace. Pone en un mismo lugar los riesgos que este proyecto fue
identificando bloque por bloque, con su probabilidad, su impacto, la
mitigación que ya existe y el punto de supervisión humana cuando
corresponde.

Qué se entrega. Este archivo, junto con `registro_prompts.py` y
`grafo_supervision.py`.

Cómo se corre. `python src/matriz_riesgos.py`. No llama a la API.

Ninguno de estos riesgos es hipotético. Cada uno se detectó midiendo,
en el bloque que se nombra en su mitigación, y la medición está en el
documento de límites de ese bloque. La matriz no inventa riesgos
nuevos, ordena por severidad los que ya estaban identificados.

Las desviaciones del código de la actividad, y por qué cada una.

Primera. El punto de supervisión es un campo del diccionario y no una
anotación aparte, como sugiere la actividad. La razón es que así se
puede comprobar por código. La actividad exige que todo riesgo ALTO o
CRÍTICO tenga uno, y con el campo adentro esa exigencia se verifica
sola en vez de quedar en la buena memoria de quien revisa.

Segunda. Cada riesgo lleva además un campo `evidencia`, que dice de
dónde salió el número. La actividad pide estimar con la información
real que se tiene, y escribir la fuente al lado es lo que permite
revisar la estimación después, que es justamente lo que el chequeo de
sensibilidad manda hacer con las filas al límite.

Tercera. La ruta. La actividad entrega el archivo en la raíz. Aquí
vive en `src/`, que es donde vive el código de este repositorio.

Las anotaciones de tipos van en todas las funciones, convención de
este repositorio desde el Bloque 29.
"""


def puntaje_riesgo(probabilidad: int, impacto: int) -> int:
    """El puntaje es el producto de las dos escalas de 1 a 5."""
    return probabilidad * impacto


def categoria_riesgo(puntaje: int) -> str:
    """Traduce el puntaje a la categoría, con los cortes del curso."""
    if puntaje >= 15:
        return "CRITICO"
    if puntaje >= 9:
        return "ALTO"
    if puntaje >= 4:
        return "MEDIO"
    return "BAJO"


def esta_en_el_limite(probabilidad: int, impacto: int) -> bool:
    """Dice si mover un punto cualquiera cambia la categoría.

    Mira los cuatro vecinos de la celda, uno arriba y uno abajo en
    cada eje, y se queda fuera del tablero cuando el vecino caería
    por debajo de 1 o por encima de 5.
    """
    categoria_actual = categoria_riesgo(
        puntaje_riesgo(probabilidad, impacto)
    )
    vecinos = [
        (probabilidad + 1, impacto), (probabilidad - 1, impacto),
        (probabilidad, impacto + 1), (probabilidad, impacto - 1),
    ]
    for p2, i2 in vecinos:
        if not (1 <= p2 <= 5 and 1 <= i2 <= 5):
            continue
        if categoria_riesgo(puntaje_riesgo(p2, i2)) != categoria_actual:
            return True
    return False


# --- Los riesgos de este proyecto ----------------------------------

mis_riesgos: list[dict[str, object]] = [

    {"riesgo": "Una regla legal llega sin la condicion que la limita",
     "probabilidad": 2,
     "impacto": 5,
     "evidencia": "medido en el Bloque 28, el articulo 40 bis D "
                  "aparecio sin su condicion de jornada parcial en "
                  "1 de 3 corridas antes de la particion por inciso",
     "mitigacion": "Particion por inciso (Bloque 24) y nota de "
                   "condicion en el corpus (Bloque 28)",
     "supervision": "Revisar a mano toda respuesta que cite un "
                    "articulo con nota de condicion antes de "
                    "entregarla"},

    {"riesgo": "El corpus queda desactualizado frente a una reforma",
     "probabilidad": 2,
     "impacto": 5,
     "evidencia": "medido sobre el registro de la Direccion del "
                  "Trabajo, 49 leyes modificaron el Codigo del "
                  "Trabajo entre 2017 y 2026, dos de ellas tocaron "
                  "articulos de este corpus (Bloque 30)",
     "mitigacion": "Tasa de reforma medida (Bloque 30). El corpus "
                   "todavia no registra su fecha ni tiene proceso "
                   "de actualizacion",
     "supervision": "Revisar el registro de leyes modificatorias de "
                    "la Direccion del Trabajo antes de cada entrega "
                    "del proyecto"},

    {"riesgo": "Instrucciones y contexto recuperado comparten el "
               "mismo canal de texto plano",
     "probabilidad": 3,
     "impacto": 4,
     "evidencia": "verificado en el Bloque 31, no hay SystemMessage "
                  "ni HumanMessage en recuperacion.py, y la fuga de "
                  "vocabulario interno medida en 4 de 20 respuestas "
                  "es ese limite difuso apareciendo",
     "mitigacion": "Filtro de catorce patrones en logging_rag.py "
                   "(Bloque 31). Las capas de separacion de roles y "
                   "delimitacion del contexto siguen pendientes",
     "supervision": "Aprobar a mano cualquier cambio al prompt "
                    "despues de medir 20 respuestas, que es el "
                    "grafo de grafo_supervision.py"},

    {"riesgo": "El vocabulario de la instruccion interna llega al "
               "usuario en la respuesta",
     "probabilidad": 4,
     "impacto": 2,
     "evidencia": "medido en el Bloque 28, 4 de 20 respuestas le "
                  "hablan al usuario de 'el contexto', que es una "
                  "palabra de la instruccion y no de su consulta",
     "mitigacion": "Medido e instrumentado (Bloques 28 y 31). Dos "
                   "reescrituras de la instruccion midieron peor y "
                   "se revirtieron",
     "supervision": ""},

    {"riesgo": "Un dato personal escrito por el trabajador queda "
               "guardado en los logs",
     "probabilidad": 1,
     "impacto": 5,
     "evidencia": "constatado en el Bloque 31, los logs guardan "
                  "longitud y huella y nunca el texto, y la "
                  "comprobacion del archivo lo verifica",
     "mitigacion": "Registrar huella y longitud en vez de contenido "
                   "(Bloque 31)",
     "supervision": ""},

    {"riesgo": "Inyeccion de prompt via un documento del corpus",
     "probabilidad": 1,
     "impacto": 5,
     "evidencia": "el corpus es hoy un archivo escrito a mano, sin "
                  "ninguna via por donde un tercero pueda escribir. "
                  "La probabilidad sube el dia que se indexen "
                  "fuentes automaticas",
     "mitigacion": "Filtro de catorce patrones medido contra 48 "
                   "textos legitimos, 0 falsos positivos "
                   "(Bloque 31)",
     "supervision": ""},
]


for r in mis_riesgos:
    r["puntaje"] = puntaje_riesgo(r["probabilidad"], r["impacto"])
    r["categoria"] = categoria_riesgo(r["puntaje"])
    r["al_limite"] = esta_en_el_limite(r["probabilidad"],
                                       r["impacto"])


if __name__ == "__main__":
    print("--- la matriz, ordenada por severidad ---")
    for r in sorted(mis_riesgos, key=lambda x: -x["puntaje"]):
        marca = "[AL LIMITE]" if r["al_limite"] else ""
        print(f"{r['categoria']:8} ({r['puntaje']:2}) "
              f"p{r['probabilidad']} x i{r['impacto']} - "
              f"{r['riesgo']} {marca}")

    print()
    print("--- cuales conviene revisar con otra persona ---")
    for r in mis_riesgos:
        if r["al_limite"]:
            print("  ", r["riesgo"])

    # Las seis filas salen marcadas, y eso no es un fallo del
    # chequeo. Los cortes en 4, 9 y 15 estan juntos dentro del rango
    # de 1 a 25, asi que la mayoria de los puntajes intermedios
    # quedan a un punto de alguno. El caso de contraste confirma que
    # la funcion si distingue cuando hay margen.
    print()
    print("--- el caso de contraste, para ver que el chequeo "
          "distingue ---")
    p, i = 1, 1
    print(f"  probabilidad {p} x impacto {i} = "
          f"{puntaje_riesgo(p, i)}, {categoria_riesgo(puntaje_riesgo(p, i))}, "
          f"{'al limite' if esta_en_el_limite(p, i) else 'no al limite'}")
    assert not esta_en_el_limite(1, 1), (
        "si hasta el caso de contraste sale marcado, el chequeo "
        "esta mal, no la matriz"
    )

    print()
    print("--- el punto de supervision de los ALTO y CRITICO ---")
    for r in mis_riesgos:
        if r["categoria"] in ("ALTO", "CRITICO"):
            print(f"  {r['categoria']} - {r['riesgo']}")
            print(f"     -> {r['supervision']}")

    # --- Las tres exigencias de la actividad, comprobadas ----------

    print()
    print("--- las exigencias de la actividad ---")

    assert len(mis_riesgos) >= 5, "la actividad pide cinco como minimo"
    print(f"  {len(mis_riesgos)} riesgos, el minimo son 5")

    severos = [r for r in mis_riesgos
               if r["categoria"] in ("ALTO", "CRITICO")]
    assert severos, (
        "no hay ningun ALTO ni CRITICO. Revisa si estas "
        "subestimando la probabilidad o el impacto"
    )
    print(f"  {len(severos)} de categoria ALTO o CRITICO")

    sin_supervision = [r for r in severos if not r["supervision"]]
    assert not sin_supervision, (
        f"hay un riesgo severo sin punto de supervision, "
        f"{sin_supervision[0]['riesgo']!r}"
    )
    print("  todos los severos tienen punto de supervision")

    con_bloque = [r for r in mis_riesgos if "Bloque" in r["mitigacion"]]
    assert len(con_bloque) >= 2, (
        "la actividad pide que al menos dos mitigaciones apunten a "
        "algo ya construido, con su numero de bloque"
    )
    print(f"  {len(con_bloque)} mitigaciones apuntan a un bloque "
          f"construido, el minimo son 2")

    categorias = {r["categoria"] for r in mis_riesgos}
    assert len(categorias) > 1, (
        "todos los riesgos quedaron en la misma categoria, que es "
        "senal de haber puesto el mismo numero por costumbre"
    )
    print(f"  {len(categorias)} categorias distintas, "
          f"{', '.join(sorted(categorias))}")

    print()
    print("la matriz cumple las exigencias de la actividad")
