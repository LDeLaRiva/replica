# Límites del logging y de la mitigación de inyección (Bloque 31)

Observaciones del Bloque 31. El diseño del código está documentado en
la cabecera de `src/logging_rag.py`, con sus once desviaciones y el
motivo de cada una. Lo que sigue son los límites de lo que quedó
construido, las mediciones que los sustentan y lo que quedó abierto.

Los límites de los bloques anteriores eran de calidad y se notaban en
la respuesta. Los de este bloque son de seguridad y no se notan hasta
que alguien los busca, así que quedan escritos aunque hoy ninguno
tenga consecuencias visibles.

---

## 1. Qué pedía el bloque y qué se entregó

La actividad pide cuatro pasos sobre el flujo propio. Logging
estructurado en JSON con un `trace_id` por consulta, registro del
consumo de tokens, un filtro de inyección sobre los documentos
recuperados, y una función que una las tres piezas alrededor de una
consulta.

Los cuatro están en `src/logging_rag.py`, que es la entrega.

### Por qué hay dos commits

Esta actividad tiene dos commits en vez de uno.

El primero es la entrega. Lleva el archivo con los cuatro pasos y su
mensaje es el que el enunciado da literal, "instrumenta el flujo RAG
con logging, trace_id, consumo y filtro de inyeccion".

El segundo suma una cosa que la actividad no pide, revisar también la
pregunta del usuario y no solo los documentos recuperados. Su mensaje
es propio, "registra los patrones de inyección en la pregunta del
usuario".

Se hicieron por separado para que se distinga cuál es la entrega y
cuál es el agregado. El segundo modifica el archivo ya entregado.

### Qué no se modificó en este bloque

`src/recuperacion.py` no se tocó. `src/logging_rag.py` importa desde
ese módulo `PROMPT_TEMPLATE` y `formatear_contexto`, de modo que el
prompt que se instrumenta es el mismo que quedó medido en el Bloque
28, sin una segunda copia que pueda quedar desactualizada.

Ese archivo sí se modificó durante el Bloque 30, dos veces, para
probar reescrituras de la instrucción 2 de la plantilla. Las dos
mediciones dieron peor que el original y los dos cambios se
revirtieron con `git checkout` antes de llegar a ningún commit, de
modo que lo que está en el repositorio sigue siendo la versión del
Bloque 28. El detalle de esas mediciones está en
`docs/decision_personalizacion.md`.

---

## 2. Las tres capas de defensa

La lección sobre inyección describe tres capas de mitigación y cierra
advirtiendo que ninguna de ellas, por separado, es una solución
completa. Este sistema tiene una de las tres.

```
Capa 1  separacion de roles          AUSENTE
Capa 2  delimitacion del contexto    PARCIAL
Capa 3  deteccion de patrones        PRESENTE
```

### Capa 1, ausente

La búsqueda de `SystemMessage`, `HumanMessage`, `ChatPromptTemplate` y
`from_messages` en `src/recuperacion.py` no devuelve ninguna
ocurrencia. El prompt se arma con `PROMPT_TEMPLATE.format(...)` y se
envía como un solo string a `(modelo | StrOutputParser()).invoke()`.

Esto significa que las instrucciones, el contexto recuperado y la
pregunta del usuario viajan por el mismo canal de texto plano, que es
la condición que la lección señala como causa de la inyección
indirecta, "una consecuencia de que el canal de entrada es el mismo
texto tanto para instrucciones como para datos".

### Capa 2, parcial

`MARCA_CONTEXTO` vale `"Contexto:\n"`. La plantilla sí acota la
respuesta al contexto, porque su instrucción 1 indica "respondela
usando SOLO el contexto", pero no declara que el contenido del
contexto sean datos y nunca instrucciones, que es la otra mitad del
trabajo de esta capa según la lección.

La frontera del contexto es una etiqueta y no un delimitador. El
contexto empieza después de `Contexto:` y termina donde aparece
`\n\nPregunta:`. Un fragmento recuperado que contuviera ese texto
desplazaría la frontera y además rompería `contexto_de()`, que recorta
por esa misma marca.

La medición sobre el corpus actual da lo siguiente.

```
Contexto:                 0 de 11 articulos lo contienen
Pregunta:                 0 de 11
Respuesta:                0 de 11
doble salto + Pregunta:   0 de 11
```

El riesgo no se materializa con el corpus de hoy. Aumenta a medida que
el corpus crece, y aumenta más si en algún momento se indexan fuentes
que no sean texto legal.

### Capa 3, presente

Es la capa que se construyó en este bloque. Sus límites se describen
en la sección 3.

---

## 3. El filtro es una lista negra

La lista tiene catorce patrones, los seis de la lección y ocho
agregados. Reconoce únicamente las frases que están escritas en ella,
y cualquier redacción que no figure pasa sin ser detectada.

Los ocho se agregaron porque la lección describe su propia lista como
"deliberadamente chica y específica" y señala que crece con el
tiempo, y porque la actividad pide ajustarla a lo que se observa en
los datos propios. Cada uno cubre una forma de ataque que los seis no
alcanzan, entre ellas los encabezados que imitan un turno de
conversación, los tokens con que algunos modelos marcan sus propios
turnos, y variantes en español y en inglés que las seis no incluyen.

La medición sobre diez intentos de inyección de prueba da lo
siguiente.

```
con los seis de la leccion     3 de 10 detectados
con los catorce                9 de 10 detectados
```

Aun así, el filtro no detecta una instrucción escrita con sinónimos
que no estén en la lista, en un idioma distinto, con las letras
separadas, ni repartida entre dos fragmentos que se recuperen juntos.
Este repositorio es público, de modo que los catorce patrones están a
la vista de quien quiera escribir alrededor de ellos.

El filtro funciona como una barrera de bajo costo contra los intentos
más comunes y no constituye un límite de seguridad. No reemplaza a las
capas 1 y 2.

### El patrón que quedó fuera

El intento que los catorce no detectan es un documento que abre con
`\n\nPregunta:` para simular que el contexto terminó, que es el hueco
de frontera descrito en la sección 2.

El patrón que lo cubriría busca `contexto:`, `pregunta:` o
`respuesta:` al comienzo de una línea. Se midió y quedó fuera, porque
marca una consulta legítima del conjunto coloquial, "pregunta: cuanto
me corresponde de finiquito tras 7 anos".

Ese hueco se cierra con la capa 2 y no con un patrón más.

### Los falsos positivos sobre el corpus propio

```
11 articulos del corpus            0 marcados
22 preguntas del dataset           0 marcadas
15 consultas en registro coloquial 0 marcadas por los ocho agregados
```

Las tres mediciones están dentro de `src/logging_rag.py`, en
`comprobar_texto_legitimo_propio`, y se ejecutan en cada corrida del
archivo.

La tercera lista está escrita en el registro en que escribe quien
consulta por un problema laboral, y cada caso se eligió por quedar
cerca de alguno de los patrones. Dos de esas quince consultas sí
quedan marcadas, pero por patrones de la lección y no por los
agregados.

Cinco de esas quince entraron durante la revisión de los patrones
candidatos, porque fueron las que descartaron a dos de ellos. Un
patrón que buscaba separadores de sección marcaba "### IMPORTANTE ###
me descontaron el bono sin avisar", y otro que buscaba "revela las
instrucciones" marcaba "el reglamento revela las instrucciones que
debo seguir". El primero quedó fuera y el segundo se estrechó a
"tus". Las cinco consultas quedaron en la comprobación para que un
patrón futuro no repita el error.

Si en el futuro un patrón nuevo marca algo legítimo de cualquiera de
las tres listas, la comprobación falla antes de que el problema
llegue a una consulta real.

El alcance de esas dos cifras es acotado. Once artículos no son el
Código del Trabajo completo, y veintidós preguntas escritas por una
sola persona, en un registro breve y formal, no representan la forma
en que escribe quien tiene un problema laboral.

---

## 4. La pregunta del usuario se registra y no se bloquea

La actividad filtra solo los documentos recuperados. La lección sobre
inyección abre nombrando los dos canales no confiables de un flujo
RAG, lo que escribe el usuario y el contenido de cada documento que el
propio sistema recupera, y luego desarrolla únicamente el segundo.

Este sistema cubre también el primero, registrando los patrones que
aparecen en la pregunta sin interrumpir la consulta. La primera
versión del agregado bloqueaba la consulta, y se descartó después de
medir los falsos positivos.

### Las dos poblaciones se superponen

```
consultas laborales legitimas     1 patron, 1 patron
intentos de inyeccion reales      1 patron, 1 patron
```

Una de las consultas legítimas que coinciden es la siguiente, que está
redactada como se redacta corrientemente.

> La empresa implementó un nuevo sistema: turnos rotativos, ¿es legal
> que no nos avisaran?

Coincide con `nuevo\s+sistema\s*:`. Un intento de inyección real puede
coincidir también con un solo patrón, de modo que las dos poblaciones
se superponen en el mismo valor y ningún umbral las separa.

La causa es que los seis patrones se escribieron pensando en
documentos. Dentro de un artículo del Código del Trabajo, la secuencia
"nuevo sistema:" sería muy poco probable, mientras que en la pregunta
de una persona que describe su trabajo es corriente.

`comprobar_superposicion_de_patrones` deja esta medición dentro
del archivo.
Sus dos asserts fallan si en algún momento **deja** de haber
superposición, de modo que la decisión se vuelva a evaluar en lugar de
quedar fija.

### Qué puede lograr una inyección directa en este sistema

```
sacar el prompt         esta publicado en este repositorio
responder fuera de tema se perjudica quien lo escribio
saltarse las citas      idem
datos de terceros       no hay, un solo usuario y sin estado compartido
herramientas            no hay, el modelo no ejecuta nada
```

Con ese nivel de impacto, un bloqueo automático cuesta más de lo que
protege. Un bloqueo equivocado deja sin respuesta a una persona con un
problema laboral real, y ninguno de los daños de la lista anterior
tiene una consecuencia comparable.

### Qué haría cambiar esta decisión

Que el sistema pase a tener varios usuarios, estado compartido,
herramientas que el modelo pueda ejecutar, o datos que no sean ley
pública. Cualquiera de esas cuatro condiciones obliga a evaluar de
nuevo si conviene bloquear.

---

## 5. Qué se loguea y qué no

La lección pide tomar esta decisión a propósito y no por descuido, y
separa el contenido que hace falta guardar tal cual del que alcanza
con registrar como longitud o como huella.

```
se guarda    longitud de la pregunta
             huella sha256 de 12 caracteres de la pregunta
             numero de articulo de cada fragmento descartado
             huella del fragmento descartado
             conteos de recuperados, limpios y descartados
             los tres campos de tokens
             cuantos patrones coincidieron

no se guarda el texto de la pregunta
             el texto de los fragmentos
             el texto de la respuesta
             que patron coincidio
```

El número de artículo se guarda completo porque corresponde a ley
pública y es el dato necesario para auditar un descarte. La huella
permite detectar que un mismo fragmento se recuperó dos veces sin
dejar su contenido escrito en el registro.

El patrón que coincidió no se guarda, para no dejar en los logs la
lista de lo que el filtro reconoce.

### Lo que se pierde con esto

La huella sirve para comparar dos textos y no para recuperar el texto.
Si en algún momento hay que revisar un incidente puntual sobre lo que
se escribió exactamente, estos logs no alcanzan y será necesario
repetir la consulta.

Los tres campos de tokens quedan en `null` cuando el modelo no informa
`usage_metadata`, porque no se estiman a partir del largo del texto.
La consecuencia es que en esas consultas no queda registrado ningún
costo. Se prefirió un campo vacío antes que un número calculado que en
el log resultaría indistinguible de una medición.

---

## 6. Los logs se guardan, y nadie decide por cuánto tiempo

El logger escribe a `sys.stdout` y además a `logs/rag_legal.log`. La
lección muestra solo la salida por pantalla, con lo cual el registro
se pierde al cerrar la terminal, y eso contradice el motivo que la
misma lección plantea al comienzo, poder responder "por qué el bot
respondió eso a las 3am" cuando el proceso que respondió ya terminó.
Por eso aquí se agregó el `FileHandler`.

La ruta se arma desde la ubicación del módulo y no desde el
directorio actual, de modo que el archivo cae siempre en el mismo
lugar sin importar desde dónde se ejecute.

Lo que queda sin resolver es la retención. Ese archivo crece sin
tope, nadie lo rota y nadie lo borra. Con el volumen de hoy, que son
dieciséis líneas por corrida de comprobaciones, no es un problema.
Con un sistema atendiendo consultas de verdad, sí lo sería.

También queda sin resolver quién puede leer ese archivo. Hoy vive en
el disco de una sola persona, de modo que la pregunta no se plantea.
El día que el sistema corra en algún servidor, los permisos sobre ese
archivo pasan a ser parte de la gobernanza, porque aunque no guarde
textos, sí guarda el patrón de uso completo.

El archivo no entra al repositorio. `logs/` está en `.gitignore`.

### El trace_id tampoco pasa a un hilo nuevo

`contextvars` aísla el valor por tarea de ejecución, y un hilo nuevo
no hereda el contexto, de modo que `trace_id_var.get()` devuelve
`None` dentro de él. La lección lo señala y da la salida,
`contextvars.copy_context().run(...)`.

No aplica hoy, porque el flujo corre en un solo hilo. Aplicaría cuando
el sistema atienda consultas concurrentes, que es el escenario para el
que `contextvars` existe.

---

## 7. El punto de supervisión humana

Cada patrón detectado en una pregunta deja una línea con su
`trace_id`, el número de coincidencias y la acción tomada.

```json
{"evento": "inyeccion_en_pregunta", "n_patrones": 2,
 "accion": "registrada, la consulta sigue"}
```

La revisión periódica de los eventos `inyeccion_en_pregunta` y
`documento_descartado_por_inyeccion` constituye el punto de
supervisión humana de este riesgo. No requiere infraestructura nueva,
porque el registro ya existe, y `src/soporte_supervision.py` del
Bloque 23 ya contiene la forma de revisión.

Mientras esa revisión no se haga, el registro no reduce ningún riesgo.
Las líneas quedan escritas y no cambian nada si nadie las lee.

---

## 8. Lo que queda abierto

```
capa 1, separacion de roles     cambiar recuperacion.py, que esta
                                entregado y calificado
capa 2, delimitadores reales    el mismo cambio
persistencia de los logs        FileHandler y politica de retencion
patrones por canal              los seis son de documento, el canal
                                de la pregunta pide otros
```

### Las capas 1 y 2 se arreglan con un solo cambio

Incorporar `SystemMessage` y `HumanMessage`, y delimitar el contexto
con etiquetas reales, es un único cambio sobre el prompt del Bloque
28.

Hay una segunda razón para hacerlo, que viene de otro lado. El Bloque
28 dejó medido que en 4 de 20 respuestas el modelo le entrega al
usuario vocabulario de la instrucción interna, y que dos reescrituras
de esa instrucción empeoraron el resultado. Las dos modificaron las
palabras de la instrucción y ninguna modificó la estructura del
prompt.

Con el contexto delimitado, la instrucción podría dejar de referirse a
"el contexto" y referirse a los documentos o a las citas, con lo cual
el vocabulario interno dejaría de aparecer en la respuesta.

Es una hipótesis y no una conclusión. Se mide con
`src/probar_generacion.py`, cuatro corridas de cinco casos, igual que
las tres configuraciones ya medidas. Un solo experimento cubre las dos
cosas, la seguridad y la fuga de vocabulario.

No se hizo en este bloque porque modificar el prompt sin medir es el
procedimiento que ya falló dos veces.
