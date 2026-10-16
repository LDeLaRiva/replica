import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------- ANTES, Bloque 5 ----------

def obtener_dato_de_prueba_monolitica(pregunta):   
    api_key_gemini = os.getenv("AI_API_KEY")
    modelo = os.getenv("AI_MODEL")
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


respuesta_gemini = (obtener_dato_de_prueba_monolitica("explicame que es json en 20 palabras"))

print(f"La respuesta de Gemini es:\n{respuesta_gemini}")



# Archivo de referencia del Bloque 6, no es parte del módulo.
# Guarda una foto de las dos versiones, la monolítica del Bloque 5
# y la refactorizada del Bloque 6, para comprobar que dan el mismo resultado.
# El módulo real es src/consumir_gemini.py



# ---------- DESPUES, Bloque 6 ----------

def armar_peticion(pregunta):
    """Deja lista la petición, con su dirección, su encabezado y su cuerpo."""
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
    """Envía la petición y devuelve la respuesta ya convertida a diccionario."""
    respuesta = requests.post(url, headers=headers, json=body)
    return respuesta.json()


def extraer_texto(datos):
    """Recorre la respuesta de Gemini y devuelve solo el texto generado."""
    return datos["candidates"][0]["content"]["parts"][0]["text"]


def obtener_dato_de_prueba(pregunta):
    """Coordina las tres funciones anteriores y devuelve el texto generado."""
    url, headers, body = armar_peticion(pregunta)
    datos = enviar_peticion(url, headers, body)
    return extraer_texto(datos)


# ---------- La comprobación ----------

if __name__ == "__main__":
    pregunta = "explicame que es json en 20 palabras"

    print("\nANTES, versión monolítica del Bloque 5")
    print(obtener_dato_de_prueba_monolitica(pregunta))

    print("\nDESPUES, versión refactorizada del Bloque 6")
    print(obtener_dato_de_prueba(pregunta))