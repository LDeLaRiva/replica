"""Consulta a la API de Gemini.
 
Cada error que lanza este módulo lleva un mensaje con dos partes,
separadas por un salto de línea. La primera es para el usuario final y la
segunda, marcada con [técnico], es el detalle para quien programa.
 
Por ahora las dos se imprimen juntas, porque esto corre en terminal y no
hay todavía un usuario distinto de quien desarrolla. Es una simulación.
Más adelante se definirá cómo se muestra cada parte por separado.
 
Lo que depende de Gemini está en armar_peticion y en extraer_texto.
Cambiar de proveedor afecta solo a esas dos.
"""
 
import json
import os
import re
import time          # solo para la medición del Bloque 9
import requests
from dotenv import load_dotenv
 
load_dotenv()
 
# Tope propio, no es el límite de la API, que acepta muchísimo más.
# Medido sobre documentos tipo. Un contrato completo son 3.900 a 5.900
# caracteres, un finiquito 2.900 y un contrato con su anexo 7.600. El peor
# caso, dos contratos para comparar, dio 11.984. Los 15.000 lo cubren con
# margen y siguen evitando que alguien pegue un documento de cien páginas.
LARGO_MAXIMO = 15000  #prueba 

 
MENSAJE_GENERICO = ("No pudimos completar tu consulta. Intenta nuevamente en unos minutos.")

INSTRUCCION = "Responde siempre en idioma español."

#precios para gemini-3.5-flash-lite
PRECIO_ENTRADA = 0.30 / 1_000_000
PRECIO_SALIDA  = 2.50 / 1_000_000

def calcular_costo_peticion(datos, precio_entrada, precio_salida):
    """Calcula el costo en dólares de una petición, según sus tokens.

    Args:
        datos: la respuesta del servicio, ya convertida en diccionario.
        precio_entrada: precio en dólares por cada token enviado.
        precio_salida: precio en dólares por cada token generado.

    Returns:
        El costo de esa petición en dólares.

    Raises:
        RuntimeError: si la respuesta no trae el bloque usageMetadata o le
            falta alguno de los dos conteos de tokens.
    """
    try:
        uso = datos["usageMetadata"]
        tokens_entrada = uso["promptTokenCount"]
        tokens_salida = uso["candidatesTokenCount"]
    except KeyError as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] KeyError. Falta el campo {fallo} para el costo.")
    except TypeError as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] TypeError. {fallo}")

    return (tokens_entrada * precio_entrada) + (tokens_salida * precio_salida)
 
 
def armar_peticion(pregunta, system_instruction, response_schema=None):
    """Valida la pregunta del usuario y arma la petición a Gemini.

    Args:
        pregunta: el texto que escribió el usuario, todavía sin validar.
        system_instruction: la instrucción de comportamiento, que viaja
            en un campo aparte de la pregunta.
        response_schema: la forma exacta que debe tener el JSON de
            respuesta. Si no se entrega, la respuesta viene como texto
            libre.

    Returns:
        Una tupla con la url, los headers y el body, en ese orden.

    Raises:
        ValueError: si la pregunta no es texto, si viene vacía o si supera
            LARGO_MAXIMO caracteres. También si falta AI_API_KEY o
            AI_MODEL en el archivo .env.
    """
    if not isinstance(pregunta, str):
        raise ValueError(
            "Escribe tu consulta como texto.\n"
            f"[técnico] La pregunta debe ser str, llegó {type(pregunta).__name__}.")
    if not pregunta.strip():
        raise ValueError(
            "Escribe tu consulta antes de enviar.\n"
            "[técnico] La pregunta está vacía o es solo espacios.")
    if len(pregunta) > LARGO_MAXIMO:
        raise ValueError(
            f"Tu consulta es muy larga. El máximo son {LARGO_MAXIMO} caracteres.\n"
            f"[técnico] La pregunta tiene {len(pregunta)} caracteres.")
 
    api_key_gemini = os.getenv("AI_API_KEY")
    modelo = os.getenv("AI_MODEL")
    if not api_key_gemini:
        raise ValueError(
            f"{MENSAJE_GENERICO}\n"
            "[técnico] Falta AI_API_KEY en el .env")
    if not modelo:
        raise ValueError(
            f"{MENSAJE_GENERICO}\n"
            "[técnico] Falta AI_MODEL en el .env")
 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    # La credencial va en el header y no en la url. Si fuera parte de la
    # url aparecería completa en el mensaje de cualquier error de conexión.
    headers = {"x-goog-api-key": api_key_gemini}
    body = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {"parts": [{"text": pregunta}]}
        ],
    }

    if response_schema is not None:
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        }
    return url, headers, body
 
 
def enviar_peticion(url, headers, body):
    """Envía la petición al servicio y entrega lo que éste responda.
 
    Args:
        url: la dirección a la que se envía la petición.
        headers: las cabeceras, que incluyen la credencial.
        body: la pregunta ya empaquetada para enviar.
 
    Returns:
        La respuesta del servicio, convertida en diccionario.
 
    Raises:
        RuntimeError: si falla la conexión, si se agota el tiempo de
            espera, si la url está mal formada, si hay un bucle de
            redirecciones, si el servicio responde con un código distinto
            de 200, o si lo que devuelve no es JSON válido.
    """
    try:
        respuesta = requests.post(url, headers=headers, json=body,
                                  timeout=120)
    except requests.exceptions.ConnectionError as fallo:
        raise RuntimeError(
            "No hay conexión. Revisa tu internet e intenta de nuevo.\n"
            f"[técnico] ConnectionError. {fallo}")
    except requests.exceptions.Timeout as fallo:
        raise RuntimeError(
            "El servicio está tardando mucho. Intenta en un momento.\n"
            f"[técnico] Timeout. {fallo}")
    except requests.exceptions.MissingSchema as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] MissingSchema. {fallo}")
    except requests.exceptions.InvalidURL as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] InvalidURL. {fallo}")
    except requests.exceptions.TooManyRedirects as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] TooManyRedirects. {fallo}")
    # Va al final porque RequestException es el padre de todos los de
    # arriba. Si estuviera primero, los atraparía antes que ellos.
    except requests.exceptions.RequestException as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] {type(fallo).__name__}. {fallo}")
 
    # Un código de error del servicio no levanta excepción, llega como
    # respuesta normal, así que hay que revisarlo a mano.
    if respuesta.status_code != 200:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] El servicio respondió {respuesta.status_code}: {respuesta.text[:300]}")
 
    try:
        return respuesta.json()
    except requests.exceptions.JSONDecodeError as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] JSONDecodeError. {fallo}")
 
 
def extraer_texto(datos):
    """Extrae el texto generado por el modelo desde la respuesta de Gemini.
 
    Args:
        datos: la respuesta del servicio, ya convertida en diccionario.
 
    Returns:
        El texto generado, como string.
 
    Raises:
        RuntimeError: si la respuesta no tiene la forma esperada, sea
            porque falta un campo, porque una lista viene vacía, o porque
            un valor no es del tipo que se esperaba.
    """
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except KeyError as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] KeyError. Falta el campo {fallo}.")
    except IndexError as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] IndexError. {fallo}")
    except TypeError as fallo:
        raise RuntimeError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] TypeError. {fallo}")

def parsear_respuesta_json(texto, claves_esperadas):
    """Convierte la respuesta del modelo en un diccionario de Python.

    Limpia las marcas de markdown que el modelo a veces agrega alrededor
    del JSON, lo interpreta, y confirma que traiga las claves pedidas.

    Args:
        texto: la respuesta del modelo, tal como la entrega extraer_texto.
        claves_esperadas: lista con los nombres de las claves que el JSON
            debe traer.

    Returns:
        El JSON ya convertido en diccionario.

    Raises:
        ValueError: si el texto no es JSON válido, o si al diccionario le
            falta alguna de las claves esperadas.
    """
    texto_limpio = texto.strip()
    texto_limpio = re.sub(r"^```(?:json)?\s*", "", texto_limpio)
    texto_limpio = re.sub(r"\s*```$", "", texto_limpio)

    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError as fallo:
        raise ValueError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] La respuesta no es JSON válido. {fallo}")

    faltantes = [c for c in claves_esperadas if c not in datos]
    if faltantes:
        raise ValueError(
            f"{MENSAJE_GENERICO}\n"
            f"[técnico] Al JSON le faltan estas claves. {faltantes}")

    return datos
 
 
def obtener_dato_de_prueba(pregunta, system_instruction, response_schema=None):
    """Obtiene la respuesta del modelo para la pregunta que se le entrega.
 
    Args:
        pregunta: el texto que escribió el usuario, todavía sin validar.
        system_instruction: la instrucción de comportamiento que se le
            entrega a armar_peticion.
        response_schema: la forma exacta que debe tener el JSON de
            respuesta, o None si la respuesta viene como texto libre.

    Returns:
        El texto generado, como string.
 
    Raises:
        ValueError: los que lanza armar_peticion.
        RuntimeError: los que lanzan enviar_peticion y extraer_texto.
    """
    url, headers, body = armar_peticion(pregunta, system_instruction, response_schema)
    datos = enviar_peticion(url, headers, body)
    costo = calcular_costo_peticion(datos, PRECIO_ENTRADA, PRECIO_SALIDA)
    return extraer_texto(datos), costo, datos["usageMetadata"]


 # ===== BLOQUE 9 · MEDICIÓN TEMPORAL ====================================
# Esto se agregó solo para medir y comparar dos modelos en la actividad
# del Bloque 9. No es parte de la aplicación, es una herramienta de
# medición, y por eso no aparece en el diagrama de arquitectura.
#
# Se comenta completo junto con el bloque del mismo nombre que está en el
# if __name__ y con la línea "import time" de arriba.

# def medir_latencia(pregunta, system_instruction, repeticiones=10, pausa=15):
#     """Repite la misma pregunta varias veces y cronometra cada llamada.

#     Las llamadas que fallan se cuentan en vez de interrumpir la medición,
#     porque la tasa de fallas es uno de los datos que se está midiendo.

#     Args:
#         pregunta: el texto que se envía en cada repetición.
#         system_instruction: la instrucción de comportamiento, la misma en
#             todas las repeticiones para que la comparación sea justa.
#         repeticiones: cuántas veces se intenta la llamada.
#         pausa: segundos de espera entre llamadas.

#     Returns:
#         Una tupla con la lista de latencias de las que respondieron,
#         cuántas fallaron, y el texto, el costo y el usageMetadata de la
#         última que respondió.
#     """
#     latencias = []
#     fallas = 0
#     texto = None
#     costo = None
#     uso = None
#     for _ in range(repeticiones):
#         inicio = time.perf_counter()
#         try:
#             texto, costo, uso = obtener_dato_de_prueba(pregunta, system_instruction)
#             latencias.append(time.perf_counter() - inicio)
#         except RuntimeError:
#             fallas += 1
#         time.sleep(pausa)
#     return latencias, fallas, texto, costo, uso

# ===== FIN BLOQUE 9 ====================================================
 
if __name__ == "__main__":
    from contraste import *
    # Este bloque solo corre cuando se ejecuta este archivo directamente.
    # Si otro archivo importa el módulo, no corre, y ese archivo necesita
    # su propio try.
    #
    # El except Exception va aquí, en el borde del programa, y no dentro
    # de las funciones, por dos razones. Primero, porque este es el único
    # lugar que imprime, y las funciones solo avisan. Segundo, porque
    # atrapar Exception dentro de una función taparía errores de
    # programación míos justo donde necesito verlos.
    try:
        titulobn(f"\nAI_MODEL vale  ->  {os.getenv('AI_MODEL')}")
        respuesta_gemini, costo, uso = obtener_dato_de_prueba(
            "explicame que es json en 2 lineas ", 
            INSTRUCCION)
        salbn(f"\nLa respuesta de Gemini es:\n{respuesta_gemini}")
        titulobn(f"\nCosto estimado de la petición: {costo:.8f} USD")

        # Los tokens y el costo son información de desarrollo (igual que
        # la línea [técnico]). Cuando se separe lo que ve el usuario, estos
        # tres van con el lado técnico.
        exitobn(f"\nTokens entrada    {uso['promptTokenCount']}")
        exitobn(f"Tokens salida     {uso['candidatesTokenCount']}")
        exitobn(f"Total tokens      {uso['totalTokenCount']}")

        # ===== BLOQUE 9 · MEDICIÓN TEMPORAL ========================
        # Esto se agregó solo para medir y comparar dos modelos en la
        # actividad del Bloque 9. No es parte de la aplicación, es una
        # herramienta de medición, y por eso no aparece en el diagrama
        # de arquitectura.
        #
        # Mide un modelo por corrida. Para medir el otro candidato se
        # cambia AI_MODEL en el .env, y también los dos PRECIO_ de
        # arriba, porque no son los mismos para los dos modelos.
        # PREGUNTA = ("¿Cuántos días de vacaciones corresponden por año en "
        #             "Chile? Responde en una línea.")

        # latencias, fallas, texto_m, costo, uso = obtener_dato_de_prueba(pregunta, INSTRUCCION)

        # titulobn(f"\nModelo medido  {os.getenv('AI_MODEL')}")

        # for numero, segundos in enumerate(latencias, 1):
        #     exitobn(f"Medición {numero:>2}       {segundos:.2f} s")

        # exitobn(f"\nRespondieron      {len(latencias)} de "
        #         f"{len(latencias) + fallas}")

        # if latencias:
        #     exitobn(f"Latencia promedio {sum(latencias)/len(latencias):.2f} s")
        #     exitobn(f"Costo             {costo_m:.8f} USD")
        #     exitobn(f"Tokens entrada    {uso_m['promptTokenCount']}")
        #     exitobn(f"Tokens salida     {uso_m['candidatesTokenCount']}")
        #     exitobn(f"Total tokens      {uso_m['totalTokenCount']}")
        #     exitobn(f"usageMetadata completo  {uso_m}")
        #     salbn(f"\nÚltima respuesta recibida:\n{texto_m}")
        # ===== FIN BLOQUE 9 ========================================

    except (ValueError, RuntimeError) as fallo:
        # El mensaje trae las dos partes juntas, la del usuario y el
        # detalle marcado con [técnico]. Hoy se imprimen las dos porque
        # es una simulación en terminal. Más adelante se definirá cómo se
        # muestra cada parte por separado.
        avisofn(f"\n{fallo}")

    except Exception as fallo:
        errorfn(f"\nError inesperado. {type(fallo).__name__}")
        avisofn(f"\n{fallo}")