"""Lectura del registro de latencia y costo (Bloque 28).

Lee el archivo que deja registro_rag.py y muestra el historial de
corridas, para comparar cómo cambian los tiempos y los tokens cuando
se toca algún parámetro del flujo.

Se corre desde la raíz del proyecto con
`python src/leer_registros.py`.

No consume API. Solo lee un archivo de texto.

Por qué el formato es una línea por corrida

El archivo es JSON Lines. Cada línea es un objeto JSON completo y no
un elemento de una lista, así que se puede leer de a un registro sin
parsear el archivo entero, y agregar una corrida nueva no obliga a
reescribir las anteriores.

Por qué las comprobaciones van en código

La actividad pide revisar a simple vista que la generación sea la
etapa más lenta. Hacerlo en código es el mismo criterio que se usó
en el Bloque 26 con la frase de abstención. A ojo, sobre un archivo
que va a ir creciendo corrida tras corrida, eso deja de ser revisable
bastante rápido.

La ruta del archivo se importa de registro_rag.py y no se escribe de
nuevo. Escrita dos veces, el día que una cambie la otra apuntaría a
un archivo que no existe.
"""

import json
import os

from registro_rag import ARCHIVO_REGISTRO

# Las claves que registro_rag.py escribe en cada línea. Si una línea
# no las trae todas, el archivo se editó a mano o lo escribió otra
# versión del script, y conviene saberlo antes de armar la tabla.
CLAVES = (
    "timestamp",
    "pregunta",
    "k",
    "tiempos_ms",
    "tiempo_total_ms",
    "tokens",
)


def leer(ruta=ARCHIVO_REGISTRO):
    """Devuelve los registros del archivo, en el orden en que se escribieron.

    Avisa qué línea está rota en vez de reventar con un error de JSON
    sin número, porque una línea mal escrita no debería impedir saber
    cuál es.

    Revisa además que cada línea traiga las claves del registro. Una
    línea con JSON válido pero incompleta reventaría más adelante, al
    armar la tabla, con un error que no dice de qué línea vino.
    """
    if not os.path.exists(ruta):
        raise SystemExit(
            f"No existe {ruta}. Corre primero "
            "python src/registro_rag.py"
        )

    registros, rotas, incompletas = [], [], []
    with open(ruta, encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, start=1):
            if not linea.strip():
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                rotas.append(numero)
                continue
            faltan = [c for c in CLAVES if c not in registro]
            if faltan:
                incompletas.append((numero, faltan))
                continue
            registros.append(registro)

    if rotas:
        raise SystemExit(
            f"Hay líneas que no son JSON válido en {ruta}, las "
            f"número {rotas}. Revísalas antes de seguir."
        )

    if incompletas:
        detalle = "\n".join(
            f"  línea {numero}, le faltan {', '.join(faltan)}"
            for numero, faltan in incompletas
        )
        raise SystemExit(
            f"Hay líneas a las que les faltan claves del registro en "
            f"{ruta}.\n{detalle}"
        )

    if not registros:
        raise SystemExit(
            f"{ruta} existe pero no tiene ninguna corrida. Corre "
            "python src/registro_rag.py"
        )

    return registros


def tokens_de(registro, clave):
    """Saca un conteo de tokens del registro, o None si no vino."""
    tokens = registro.get("tokens")
    return tokens.get(clave) if tokens else None


def particion_de(registro):
    """Devuelve el tope y el solape con que se midió esa corrida.

    Las corridas anteriores al Bloque 28 no guardaban la partición,
    así que para esas se informa que no consta en vez de suponerla.
    """
    tope, solape = registro.get("tope"), registro.get("solape")
    if tope is None or solape is None:
        return "no consta"
    return f"{tope}/{solape}"


def mostrar(registros):
    """Imprime una línea por corrida, con su partición y sus tokens."""
    print(f"  {'#':>3}  {'k':>3}  {'tope/sol':>10}  {'entrada':>8}  "
          f"{'salida':>7}  {'total ms':>9}  pregunta")
    print("  " + "-" * 76)
    for numero, registro in enumerate(registros, start=1):
        entrada = tokens_de(registro, "input_tokens")
        salida = tokens_de(registro, "output_tokens")
        print(
            f"  {numero:>3}  {registro['k']:>3}  "
            f"{particion_de(registro):>10}  "
            f"{'n/a' if entrada is None else entrada:>8}  "
            f"{'n/a' if salida is None else salida:>7}  "
            f"{registro['tiempo_total_ms']:>9.2f}  "
            f"{registro['pregunta'][:28]}"
        )


def comparar_por_k(registros):
    """Muestra, para cada pregunta repetida, cómo movió el k los tokens.

    Solo mira las preguntas que aparecen con más de un k. Son las que
    sirven para la comprobación que pide la actividad, porque
    comparar tokens entre preguntas distintas no dice nada.
    """
    por_pregunta = {}
    for registro in registros:
        entrada = tokens_de(registro, "input_tokens")
        if entrada is None:
            continue
        # la clave lleva la particion, porque comparar el k entre dos
        # particiones distintas no dice nada sobre el k
        clave = (registro["pregunta"], particion_de(registro))
        por_pregunta.setdefault(clave, {})[registro["k"]] = entrada

    repetidas = {
        clave: valores
        for clave, valores in por_pregunta.items()
        if len(valores) > 1
    }

    if not repetidas:
        print("  ninguna pregunta se corrió con dos k distintos")
        print("  en la misma partición todavía")
        return

    for (pregunta, particion), valores in repetidas.items():
        print(f"  {pregunta[:52]}   particion {particion}")
        anterior_k = anterior_tokens = None
        for k in sorted(valores):
            entrada = valores[k]
            if anterior_tokens is None:
                print(f"      k={k}  entrada={entrada}")
            else:
                dif = entrada - anterior_tokens
                print(f"      k={k}  entrada={entrada}  "
                      f"({dif:+d} contra k={anterior_k})")
            anterior_k, anterior_tokens = k, entrada
        print()


def revisar_etapas(registros):
    """Confirma que la generación sea la etapa más lenta de cada corrida."""
    lentas = []
    for numero, registro in enumerate(registros, start=1):
        tiempos = registro.get("tiempos_ms", {})
        if "generacion" not in tiempos or "embed_y_busqueda" not in tiempos:
            continue
        if tiempos["generacion"] <= tiempos["embed_y_busqueda"]:
            lentas.append((numero, tiempos))

    if not lentas:
        print(f"  la generación fue la etapa más lenta en las "
              f"{len(registros)} corridas")
        return

    print("  hay corridas donde la generación NO fue la más lenta")
    for numero, tiempos in lentas:
        print(f"      corrida {numero}, "
              f"embed+busqueda {tiempos['embed_y_busqueda']} ms, "
              f"generación {tiempos['generacion']} ms")


def promedios(registros):
    """Promedia cada etapa, separando por partición.

    Devuelve un diccionario de partición a etapas, y no un promedio
    único. Promediar corridas de particiones distintas junta
    mediciones que no se comparan, y el Bloque 28 dejó la razón
    escrita. Entre dos corridas de la misma configuración separadas
    por cuatro minutos, la generación de una consulta pasó de 8709 a
    1127 milisegundos. El tiempo de generación lo mueve la API, así
    que un promedio que mezcla configuraciones no dice nada sobre
    ninguna de ellas.
    """
    por_particion = {}
    for registro in registros:
        clave = particion_de(registro)
        etapas = por_particion.setdefault(clave, {})
        for etapa, milisegundos in registro.get("tiempos_ms", {}).items():
            etapas.setdefault(etapa, []).append(milisegundos)

    return {
        particion: {
            etapa: (sum(valores) / len(valores), len(valores))
            for etapa, valores in etapas.items()
        }
        for particion, etapas in por_particion.items()
    }


if __name__ == "__main__":
    registros = leer()

    print(f"\n  Archivo     {ARCHIVO_REGISTRO}")
    print(f"  Corridas    {len(registros)}")
    sin_tokens = len([r for r in registros if not r.get("tokens")])
    print(f"  Sin tokens  {sin_tokens}")
    if sin_tokens:
        print("  Esas consultas no devolvieron datos de uso. No es un")
        print("  error de la instrumentación, es que la llamada no los")
        print("  trajo.")

    print("\n" + "=" * 70)
    print("  EL HISTORIAL")
    print("=" * 70 + "\n")
    mostrar(registros)

    print("\n" + "=" * 70)
    print("  LO QUE MUEVE EL K")
    print("=" * 70 + "\n")
    comparar_por_k(registros)

    print("=" * 70)
    print("  LAS ETAPAS")
    print("=" * 70 + "\n")
    revisar_etapas(registros)

    medias = promedios(registros)
    if medias:
        print("\n  Promedio por etapa, separado por particion")
        for particion in sorted(medias):
            etapas = medias[particion]
            cuantas = max(cantidad for _, cantidad in etapas.values())
            print(f"\n      tope/solape {particion}, {cuantas} corridas")
            for etapa, (milisegundos, _) in sorted(
                    etapas.items(), key=lambda par: -par[1][0]):
                print(f"        {etapa:<20}{milisegundos:>10.2f} ms")
        if len(medias) > 1:
            print("\n      No se promedian las particiones juntas. El")
            print("      tiempo de generacion lo mueve la API, medido en")
            print("      la seccion 4 del docs/limites_bloque28.md, asi")
            print("      que un promedio que las mezcle no describe a")
            print("      ninguna.")
    print()
