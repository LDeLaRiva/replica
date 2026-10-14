import os
import requests
from dotenv import load_dotenv

load_dotenv()


def request_prueba(pregunta):
   
    api_key = os.getenv("AI_API_KEY")
    modelo = "gemini-3.5-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"x-goog-api-key": api_key}
    body = {
        "contents": [
            {"parts": [{"text": pregunta}]}
        ]
    }

    respuesta = requests.post(url, headers=headers, json=body)
    datos = respuesta.json()
    return datos["candidates"][0]["content"]["parts"][0]["text"]


print(request_prueba("explicame que es json en 20 palabras"))