"""Punto de entrada de la miniaplicación.

Hace una consulta al modelo y muestra la respuesta. El manejo de
errores vive aquí, en el borde, porque es el único lugar que sabe
cómo mostrarle algo a la persona que está usando el programa.
"""

from src.consumir_gemini import obtener_dato_de_prueba, INSTRUCCION
from src.contraste import *

try:
    respuesta_gemini, _, _ = obtener_dato_de_prueba(
        "¿Cuál es la capital de Inglaterra?",
        INSTRUCCION)

    titulobn(f"\nLa respuesta de Gemini es:\n{respuesta_gemini}")

except (ValueError, RuntimeError) as fallo:
    avisofn(f"\n{fallo}")

except Exception as fallo:
    errorfn(f"\nError inesperado. {type(fallo).__name__}")
    avisofn(f"\n{fallo}")