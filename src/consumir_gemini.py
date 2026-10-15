import os
import requests
from dotenv import load_dotenv

load_dotenv()


def obtener_dato_de_prueba(pregunta):
   
    api_key_gemini = os.getenv("AI_API_KEY")
    modelo = "gemini-3.5-flash-lite"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"x-goog-api-key": api_key_gemini}
    body = {
        "contents": [
            {"parts": [{"text": pregunta}]}
        ]
    }

    respuesta = requests.post(url, headers=headers, json=body)
    #print(respuesta.status_code)
    #print(respuesta.text)
    datos = respuesta.json()
    return datos["candidates"][0]["content"]["parts"][0]["text"]


respuesta_gemini = (obtener_dato_de_prueba("explicame que es json en 20 palabras"))

print(f"La respuesta de Gemini es:\n{respuesta_gemini}")