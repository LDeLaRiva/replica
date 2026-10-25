"""Prueba de consistencia del banco de prompts.

Ejecuta cada prompt varias veces contra la API real y cuenta cuántas
respuestas llegaron como JSON válido y con las claves que el propio
prompt declara.

Se puede ejecutar de las dos formas, con el mismo resultado:
    python -m prompts.test_consistencia
    python prompts/test_consistencia.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Este archivo vive en prompts/ y el módulo en src/. Al ejecutarlo
# directamente, Python solo mira la carpeta de este archivo y no
# encontraría src/. Agregar la raíz del repositorio permite las dos
# formas de ejecución.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from prompts.banco import BANCO_DE_PROMPTS          # noqa: E402
from src.consumir_gemini import (                   # noqa: E402
    armar_peticion,
    enviar_peticion,
    extraer_texto,
    parsear_respuesta_json,
)
from src.contraste import *                         # noqa: E402, F403

# La ruta se arma desde la raíz y no como texto suelto, para que el
# registro caiga siempre en el mismo lugar sin importar desde qué
# carpeta se ejecute.
ARCHIVO_REGISTRO = RAIZ / "prompts" / "registro_resultados.json"

REPETICIONES = 5
PAUSA = 5

# Muestra el contenido de cada respuesta, no solo el conteo.
MOSTRAR_RESPUESTAS = True

# Imprime la plantilla del documento de ajustes. Se enciende solo
# cuando hubo un cambio que documentar.
PLANTILLA_AJUSTE = False

registro = {}

for prompt in BANCO_DE_PROMPTS:
    exitos = 0
    titulofn(f"\n{prompt['nombre']}")

    for intento in range(REPETICIONES):
        try:
            url, headers, body = armar_peticion(
                prompt["ejemplo_usuario"],
                prompt["system_instruction"],
                prompt.get("response_schema"),
            )
            respuesta = enviar_peticion(url, headers, body)
            texto = extraer_texto(respuesta)

            datos = parsear_respuesta_json(
                texto, prompt["claves_esperadas"])

            # Si llegamos hasta aquí el JSON vino bien y con todas
            # las claves. No hace falta volver a revisarlas, porque
            # parsear_respuesta_json levanta ValueError cuando falta
            # alguna.
            exitos += 1

            if MOSTRAR_RESPUESTAS:
                salbn(f"  intento {intento + 1}")
                # El ancho sale de la clave más larga, para que los
                # valores queden en columna. Cada prompt tiene sus
                # propias claves, así que se calcula en cada vuelta.
                ancho = max(len(clave) for clave in datos)
                for clave, valor in datos.items():
                    salfn(f"    {clave:<{ancho}}  {valor}")

        except (ValueError, RuntimeError, TimeoutError) as fallo:
            avisofn(f"  intento {intento + 1} falló. {fallo}")

        # Una falla rara no debe botar la medición completa y dejar
        # sin registro las repeticiones ya hechas.
        except Exception as fallo:
            errorbn(f"  intento {intento + 1} error inesperado. "
                    f"{type(fallo).__name__}")

        time.sleep(PAUSA)

    if exitos == REPETICIONES:
        exitobn(f"  {exitos}/{REPETICIONES} respuestas válidas")
    else:
        avisobn(f"  {exitos}/{REPETICIONES} respuestas válidas")

    registro[prompt["nombre"]] = {
        "exitos": exitos,
        "fallas": REPETICIONES - exitos,
        "intentos": REPETICIONES,
    }

ahora = datetime.now()
hoy = ahora.date().isoformat()

# El archivo guarda, además de los conteos, el momento en que se
# midió. Sin eso no se sabe si los números siguen vigentes.
salida = {
    "fecha": ahora.isoformat(timespec="seconds"),
    "resultados": registro,
}

# Si no hubo ni una respuesta válida, lo más probable es que el
# problema sea de configuración y no de los prompts. Escribir ceros
# en ese caso borraría una medición buena y no aportaría ninguna,
# así que el archivo se deja como estaba.
if sum(r["exitos"] for r in registro.values()) == 0:
    errorbn("\nNinguna respuesta válida en toda la medición.")
    avisobn("\nEl registro no se modificó. Revisa la configuración "
            "y vuelve a correr.")
    raise SystemExit(1)

with open(ARCHIVO_REGISTRO, "w", encoding="utf-8") as archivo:
    json.dump(salida, archivo, indent=2, ensure_ascii=False)

titulofn("\nRegistro guardado en prompts/registro_resultados.json")

# Filas en formato markdown, para copiarlas al documento de ajustes
# sin transcribir los números a mano.
titulofn("\nPara pegar en docs/ajustes-prompts.md")
for nombre, resultado in registro.items():
    titulobn(f"| {hoy} | {nombre} | "
          f"{resultado['exitos']}/{resultado['intentos']} |")

if PLANTILLA_AJUSTE:
    salbn(f"""
## Iteración N — (título corto del cambio)

**Fecha.** {hoy}
**Prompt.** (cuál)

**Qué se observó.**
(...)

**Qué se cambió.**
(...)

**Resultado.**""")
    for nombre, resultado in registro.items():
        salbn(f"{nombre}  "
              f"{resultado['exitos']}/{resultado['intentos']}")