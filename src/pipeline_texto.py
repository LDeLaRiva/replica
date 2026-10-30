"""Pipeline de limpieza y tokenización de texto, y métricas.

limpiar_texto deja el texto parejo, tokenizar lo parte en palabras, y
procesar_texto hace las dos cosas de una sola llamada.

Sobre esas tres se calculan las métricas del Bloque 16. Precisión,
cobertura y F1, que miden cuánto se parece una respuesta generada a
una referencia escrita a mano.

Se corre desde la raíz del repositorio con
`python -m src.pipeline_texto`
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# La raíz se agrega a la ruta de búsqueda, igual que en cliente.py y en
# test_cliente.py. Con esto el archivo importa con el mismo prefijo src.
# que usa el resto del proyecto, y Python carga cada archivo una sola
# vez en vez de dos bajo dos nombres distintos.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Ninguna de las funciones de abajo usa el cliente. Solo lo necesita la
# demostración del final, que consulta al modelo de verdad.
from src.cliente import consultar_modelo                  # noqa: E402


# ===== El pipeline ====================================================

def limpiar_texto(texto: str) -> str:
    """Deja el texto en minúsculas, sin puntuación y sin espacios de sobra.

    El orden de los tres pasos importa y no se puede invertir. Quitar la
    puntuación crea espacios nuevos, porque al borrar la coma de
    "perro , y" quedan pegados el espacio de antes y el de después. Si
    los espacios se limpiaran primero, esos nuevos quedarían sin limpiar.

    Args:
        texto: el texto tal como llegó, sin normalizar.

    Returns:
        El mismo texto en minúsculas, sin signos y con un solo espacio
        entre palabras.

    Raises:
        TypeError: si lo que llega no es texto. Sin esta comprobación el
            error aparecería más abajo, en texto.lower(), como un
            AttributeError que no dice cuál fue el problema real.
    """
    if not isinstance(texto, str):
        tipo = type(texto).__name__
        raise TypeError(f"limpiar_texto espera str, no {tipo}")

    texto = texto.lower()
    # [^\w\s] es todo lo que no sea letra, número o espacio.
    # En Python 3 \w reconoce las tildes y la ñ.
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar(texto_limpio: str) -> list[str]:
    """Parte un texto ya limpio en la lista de sus palabras.

    Separar por espacios alcanza porque el texto ya pasó por
    limpiar_texto.

    Args:
        texto_limpio: el texto que devolvió limpiar_texto.

    Returns:
        La lista de palabras. Un texto que era solo puntuación devuelve
        una lista vacía, no un error.
    """
    return texto_limpio.split()


def procesar_texto(texto: str) -> list[str]:
    """Limpia y tokeniza en un solo paso.

    Es la función que conviene usar siempre, en vez de llamar a las dos
    por separado. Centralizar los dos pasos evita que alguien aplique
    uno y olvide el otro antes de calcular una métrica.

    Args:
        texto: el texto tal como llegó, sin normalizar.

    Returns:
        La lista de palabras ya normalizadas.

    Raises:
        TypeError: el que lanza limpiar_texto si no recibe texto.
    """
    return tokenizar(limpiar_texto(texto))


def vectorizar(tokens: list[str]) -> Counter:
    """Cuenta cuántas veces aparece cada palabra.

    Lo que agrega sobre contar con un conjunto es que distingue
    "aparece una vez" de "aparece dos veces". Para un conjunto, "el
    gato el gato" y "el gato" son lo mismo. Para este conteo no.

    Es la idea que contar_coincidencias lleva un paso más allá, usando
    la intersección de dos conteos en vez de uno solo.

    Args:
        tokens: la lista de palabras que devolvió procesar_texto.

    Returns:
        Un Counter con cada palabra distinta y su cantidad. Una lista
        vacía devuelve un Counter vacío, no un error.
    """
    return Counter(tokens)


# ===== Las métricas ===================================================

def contar_coincidencias(
    tokens_referencia: list[str],
    tokens_respuesta: list[str],
) -> int:
    """Cuenta las coincidencias entre referencia y respuesta."""
    conteo_referencia = Counter(tokens_referencia)
    conteo_respuesta = Counter(tokens_respuesta)
    interseccion = conteo_referencia & conteo_respuesta
    return sum(interseccion.values())


def calcular_precision_cobertura_f1(
    tokens_referencia: list[str],
    tokens_respuesta: list[str],
) -> dict[str, float]:
    """Calcula precisión, cobertura y F1 de dos listas de tokens."""
    coincidencias = contar_coincidencias(
        tokens_referencia, tokens_respuesta
    )

    if not tokens_respuesta or not tokens_referencia:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

    precision = coincidencias / len(tokens_respuesta)
    cobertura = coincidencias / len(tokens_referencia)

    if precision + cobertura == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * cobertura / (precision + cobertura)

    resultado = {
        "precision": precision,
        "cobertura": cobertura,
        "f1": f1,
    }

    return resultado


def calcular_metricas(texto_referencia, texto_respuesta):
    """Procesa los dos textos y devuelve sus métricas, de una llamada."""
    tokens_referencia = procesar_texto(texto_referencia)
    tokens_respuesta = procesar_texto(texto_respuesta)
    return calcular_precision_cobertura_f1(
        tokens_referencia, tokens_respuesta
    )


def resumir_metricas(resultados):
    """Promedia precisión, cobertura y F1 de una lista de resultados."""
    if not resultados:
        return {
            "precision_promedio": 0,
            "cobertura_promedio": 0,
            "f1_promedio": 0,
        }
    n = len(resultados)
    return {
        "precision_promedio": sum(
            r["precision"] for r in resultados
        ) / n,
        "cobertura_promedio": sum(
            r["cobertura"] for r in resultados
        ) / n,
        "f1_promedio": sum(r["f1"] for r in resultados) / n,
    }


if __name__ == "__main__":
    # El módulo no usa colores, solo esta demostración.
    from src.contraste import *                       # noqa: E402, F403

    # El archivo de resultados queda al lado de este script, igual que
    # registro_resultados.json queda al lado de test_consistencia.py.
    # La ruta se arma desde __file__ y no desde la carpeta actual, para
    # que caiga siempre en el mismo lugar sin importar desde dónde se
    # lance el programa.
    RUTA_RESULTADOS = Path(__file__).resolve().parent / \
        "resultados_metricas.json"

    # ===== Primera parte, el pipeline a solas ========================
    #
    # Las cuatro funciones sobre una frase conocida, sin salir a
    # internet y sin gastar cuota. Es el ejemplo de la lección y su
    # salida está documentada ahí, así que sirve para confirmar de una
    # mirada que el pipeline quedó bien.

    EJEMPLO = "El gato, el perro y el gato corren."

    titulobn("\nEl pipeline paso a paso")
    notabn("\nSobre una frase de ejemplo, sin consultar al modelo.")

    ejemplo_limpio = limpiar_texto(EJEMPLO)
    ejemplo_tokens = tokenizar(ejemplo_limpio)
    ejemplo_conteo = vectorizar(ejemplo_tokens)

    salbn(f"\n  Texto     {EJEMPLO}")
    salbn(f"  Limpio    {ejemplo_limpio}")
    salbn(f"  Tokens    {ejemplo_tokens}")
    salbn(f"  Conteo    {ejemplo_conteo}")

    notabn("\n  El 3 del artículo es lo que un conjunto no sabría "
           "decir.\n  Para set() esa palabra aparece, y nada más.")

    # ===== Segunda parte, sobre respuestas reales ====================
    #
    # Consultas que sí gastan cuota. Son tres, y cada una se usa para
    # las dos mediciones. La del Bloque 15, que compara el texto crudo
    # contra el procesado, y la del Bloque 16, que calcula precisión,
    # cobertura y F1. Preguntar dos veces lo mismo costaría el doble
    # sin agregar nada.

    # La referencia es lo que esperamos que conteste, escrita a mano, y
    # es contra eso que se compara la respuesta real del modelo.
    #
    # Los tres datos están verificados contra la Dirección del Trabajo.
    # El de la jornada cambió en abril de 2026, así que es posible que
    # el modelo conteste 45 o 40 horas. Si pasa, no es una falla del
    # ejercicio, es un hallazgo sobre lo desactualizado que puede estar.
    CASOS = [
        ("¿Cuántos días de permiso por fallecimiento de un hijo "
         "establece el Código del Trabajo chileno?",
         "El trabajador tiene derecho a diez días corridos de permiso "
         "pagado, adicionales al feriado anual."),

        ("¿Cuántas horas semanales dura la jornada ordinaria de "
         "trabajo en Chile?",
         "Desde abril de 2026, la jornada ordinaria de trabajo no "
         "puede exceder de cuarenta y dos horas semanales."),

        ("¿Cuántos días de feriado anual corresponden a un trabajador "
         "con más de un año de servicio?",
         "El trabajador con más de un año de servicio tiene derecho a "
         "quince días hábiles de feriado anual."),
    ]

    # La instrucción pide brevedad a propósito. La precisión divide las
    # coincidencias por el largo de la respuesta, así que una respuesta
    # larga la hunde aunque diga lo correcto.
    INSTRUCCION = ("Responde en una sola oración breve, en español y "
                   "sin viñetas.")

    titulobn("\nEl pipeline sobre respuestas reales")
    notabn(f"\nSe hacen {len(CASOS)} consultas al modelo y se compara "
           f"cada respuesta\ncontra una referencia escrita a mano.")

    consultados = 0
    cambiados = 0
    resultados = []

    for numero, (pregunta, referencia) in enumerate(CASOS, 1):
        titulofn(f"\nCaso {numero}")
        salbn(f"\n  Pregunta\n    {pregunta}")
        salbn(f"\n  Referencia, escrita a mano\n    {referencia}")

        try:
            respuesta = consultar_modelo(pregunta, INSTRUCCION)
        except (ValueError, RuntimeError) as fallo:
            # Se informa y se sigue con el resto. Una consulta que falló
            # no tiene por qué botar las otras dos, que ya se pagaron.
            errorbn(f"\n  El caso {numero} no se pudo consultar.")
            avisofn(f"\n{fallo}")
            continue

        consultados += 1
        exitobn(f"\n  Respuesta del modelo\n    {respuesta}")

        # El antes.
        # Se parte por espacios, sin limpiar nada, que es el error
        # a evitar.
        crudo_ref = referencia.split()
        crudo_resp = respuesta.split()
        comunes_crudo = set(crudo_ref) & set(crudo_resp)
        if crudo_ref:
            pct_crudo = len(comunes_crudo) / len(set(crudo_ref))
        else:
            pct_crudo = 0.0

        # El después.
        # El mismo cálculo, con los dos lados procesados.
        # Procesar un solo lado dejaría la comparación igual de
        # torcida. Se escribe completo y no en una función, para que
        # la única diferencia entre los dos bloques sea visible.
        tokens_ref = procesar_texto(referencia)
        tokens_resp = procesar_texto(respuesta)
        comunes = set(tokens_ref) & set(tokens_resp)
        if tokens_ref:
            pct_proc = len(comunes) / len(set(tokens_ref))
        else:
            pct_proc = 0.0

        diferencia = pct_proc - pct_crudo
        if diferencia != 0:
            cambiados += 1

        lilafn("\n  Coincidencia por conjuntos, Bloque 15")
        lilabn(f"    Texto crudo        {pct_crudo:.1%}")
        lilabn(f"    Texto procesado    {pct_proc:.1%}")
        lilabn(f"    Diferencia         {diferencia:+.1%}")

        # Las métricas del Bloque 16, sobre la misma respuesta.
        metricas = calcular_metricas(referencia, respuesta)

        lilafn("\n  Métricas por conteo, Bloque 16")
        lilabn(f"    Precisión          {metricas['precision']:.3f}")
        lilabn(f"    Cobertura          {metricas['cobertura']:.3f}")
        lilabn(f"    F1                 {metricas['f1']:.3f}")

        # La referencia se guarda junto con la respuesta, además de lo
        # que pide la lección. Sin ella, al volver a leer el archivo no
        # hay con qué juzgar si la respuesta estuvo bien, que es justo
        # lo que el Bloque 17 va a pedir hacer.
        resultados.append({
            "consulta": pregunta,
            "referencia": referencia,
            "respuesta": respuesta,
            **metricas,
        })

    # ===== Tercera parte, el resumen =================================

    titulofn("\nQué cambió el pipeline")
    salfn(f"  En {cambiados} de {consultados} casos consultados, la "
          f"coincidencia por\n  conjuntos cambió al normalizar el "
          f"texto antes de comparar.")

    if cambiados == 0 and consultados > 0:
        # Puede pasar si las dos oraciones terminan en la misma palabra
        # y no hay comas de por medio. No invalida el pipeline, pero
        # deja el registro sin la evidencia que pide la actividad.
        avisobn("\n  Ninguna medición cambió en esta corrida. Conviene "
                "volver a\n  correrla, porque el modelo no contesta "
                "igual dos veces.")

    resumen = resumir_metricas(resultados)

    titulofn("\nPromedio de las métricas")
    salfn(f"  Precisión   {resumen['precision_promedio']:.3f}\n"
          f"  Cobertura   {resumen['cobertura_promedio']:.3f}\n"
          f"  F1          {resumen['f1_promedio']:.3f}")
    notabn("\n  Un promedio no dice si hay tres respuestas regulares o "
           "dos\n  buenas y una mala. Para eso está la lista de abajo.")

    # Ordenadas de peor a mejor. Revisar primero las peores rinde más
    # que revisarlas en el orden en que se generaron. Se muestran las
    # tres peores, que con tres casos son todas.
    titulofn("\nLos peores casos, por F1")
    peores_casos = sorted(resultados, key=lambda r: r["f1"])
    for caso in peores_casos[:3]:
        # La pregunta se corta en la última palabra que entra, para
        # que la línea no se parta en dos. Completa ya aparece más
        # arriba, en el detalle de cada caso.
        consulta = caso["consulta"]
        if len(consulta) > 50:
            consulta = consulta[:50].rsplit(" ", 1)[0] + "..."
        salfn(f"  {caso['f1']:.3f}   {consulta}")

    # ===== El archivo ================================================

    if resultados:
        with open(RUTA_RESULTADOS, "w", encoding="utf-8") as archivo:
            json.dump(resultados, archivo, indent=2, ensure_ascii=False)
        exitobn(f"\nResultados guardados en {RUTA_RESULTADOS.name}")
    else:
        avisobn("\nNo hubo resultados que guardar.")

    titulofn("\nQué no mide este número")
    salfn("  No mide si la respuesta es correcta. Mide cuántas "
          "palabras de\n  la referencia aparecen en ella. Una respuesta "
          "a la que solo le\n  falta un \"no\" puede sacar 0.909 y "
          "decir lo contrario.")
    salfn("  Tampoco entiende sinónimos. Decir lo mismo con otras "
          "palabras\n  baja la nota, aunque la respuesta sea correcta.")

    titulobn("\nFin del registro")
