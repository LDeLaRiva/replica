import os
import requests
from dotenv import load_dotenv
from cprint import cprint
from contraste import *

load_dotenv()


def armar_peticion(pregunta):
    api_key_gemini = os.getenv("AI_API_KEY")
    modelo = os.getenv("AI_MODEL")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"x-goog-api-key": api_key_gemini}
    body = {
        "contents": [
            {"parts": [{"text": pregunta}]}
        ]
    }
    return url, headers, body


def enviar_peticion(url, headers, body):
    respuesta = requests.post(url, headers=headers, json=body)
    return respuesta.json()


def extraer_texto(datos):
    return datos["candidates"][0]["content"]["parts"][0]["text"]


def obtener_dato_de_prueba(pregunta):
    url, headers, body = armar_peticion(pregunta)
    datos = enviar_peticion(url, headers, body)
    return extraer_texto(datos)


if __name__ == "__main__":
    respuesta_gemini = obtener_dato_de_prueba("explicame que es json en 20 palabras")
    print(f"\nLa respuesta de Gemini es:\n{respuesta_gemini}")
    salfn(f"\nLa respuesta de Gemini es:\n{respuesta_gemini}")
