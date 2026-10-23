"""Punto de entrada de la miniaplicación de consultas laborales.

Hace una consulta real usando un prompt del banco y muestra la
respuesta ya convertida en diccionario de Python.

El manejo de errores vive aquí, en el borde, porque es el único
lugar que sabe cómo mostrarle algo a la persona que usa el programa.

Se ejecuta desde la raíz del repositorio con:
    python main.py
"""

from prompts.banco import BANCO_DE_PROMPTS
from src.consumir_gemini import (
    PRECIO_ENTRADA,
    PRECIO_SALIDA,
    armar_peticion,
    calcular_costo_peticion,
    enviar_peticion,
    extraer_texto,
    parsear_respuesta_json,
)
from src.contraste import *

# Para probar otro prompt del banco se cambian estas dos
# constantes. El resto del archivo no cambia.
PREGUNTA = ("¿Cuántos días de permiso me corresponden por el "
            "fallecimiento de un hijo?")
NOMBRE_PROMPT = "responder_consulta"

try:
    # Se busca por nombre y no por posición, para que siga
    # funcionando si mañana el banco cambia de orden.
    prompt = next(
        (p for p in BANCO_DE_PROMPTS
         if p["nombre"] == NOMBRE_PROMPT), None)

    if prompt is None:
        # Este error solo lo puede provocar quien programa, al
        # escribir mal la constante. No lleva mensaje para el
        # usuario porque no hay un usuario que pueda hacer algo.
        disponibles = ", ".join(
            p["nombre"] for p in BANCO_DE_PROMPTS)
        raise ValueError(
            f"[técnico] El banco no tiene un prompt llamado "
            f"{NOMBRE_PROMPT}. Los disponibles son {disponibles}.")

    url, headers, body = armar_peticion(
        PREGUNTA,
        prompt["system_instruction"],
        prompt.get("response_schema"))

    respuesta = enviar_peticion(url, headers, body)
    texto = extraer_texto(respuesta)
    datos = parsear_respuesta_json(texto, prompt["claves_esperadas"])
    costo = calcular_costo_peticion(
        respuesta, PRECIO_ENTRADA, PRECIO_SALIDA)

    titulobn(f"\nConsulta\n  {PREGUNTA}")

    # El tipo va en las dos líneas porque mirándolos no se
    # distinguen. El crudo es un string escrito en formato JSON,
    # no un tipo JSON, que en Python no existe.
    salbn(f"\nTexto crudo, tal como llegó   {type(texto)}"
          f"\n  {texto}")

    exitobn(f"\nYa convertido en diccionario   {type(datos)}")
    exitot(datos)

    # Consumo de esta llamada. Es información de desarrollo, igual
    # que la línea [técnico] de los errores, y cuando se separe lo
    # que ve el usuario se va con el lado técnico. El total lo
    # informa la API y no siempre es la suma de los otros dos,
    # porque puede incluir tokens que no se desglosan.
    uso = respuesta["usageMetadata"]
    lilabn("\nConsumo de esta petición")
    lilabn(f"  Tokens de entrada  {uso['promptTokenCount']}")
    lilabn(f"  Tokens de salida   {uso['candidatesTokenCount']}")
    lilabn(f"  Total de tokens    "
           f"{uso.get('totalTokenCount', 'no informado')}")
    lilabn(f"  Costo estimado     {costo:.8f} USD")
    notabn("\nProceso terminado.")

except (ValueError, RuntimeError) as fallo:
    avisofn(f"\n{fallo}")

except Exception as fallo:
    errorfn(f"\nError inesperado. {type(fallo).__name__}")
    avisofn(f"\n{fallo}")