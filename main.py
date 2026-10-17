from src.consumir_gemini import obtener_dato_de_prueba
from src.contraste import *

respuesta_gemini = obtener_dato_de_prueba("¿Cuál es la capital de Inglaterra?")

salbn(f"\nLa respuesta de Gemini es:\n{respuesta_gemini}")