# Decisión de personalización (Bloque 30)

## 1. El problema

Mi sistema le entrega al usuario frases que pertenecen
a sus instrucciones internas, en 4 de 20 respuestas medidas.
Reescribí dos veces la instrucción que las causaba y volví a medir
cada versión, y las dos reescrituras quedaron peor que el original,
así que revertí.

## 2. Resultado del método de decisión

Las cinco respuestas, con la evidencia de cada una.

- `informacion_cambia_seguido`, **no**.
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
  más versiones.

Puntaje que resulta.

- PEFT, 3 puntos
- RAG, 2 puntos
- Fine-tuning completo, 1 punto

## 3. Técnica elegida y por qué

**PEFT**, con 3 puntos contra 2 de RAG y 1 de
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
corrige y lo que seguir ajustando el prompt no corrige.

## 4. Qué necesitaría para ejecutarla

El método recomienda una técnica que hoy no puedo
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
medir no se puede defender.