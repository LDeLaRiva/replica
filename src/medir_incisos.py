"""Medición de la partición por inciso (Bloque 28).

Respalda las dos decisiones de indexación que se tomaron en el Bloque
28. Separar los incisos con línea en blanco, y subir el tope de
setecientos a mil trescientos.

Qué problema mide. El corpus separa sus incisos con un salto de línea,
igual que separa las letras a) y b) de adentro de un inciso. El
splitter prefiere cortar en línea en blanco y después en salto simple,
de modo que sin esa distinción trata el borde entre dos incisos igual
que el borde entre dos letras, y corta en cualquiera de los dos.

Un fragmento que empieza a media oración o en una letra suelta llega
al modelo sin decir de qué inciso viene ni bajo qué condición se
aplica. Si ese inciso tenía una condición en su encabezado, la regla
viaja sin ella.

Qué imprime. El largo de cada unidad estructural del corpus, cuántos
fragmentos empiezan a media unidad con cada configuración, y cuáles
son.

De ahí sale el criterio del tope. No es un número elegido, es que el
tope no puede quedar por debajo de la unidad estructural más larga
del corpus. La más larga mide 1057 caracteres y la medición muestra
que desde 1057 las cuarenta y nueve unidades caben enteras, así que
el piso es ese valor y no uno más. Cuando el corpus crezca se vuelve
a correr esto y se ajusta.

El piso es un piso y no el valor entregado. Cuál de los topes por
encima del piso se adopta se decide con otras cuatro mediciones, y
está en la cabecera de indexar_corpus.py.

Lo que midió esta medición está escrito en docs/limites_bloque28.md,
junto con las referencias de la práctica publicada en textos legales.

No consume API. Solo parte el corpus en memoria, que es local y no
cuesta nada.

Se corre desde la raíz del proyecto con
`python src/medir_incisos.py`.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indexar_corpus import (
    ETIQUETA,
    SOLAPE,
    TOPE,
    fragmentar,
    separar_incisos,
)
from soporte_corpus_legal import ARTICULOS

# Un fragmento que empieza con el rótulo de un artículo, con un
# inciso [n] o con una causal numerada N.- empieza donde empieza una
# unidad. Cualquier otro comienzo es a media unidad.
INICIO_LIMPIO = re.compile(r"^(?:\[\d+\]|Art\.|Artículo|\d+\.-)")

# Los topes que se compararon. El de hoy va marcado al imprimir.
# El 1057 está en la lista porque es el piso exacto, el valor donde
# las cuarenta y nueve unidades empiezan a caber enteras. Es el
# número en que se apoya todo el criterio del tope, así que la
# medición lo muestra en vez de dejarlo entre el 1000 y el 1100.
TOPES = (700, 1000, 1056, 1057, 1100, 1300, 1500, 2000)

# La proporción de solape, la misma que usaba la configuración
# anterior y la que usa la de ahora.
PROPORCION_SOLAPE = 0.18

ANCHO = 56


def articulos_con_etiqueta():
    """Devuelve el texto de cada artículo con su número, sin separar."""
    salida = []
    for claves, texto in ARTICULOS:
        calce = ETIQUETA.match(texto)
        etiqueta = calce.group(1).strip() if calce else "sin etiqueta"
        salida.append((etiqueta, texto, {"articulo": etiqueta}))
    return salida


def unidades_de(texto):
    """Parte un artículo en sus unidades estructurales."""
    return [
        parte.strip()
        for parte in separar_incisos(texto).split("\n\n")
        if parte.strip()
    ]


def huerfanos_de(articulos, tope, solape, separar):
    """Cuenta los fragmentos que empiezan a media unidad.

    Devuelve el total de fragmentos y la lista de los que empiezan
    donde no empieza ninguna unidad.
    """
    total, sueltos = 0, []
    for etiqueta, texto, metadato in articulos:
        preparado = separar_incisos(texto) if separar else texto
        fragmentos = fragmentar([preparado], [metadato], tope, solape)
        total += len(fragmentos)
        for posicion, fragmento in enumerate(fragmentos):
            limpio = fragmento.page_content.lstrip()
            if not INICIO_LIMPIO.match(limpio):
                sueltos.append((etiqueta, posicion, len(limpio),
                                limpio[:ANCHO]))
    return total, sueltos


def main():
    articulos = articulos_con_etiqueta()

    print(f"\n  articulos en el corpus   {len(articulos)}")
    print(f"  configuracion de hoy     tope {TOPE}, solape {SOLAPE}")

    print("\n" + "=" * 72)
    print("  LAS UNIDADES ESTRUCTURALES Y SU LARGO")
    print("=" * 72)

    unidades = []
    for etiqueta, texto, _ in articulos:
        for pieza in unidades_de(texto):
            unidades.append((etiqueta, len(pieza)))
    unidades.sort(key=lambda par: -par[1])

    print(f"\n  unidades en total   {len(unidades)}")
    print(f"  la mas larga        {unidades[0][1]} caracteres, "
          f"art. {unidades[0][0]}")
    print("\n  las cinco mas largas")
    for etiqueta, largo in unidades[:5]:
        print(f"      art. {etiqueta:<12}{largo:>6} caracteres")

    print("\n  cuantas caben enteras segun el tope")
    for tope in TOPES:
        caben = len([1 for _, largo in unidades if largo <= tope])
        marca = "   <-- el de hoy" if tope == TOPE else ""
        print(f"      tope {tope:>4}   {caben:>3} de {len(unidades)}"
              f"   {caben / len(unidades):>4.0%}{marca}")

    print("\n" + "=" * 72)
    print("  FRAGMENTOS QUE EMPIEZAN A MEDIA UNIDAD")
    print("=" * 72)
    print(f"\n  {'configuracion':<34}{'fragmentos':>12}{'a media':>10}")
    print("  " + "-" * 56)

    total, sueltos = huerfanos_de(articulos, 700, 126, separar=False)
    print(f"  {'tope 700, sin separar incisos':<34}{total:>12}"
          f"{len(sueltos):>10}")
    antes = list(sueltos)

    for tope in TOPES:
        solape = int(tope * PROPORCION_SOLAPE)
        total, sueltos = huerfanos_de(articulos, tope, solape,
                                      separar=True)
        marca = "  <-- el de hoy" if tope == TOPE else ""
        print(f"  {f'tope {tope}, separando incisos':<34}{total:>12}"
              f"{len(sueltos):>10}{marca}")

    print("\n" + "=" * 72)
    print("  LOS DE LA CONFIGURACION ANTERIOR, UNO POR UNO")
    print("=" * 72)
    print("\n  Son los que motivaron el cambio. Cada uno llega al")
    print("  modelo sin decir de que inciso viene.\n")
    print(f"  {'articulo':<12}{'frag':>5}{'car':>6}   empieza en")
    print("  " + "-" * 68)
    for etiqueta, posicion, largo, inicio in antes:
        print(f"  {etiqueta:<12}{posicion:>5}{largo:>6}   {inicio!r}")

    print("\n" + "=" * 72)
    print("  LA CONFIGURACION DE HOY")
    print("=" * 72)
    total, sueltos = huerfanos_de(articulos, TOPE, SOLAPE, separar=True)
    print(f"\n  fragmentos            {total}")
    print(f"  a media unidad        {len(sueltos)}")
    if sueltos:
        print("\n  Quedan estos, y hay que mirarlos.")
        for etiqueta, posicion, largo, inicio in sueltos:
            print(f"      art. {etiqueta:<12}{inicio!r}")
    else:
        print("\n  Ninguno. Todos los fragmentos empiezan donde empieza")
        print("  una unidad, asi que ninguna regla llega separada de la")
        print("  condicion que vive en el encabezado de su inciso.")
    print()


if __name__ == "__main__":
    main()
