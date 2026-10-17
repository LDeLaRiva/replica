import os
import requests
from dotenv import load_dotenv

load_dotenv()


def armar_peticion(pregunta):
    """
    * Deja lista la petición, con su dirección, su encabezado y su cuerpo.
    * Lanza ValueError si la pregunta viene vacía o si falta una variable del .env.
    """
    if not pregunta or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    api_key_gemini = os.getenv("AI_API_KEY")
    modelo = os.getenv("AI_MODEL")

    if not api_key_gemini:
        raise ValueError("Falta AI_API_KEY en el archivo .env")
    if not modelo:
        raise ValueError("Falta AI_MODEL en el archivo .env")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"x-goog-api-key": api_key_gemini}
    body = {
        "contents": [
            {"parts": [{"text": pregunta}]}
        ]
    }
    return url, headers, body


def enviar_peticion(url, headers, body):
    """
    * Envía la petición y devuelve la respuesta ya convertida a diccionario.
    * Lanza RuntimeError si no hay conexión, si el servicio tarda demasiado,
    o si lo que responde no es JSON válido.
    """
    try:
        respuesta = requests.post(url, headers=headers, json=body, timeout=30)
    except requests.exceptions.ConnectionError:
        raise RuntimeError("No se pudo conectar con el servicio. Intenta de nuevo en unos segundos.")
    except requests.exceptions.Timeout:
        raise RuntimeError("El servicio tardó demasiado en responder.")

    try:
        return respuesta.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError("La respuesta del servicio no llegó en el formato esperado.")


def extraer_texto(datos):
    """
    * Recorre la respuesta de Gemini y devuelve solo el texto generado.
    * Lanza RuntimeError si la respuesta no trae el texto donde se espera.
    """
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("La respuesta no trae el texto generado en el lugar esperado.")


def obtener_dato_de_prueba(pregunta):
    """
    * Coordina las tres funciones anteriores y devuelve el texto generado.
    * Puede lanzar ValueError o RuntimeError, según dónde falle.
    """
    url, headers, body = armar_peticion(pregunta)
    datos = enviar_peticion(url, headers, body)
    return extraer_texto(datos)


if __name__ == "__main__":
    from contraste import *

    try:
        respuesta_gemini = obtener_dato_de_prueba("explicame que es json en 20 palabras")
        salfn(f"\nLa respuesta de Gemini es:\n{respuesta_gemini}")
    except (ValueError, RuntimeError) as error:
        errorb(f"\nNo se pudo completar la operación:\n{error}")
