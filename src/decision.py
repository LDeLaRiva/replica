"""Método de decisión de estrategia de personalización (Bloque 30).

Qué hace. Corre el método de cinco preguntas de la lección 2 sobre el
caso de este proyecto, y escribe el documento que es la entrega de la
actividad.

Qué se entrega. Solo `docs/decision_personalizacion.md`, el archivo
que este script escribe. La actividad pide subir el markdown y no el
script que lo genera.

El caso evaluado. Es el mismo del Bloque 29, clasificar la consulta
de un trabajador en una materia y una marca de si la respuesta
necesita un cálculo. No se evalúa el proyecto entero, porque la
actividad pide un caso candidato a personalización y ese es el que
quedó identificado.

De dónde sale cada respuesta. La actividad exige responder con
evidencia y no con una impresión, así que cada una lleva al lado el
número o el hecho que la sustenta. Dos están medidas, una está
contada y dos son una constatación del proyecto.

La desviación de umbral, declarada. La actividad autoriza usar otro
umbral si se anota, "son umbrales orientativos de este curso, no
valores oficiales de la API, si usas otro, anótalo y justifícalo en
tu documento". Aquí no se cambió ninguno. La primera pregunta se
responde con el umbral del curso, una vez al mes, y la medición queda
muy por debajo con cualquier umbral razonable, así que no hizo falta.

Dónde se guarda el resultado. La plataforma escribe el markdown en la
carpeta desde donde se ejecuta el script. Aquí la ruta va explícita
hacia `docs/`, que es donde viven los documentos de este repositorio,
para que el resultado no dependa de desde dónde se corra.

Las anotaciones de tipos van en todas las funciones. La actividad del
Bloque 29 lo pidió de forma explícita y desde entonces es convención
de este repositorio.

Tres desviaciones del esqueleto de la lección, y por qué.

Primera. El esqueleto de la lección imprime en la sección 2 solo los
puntajes. Aquí van además las cinco respuestas con su evidencia. La
actividad exige que cada respuesta esté sustentada, y si la evidencia
vive únicamente en los comentarios de este script, que no se entrega,
el documento entregado presenta tres números que nadie puede
verificar. La evidencia tiene que estar en el archivo que se entrega.

Segunda. El análisis de sensibilidad que pide la actividad se corre
igual al final y se imprime en consola, pero su conclusión va escrita
en la sección 3. El margen entre la técnica ganadora y la segunda es
de un punto, y un lector tiene derecho a saber qué respuestas
sostienen ese punto.

Tercera. El markdown lleva acentos. El esqueleto de la lección los
omite. Un documento en español que se entrega a revisión y dice
"decision" y "metodo" se lee descuidado. El archivo se escribe con
encoding utf-8, así que los acentos quedan correctos en el archivo
incluso si la consola de Windows los muestra mal al imprimir. Si se
ven raros en pantalla, hay que juzgar por el archivo.
"""

from pathlib import Path


CARPETA_DOCS = Path(__file__).resolve().parent.parent / "docs"

ARCHIVO_SALIDA = CARPETA_DOCS / "decision_personalizacion.md"


# --- Paso 1, el método de decisión ---------------------------------

def recomendar_estrategia(
    respuestas: dict[str, bool],
) -> tuple[dict[str, int], list[str]]:
    """Puntúa las tres técnicas y devuelve todas las empatadas.

    Es la versión corregida de la lección 2. La primera versión usaba
    `max(puntos, key=puntos.get)`, que devuelve la primera clave con
    el valor máximo y por lo tanto presenta un empate como si fuera
    un ganador. Esta devuelve la lista completa.
    """
    puntos = {"RAG": 0, "Fine-tuning completo": 0, "PEFT": 0}

    if respuestas["informacion_cambia_seguido"]:
        puntos["RAG"] += 3
    if respuestas["problema_de_formato_o_tono"]:
        puntos["PEFT"] += 2
        puntos["Fine-tuning completo"] += 1
    if respuestas["dataset_grande_y_de_calidad"]:
        puntos["Fine-tuning completo"] += 2
        puntos["PEFT"] += 1
    if respuestas["presupuesto_limitado_o_iterar_rapido"]:
        puntos["RAG"] += 2
        puntos["PEFT"] += 1
    if respuestas["necesita_multiples_variantes"]:
        puntos["PEFT"] += 2

    maximo = max(puntos.values())
    ganadoras = [t for t, p in puntos.items() if p == maximo]
    return puntos, ganadoras


# Las cinco respuestas, cada una con la evidencia que la sustenta.
respuestas_mi_caso: dict[str, bool] = {

    # NO. Medido sobre el registro de leyes modificatorias que
    # publica la Direccion del Trabajo. Entre 2017 y septiembre de
    # 2026 hubo 49 leyes que modificaron el Codigo del Trabajo, una
    # cada 2,4 meses. De esas, dos nombran articulos de este corpus,
    # el 163 por la ley 21.269 del 21.09.2020 y el 66 por la ley
    # 21.797 del 07.02.2026, es decir una cada cinco años. El umbral
    # del curso es una vez al mes.
    "informacion_cambia_seguido": False,

    # SI. Medido sobre 20 respuestas reales, cuatro corridas de
    # probar_generacion.py con sus 5 casos, revisadas con la lista
    # de criterios que ese script ya trae. En 4 de 20 la respuesta
    # le entrega al usuario vocabulario de la instruccion interna.
    # El umbral del curso son 3 o mas de 20.
    #
    # Hay una segunda medicion que apunta al mismo lado. El mismo
    # sistema se midio con tres redacciones de esa instruccion, 20
    # respuestas cada una. El original fallo 4 veces y la segunda
    # reescritura 9. Un comportamiento que se mueve asi cuando
    # cambian cinco palabras de la instruccion es inconsistente, que
    # es lo que esta pregunta busca detectar.
    "problema_de_formato_o_tono": True,

    # NO. Contado. El dataset del Bloque 29 tiene 22 ejemplos y el
    # umbral del curso son 200. La propia actividad lo zanja, "si
    # tienes menos de 200, la respuesta es False".
    "dataset_grande_y_de_calidad": False,

    # SI. No hay presupuesto para entrenamientos repetidos y el
    # ciclo de trabajo de este proyecto exige ver el efecto de un
    # cambio el mismo dia. El umbral pide como maximo 2 intentos de
    # entrenamiento, o necesitar el resultado en menos de un dia.
    "presupuesto_limitado_o_iterar_rapido": True,

    # NO. Un solo sistema, sin versiones por cliente, por idioma ni
    # por linea de producto. El umbral pide 2 o mas versiones.
    "necesita_multiples_variantes": False,
}

if any(valor is None for valor in respuestas_mi_caso.values()):
    raise SystemExit(
        "Completa las cinco respuestas con True o False antes de "
        "continuar."
    )

puntos, ganadoras = recomendar_estrategia(respuestas_mi_caso)
print(puntos)
print("candidatas:", ganadoras)


# --- Paso 2, el documento ------------------------------------------

def generar_esqueleto_decision(
    problema: str,
    evidencia: str,
    eleccion: str,
    requisitos: str,
    puntos: dict[str, int],
    ganadoras: list[str],
) -> str:
    """Arma el markdown de las cuatro secciones a partir del puntaje.

    Si hubo empate lo dice de forma explícita, en vez de presentar la
    primera opción como ganadora. Es el error que la actividad nombra
    y el mismo que la lección 2 corrigió en el código.
    """
    empate = len(ganadoras) > 1
    lineas: list[str] = []
    lineas.append("# Decisión de personalización")
    lineas.append("")
    lineas.append("## 1. El problema")
    lineas.append("")
    lineas.append(problema)
    lineas.append("")
    lineas.append("## 2. Resultado del método de decisión")
    lineas.append("")
    lineas.append("Las cinco respuestas, con la evidencia de cada "
                  "una.")
    lineas.append("")
    lineas.append(evidencia)
    lineas.append("")
    lineas.append("Puntaje que resulta.")
    lineas.append("")
    for tecnica, p in sorted(puntos.items(), key=lambda x: -x[1]):
        unidad = "punto" if p == 1 else "puntos"
        lineas.append(f"- {tecnica}, {p} {unidad}")
    if empate:
        lineas.append("")
        lineas.append(f"**Empate entre {', '.join(ganadoras)}**")
    lineas.append("")
    lineas.append("## 3. Técnica elegida y por qué")
    lineas.append("")
    if empate:
        lineas.append(
            "[COMPLETAR, el puntaje no resolvió el empate solo]"
        )
    else:
        lineas.append(eleccion)
    lineas.append("")
    lineas.append("## 4. Qué necesitaría para ejecutarla")
    lineas.append("")
    lineas.append(requisitos)
    return "\n".join(lineas)


# --- Los textos de las cuatro secciones ----------------------------

# Sección 1. La actividad pide una o dos oraciones sobre el
# comportamiento que se quiere resolver, sin nombrar todavía ninguna
# técnica. Son dos y no nombran ninguna.
PROBLEMA = """Mi sistema le entrega al usuario frases que pertenecen
a sus instrucciones internas, en 4 de 20 respuestas medidas.
Reescribí dos veces la instrucción que las causaba y volví a medir
cada versión, y las dos reescrituras quedaron peor que el original,
así que revertí."""

EVIDENCIA = """- `informacion_cambia_seguido`, **no**.
  Medido sobre el registro de leyes modificatorias que publica la
  Dirección del Trabajo. Entre 2017 y septiembre de 2026, 49 leyes
  modificaron el Código del Trabajo, una cada 2,4 meses. De esas,
  dos nombran artículos de este corpus, el 163 por la ley 21.269
  del 21.09.2020 y el 66 por la ley 21.797 del 07.02.2026, una cada
  cinco años. El umbral del curso es una vez al mes. Medí nueve años
  en vez de los últimos 3 meses que sugiere la tabla del enunciado,
  porque en una ventana de 3 meses un código legal casi nunca
  registra cambios y el dato no distinguiría una norma estable de
  una que cambia seguido. El umbral aplicado es el del curso.

- `problema_de_formato_o_tono`, **sí**.
  Medido sobre 20 respuestas reales, cuatro corridas de cinco casos,
  revisadas con una lista fija de criterios. En 4 de 20 la respuesta
  le entrega al usuario vocabulario de la instrucción interna, texto
  que habla de "el contexto" a una persona que no tiene forma de
  saber qué es eso. El umbral son 3 de 20.

- `dataset_grande_y_de_calidad`, **no**.
  Contado. El dataset de ejemplos etiquetados tiene 22 y el umbral
  son 200. La actividad lo zanja, "si tienes menos de 200, la
  respuesta es False".

- `presupuesto_limitado_o_iterar_rapido`, **sí**.
  Constatación del proyecto. No hay presupuesto para entrenamientos
  repetidos, y el ciclo de trabajo exige ver el efecto de un cambio
  el mismo día. El umbral pide como máximo 2 intentos de
  entrenamiento, o necesitar el resultado en menos de un día.

- `necesita_multiples_variantes`, **no**.
  Constatación del proyecto. Un solo sistema, sin versiones por
  cliente, por idioma ni por línea de producto. El umbral pide 2 o
  más versiones."""

ELECCION = """**PEFT**, con 3 puntos contra 2 de RAG y 1 de
fine-tuning completo. No hubo empate.

El margen es de un solo punto, así que corresponde decir qué lo
sostiene. Corrí el método cinco veces más, cambiando una respuesta
cada vez y dejando las otras cuatro quietas. Dos de los cinco
cambios mueven la recomendación, y los dos se la entregan a RAG. Uno
es `informacion_cambia_seguido`, que si fuera sí le daría 5 puntos a
RAG. El otro es `problema_de_formato_o_tono`, que si fuera no dejaría
a PEFT en 1. Las otras tres respuestas no mueven nada. La
recomendación descansa entonces sobre las dos respuestas que están
medidas, y no sobre las tres que son un conteo o una constatación.

Más allá del puntaje, la razón de fondo es de qué tipo es esta falla.
En los 4 casos de 20 la recuperación funcionó, el fragmento correcto
llegó al modelo y la cita salió bien. Lo que falló fue la forma de la
respuesta. Agregar documentos no arregla la forma de una respuesta,
porque no hay ningún documento faltante. El corpus ya tenía lo que
hacía falta.

La evidencia más fuerte es un experimento que fracasó. Medí el mismo
sistema con tres redacciones de la misma instrucción, 20 respuestas
cada una, 60 generaciones en total. El original falla 4 veces y la
segunda reescritura 9. La primera reescritura también quedó peor que
el original. La segunda además produjo una falla de otro tipo, más
grave, una regla legal entregada sin la condición que la limita.
Cambiar cinco palabras de la instrucción mueve el comportamiento del
sistema de 4 a 9 fallas por cada 20, y revertí al original porque era
el menos malo de los tres. Un
comportamiento que se mueve así con el texto de la instrucción es
inconsistente, y esa inconsistencia es justamente lo que esta técnica
corrige y lo que seguir ajustando el prompt no corrige."""

REQUISITOS = """El método recomienda una técnica que hoy no puedo
ejecutar, y eso también es parte de la respuesta.

**Faltan 178 ejemplos etiquetados.** Tengo 22 y el umbral son 200. El
etiquetado es manual y no se puede delegar a un modelo, porque el
modelo no tiene la referencia legal, se equivoca, y una etiqueta mala
entra al entrenamiento como si fuera buena. Los 22 ejemplos salieron
de un corpus de 11 artículos, así que llegar a 200 pide ampliar
primero el corpus y etiquetar después, en ese orden. A 5 minutos por
ejemplo bien etiquetado, que es el ritmo que usa la lección de
costos, los 178 que faltan son 14,8 horas de trabajo humano, casi
dos jornadas de ocho horas. No pongo una cifra en dinero porque el
etiquetado lo hago yo y no hay una tarifa por hora que aplicar.

**Falta un conjunto de prueba aparte.** Las 20 respuestas que medí son
la línea base. Si entreno un adaptador y lo evalúo con esos mismos
casos, no voy a poder distinguir si el comportamiento mejoró o si el
modelo se aprendió la muestra. La actividad no lo pide, pero sin esto
el entrenamiento no se puede medir, y una técnica que no se puede
medir no se puede defender."""


esqueleto = generar_esqueleto_decision(
    PROBLEMA, EVIDENCIA, ELECCION, REQUISITOS, puntos, ganadoras
)

CARPETA_DOCS.mkdir(exist_ok=True)
with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
    f.write(esqueleto)

print()
print("escrito en", ARCHIVO_SALIDA)
print(len(esqueleto.splitlines()), "lineas")


# --- Comprobacion, el analisis de sensibilidad ---------------------
#
# La actividad pide correr el metodo una segunda vez cambiando una
# sola respuesta, la que mas dudas genero, y entender por que el
# puntaje cambia como cambia. Esto lo hace con las cinco, que es lo
# que muestra la leccion 2, y asi se ve cuales mueven el resultado.
# La conclusion de esta corrida es la que esta escrita en la seccion
# 3 del documento.

print()
print("--- sensibilidad, una respuesta a la vez ---")
for clave in respuestas_mi_caso:
    variante = dict(respuestas_mi_caso)
    variante[clave] = not variante[clave]
    _, ganadoras_v = recomendar_estrategia(variante)
    cambio = (
        "CAMBIA" if set(ganadoras_v) != set(ganadoras) else "igual"
    )
    print(f"{clave} -> {not respuestas_mi_caso[clave]}: "
          f"{ganadoras_v}  [{cambio}]")
