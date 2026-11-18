# Límites de la latencia y el costo del flujo RAG (Bloque 28)

Observaciones de las corridas del Bloque 28. El diseño del código está
documentado en las cabeceras de `src/registro_rag.py` y
`src/leer_registros.py`. Lo que sigue son los hallazgos medidos, las
decisiones que se tomaron con ellos y lo que quedó sin resolver.

Este bloque se salió de lo que pedía. La actividad pedía instrumentar
el flujo y guardar un registro. Al mirar los tokens de salida
aparecieron dos problemas de calidad que ninguna métrica anterior
veía, y arreglarlos obligó a cambiar el prompt del Bloque 26 y la
partición del Bloque 24. Todo eso queda documentado más abajo, con
sus mediciones.

---

## 1. Qué pedía el bloque y qué se entregó

```
  registro_rag.py                  la instrumentacion
  registros_latencia_costo.jsonl   una linea por corrida
  leer_registros.py                opcional, recomendado en clase
```

Las tres comprobaciones que pide la actividad pasan.

```
  cuatro corridas, cuatro lineas nuevas
  la misma pregunta con k=3 y k=6, y los tokens de entrada crecieron
  la generacion fue la etapa mas lenta en las cuatro
```

---

## 2. Lo que se hizo distinto de la lección, y por qué

La lección arma su propio flujo adentro de `registrar_consulta`, con
su plantilla de prompt, su `formatear_contexto`, sus embeddings y su
Chroma.

```
  la leccion                   este proyecto

  rearma el flujo completo     importa construir_prompt de
                               recuperacion.py

  Chroma sin collection_name   importa CARPETA_INDICE y COLECCION

  k=3 por defecto              el k del proyecto, importado

  el archivo en la raiz        al lado del script
```

La segunda no es preferencia. El índice de este proyecto vive en la
colección `corpus_legal_chile`, y conectarse sin nombrarla devuelve
una colección vacía sin lanzar ningún error. La consulta correría,
mediría tiempos y guardaría su registro con el contexto en blanco. La
propia lección 14 nombra ese fallo como la causa más común de un
`count() = 0`.

La primera evita que el proyecto quede con dos plantillas de prompt
que se pueden desincronizar.

### Una guarda agregada

La comprobación del índice vacío vive en `responder_con_citas` y no
en `construir_prompt`. Llamando al segundo se perdía, así que se
repite. Sin ella, una colección vacía haría pagar una generación
sobre un contexto en blanco y guardaría ese registro como si valiera.

### El registro guarda el tope y el solape

El registro de la lección guarda el `k` y no guarda la partición. Con
el `k` solo no se distingue una corrida de otra cuando la partición
cambió, y la de este proyecto cambió en este mismo bloque.

La lección advierte que este archivo no debe mezclar corridas sin
poder distinguirlas, porque sirve para comparar en el futuro. Con el
tope y el solape adentro, cada línea dice con qué configuración se
midió.

---

## 3. Las cuatro corridas

```
    k   embed+busq   generacion      total   entrada  salida
  ---------------------------------------------------------
    3      1267.15      5620.76    6887.91       882     109
    3      1327.12      8287.10    9614.22       902     416
    3       513.72       714.03    1227.75      1130      10
    6      1342.10     10231.00   11573.10      1834     433
```

Las tres preguntas se eligen por largo, del conjunto de evaluación
del Bloque 27, descartando las dos que el corpus no responde. El
largo es el criterio porque la lección advierte que una sola consulta
no es muestra y pide variar el largo antes de concluir sobre el
costo. El código las ordena, no se eligen a dedo.

La cuarta corrida es la misma pregunta del medio con `k=6`, que es la
comparación que pide la actividad.

### Por qué son cuatro y no cinco

El `k` del proyecto es 3, que es también el `k` bajo de la
comparación. Esa corrida ya está hecha y repetirla pagaría una
generación para escribir dos veces la misma línea.

---

## 4. El k mueve el costo y no mueve el tiempo

```
  k=3    902 tokens de entrada
  k=6   1834 tokens de entrada
         +932, unos 311 por cada fragmento extra
```

Con la partición anterior cada fragmento extra costaba unos 140
tokens. Con la de ahora cuesta 311, porque los fragmentos son dos
veces y media más grandes.

El tiempo no acompaña. En las corridas de este bloque el total va de
1227 a 11573 milisegundos sin relación con el `k`, y lo que lo mueve
es la generación y la red. Es lo que dice la lección 13, confirmado
con datos propios.

---

## 5. La salida pesa más que la entrada

Con las tarifas de ejemplo de la lección 13, que no son las reales de
Google y sirven para la proporción y no para el monto.

```
  pregunta         k  entrada  salida      costo   % salida
  ---------------------------------------------------------
  fuero laboral    3      882     109   0.000132      33%
  indemnizacion    3      902     416   0.000257      65%
  acoso            3     1130      10   0.000117       3%
  indemnizacion    6     1834     433   0.000357      49%
```

En las que responden de verdad, **la salida pesa el 51% del costo**.
Y ese número no cambia al agrandar los fragmentos, porque el modelo
no responde más largo porque el prompt sea más largo.

De ahí sale la consecuencia práctica de este bloque.

> Mirar solo cuánto creció el prompt engaña. Al pasar de la partición
> anterior a la de ahora, los tokens de entrada subieron un 59% y el
> costo total subió un 20%, porque la salida pesa más y no se mueve.

### La proyección aguantó

Antes de medir se proyectó el costo de la configuración nueva a
partir de la relación de caracteres por token de la configuración
anterior.

```
  proyectado   830 tokens de entrada, 260 de salida, costo 0.000187
  medido       892 tokens de entrada, 262 de salida, costo 0.000194
```

Cuatro por ciento de diferencia. El modelo de costo sirve para
estimar antes de pagar una corrida.

---

## 6. Los tokens de salida destaparon un problema de calidad

Este es el hallazgo central del bloque y no se fue a buscar.

La primera corrida del registro, con la configuración anterior, dio
esto.

```
  #   entrada  salida
  1       633      47
  2       565      10
  3       724      10
  4       411      10
  5       831      10
```

Diez tokens de salida, cuatro veces, el mismo número exacto. Diez
tokens en español son unas siete palabras, y cuatro respuestas a
preguntas distintas no dan el mismo largo por casualidad.

Eran abstenciones. El modelo respondía la frase de `SIN_CONTEXTO`.

**Y dos de esas preguntas tienen recall 1.00 en la evaluación del
Bloque 27.** El fragmento etiquetado llegaba al contexto y el modelo
decía que el contexto no alcanzaba.

```
  recall 1.00 significa   el fragmento etiquetado llego al contexto
  NO significa            que el modelo pueda responder con el
```

Ese hueco no lo mide ninguna de las dos métricas del Bloque 27.
Apareció porque este bloque cuenta los tokens de salida, y no por
otra cosa.

---

## 7. La pregunta compuesta

La pregunta que se abstenía era esta.

> ¿en qué consiste la indemnización por años de servicio y qué
> incluye?

Se probaron tres explicaciones y se descartaron dos, midiendo.

**No era el contexto.** El fragmento que responde llegaba textual.
El `[3]` del contexto decía *"el empleador deberá pagar al trabajador
una indemnización equivalente a treinta días de la última
remuneración mensual devengada por cada año de servicio y fracción
superior a seis meses... con un límite máximo de trescientos treinta
días"*.

**No era la redacción del prompt.** La frase de abstención quedaba
suelta en su línea, sin comillas, justo antes del contexto, y leída
de corrido parece una afirmación sobre esa consulta. Se probaron las
dos redacciones sobre el mismo contexto, dos corridas cada una.

```
  frase suelta      2 de 2 abstenciones
  entrecomillada    2 de 2 abstenciones
```

**Era la pregunta.** Con el contexto idéntico, los mismos cuatro
fragmentos y los mismos 2082 caracteres.

```
  entera, "en que consiste Y que incluye"   se abstiene, 4 de 4
  mitad 1, "en que consiste"                responde, 665 caracteres
  mitad 2, "que incluye"                    responde, 663 caracteres
  la redaccion del Bloque 26                responde, 1184 caracteres
```

Las dos mitades dan casi el mismo texto, 665 y 663 caracteres. Para
este corpus, *"en qué consiste"* y *"qué incluye"* son la misma
pregunta. Al recibir las dos juntas, el modelo no es que no tenga
información, es que se le piden dos respuestas distintas para algo
que tiene una sola.

### La causa, enunciada

> El prompt del Bloque 26 ofrecía dos salidas. Responder todo o
> abstenerse de todo. Ante una pregunta de dos partes y un contexto
> que cubre una, el modelo tomaba la segunda.

---

## 8. La plantilla de tres salidas

El arreglo agrega una salida intermedia.

```
  el contexto cubre todo       responde
  cubre una parte              responde esa parte y dice cual
                               parte no puede responder
  no cubre nada                la frase exacta de siempre
```

Se midió antes de adoptarla, con los controles que el Bloque 26
exige.

```
  las dos que fallaban, ahora responden   2 de 2
  los tres controles, siguen bien         3 de 3
```

Los controles eran la receta de cocina y la consulta de vacaciones,
que tienen que seguir recibiendo la frase exacta, y la consulta del
Bloque 26 que ya respondía y no se podía romper.

La respuesta a la pregunta con premisa muestra para qué sirve la
salida del medio.

> *El contexto establece que el contrato de trabajo termina sin
> derecho a indemnización cuando el empleador invoque conductas de
> acoso laboral [1]. **Sin embargo, el contexto no menciona si se
> requiere la existencia de pruebas** para proceder con dicho
> despido, por lo que esa parte no se puede responder con este
> contexto.*

Responde lo que está y nombra lo que falta. Para una consulta laboral
eso es mejor que las dos salidas anteriores, porque callarse entero
deja a la persona sin nada que sí estaba en la ley, y media respuesta
sin avisar la deja creyendo que tiene todo.

Esa misma respuesta tiene un error que se descubrió más adelante, y
está en la sección 14.

---

## 9. Trece fragmentos empezaban a media unidad

El segundo problema salió al revisar por qué el modelo presentaba
reglas condicionales como si fueran generales.

Con la partición anterior, medido con `src/medir_incisos.py`.

```
  fragmentos en total                      45
  fragmentos que nombran a su articulo     11
  fragmentos que no lo nombran             34   el 76%
  fragmentos que empiezan a media unidad   13
```

Los once que se nombran son uno por artículo, el primero de cada uno.
Del segundo en adelante el texto habla de plazos, montos y
condiciones sin decir de qué artículo viene.

De los trece que empiezan a media unidad, cuatro traen una regla sin
la condición que la limita.

```
  163 frag 6   "b) La obligacion del aporte..."   casa particular
  163 frag 3   "la prestacion antes señalada"     obra o faena
  161 frag 2   "Regira tambien esta norma"        gerentes y casa
                                                  particular
  168 frag 1   "a) En un treinta por ciento"      recargo judicial
```

### El daño, medido en una respuesta real

A la consulta *"¿cómo se calcula la indemnización por años de
servicio?"* el modelo respondió, entre otras cosas, esto.

> *Para los efectos del cálculo de la última remuneración, se
> entiende por tal el promedio de las remuneraciones percibidas
> durante la vigencia de su contrato o de los últimos once años.*

Eso es el artículo 40 bis D, y **rige solo para la jornada parcial de
treinta horas semanales o menos**. Lo presentó como la regla general.
Para alguien con jornada completa, ese promedio de once años puede
dar bastante menos que su última remuneración.

> *el monto de la indemnización puede quedar determinado por los
> aportes correspondientes al período respectivo.*

Eso es el régimen de indemnización a todo evento, que es para
trabajadores de casa particular. También presentado como general.

### Por qué pasaba

El corpus separa sus incisos con un salto de línea, igual que separa
las letras a) y b) de adentro de un inciso. El splitter prefiere
cortar en línea en blanco y después en salto simple, de modo que sin
esa distinción trata el borde entre dos incisos igual que el borde
entre dos letras.

La condición del artículo 163 está escrita en el corpus, en el
encabezado de su inciso 5.

> *Lo dispuesto en los incisos anteriores no se aplicará en el caso
> de terminación del contrato de los trabajadores de casa
> particular, respecto de los cuales regirán las siguientes normas.*

Y las letras a) y b) que esa frase condiciona caían en otros
fragmentos. De la condición al final de la letra b) hay 872
caracteres, y el tope eran 700, de modo que no cabían juntas con
ninguna reordenación.

---

## 10. La partición por inciso

El arreglo tiene dos partes y ninguna toca el texto legal.

**Separar los incisos con línea en blanco**, para que el splitter los
prefiera sobre los bordes de adentro de un inciso.

**Subir el tope** hasta que cada unidad estructural quepa entera.

```
  configuracion                    fragmentos   a media unidad
  ------------------------------------------------------------
  tope 700, sin separar incisos            45       13
  tope 700, separando incisos              46        9
  tope 1000, separando incisos             32        2
  tope 1500, separando incisos             19        0
  tope 2000, separando incisos             16        0
```

### El salto de línea no toca una palabra

La separación se aplica al preparar los documentos y no en el corpus.
El texto de `soporte_corpus_legal.py` está verificado contra la
fuente artículo por artículo, y esta es una decisión de indexación y
no del texto.

Lo que se inserta se comprobó.

```
  corpus antes      20480 caracteres
  corpus despues    20518 caracteres
  diferencia        38 saltos de linea

  el contenido sin espacios es identico en los 11 articulos
  los caracteres insertados son unicamente  '\n'
```

---

## 11. Por qué el tope es 1500

Este número no se eligió mirando qué preguntas fallaban. Esa objeción
ya había descartado subir el tope a 1000 en el Bloque 27, y vale
igual para esta decisión.

```
  unidades estructurales del corpus   49
  la mas larga                        1057 caracteres, art. 168

  cuantas caben enteras
      tope  700    40 de 49    82%
      tope 1000    47 de 49    96%
      tope 1500    49 de 49   100%
```

**La regla no es el número, es el criterio.** El tope tiene que ser
mayor que la unidad estructural más larga del corpus. Eso es una
propiedad del texto y no de las preguntas. Cuando el corpus crezca y
entre un inciso más largo, se vuelve a correr `medir_incisos.py` y se
sube.


### Por qué se buscaron referencias

La opción de cortar por la unidad legal se planteó al ver los trece
fragmentos de la sección 9, pero no había seguridad de que fuera el
camino correcto. Los intentos anteriores habían fallado, el tope y
el solape en el Bloque 24, el k y la línea de contexto en el Bloque
27, los cuatro medidos y los cuatro descartados, y nada garantizaba
que este no fuera otro ajuste más. Antes de reescribir el indexador
se buscó si alguien había resuelto este mismo problema en proyectos
de este tipo, sobre textos legales.

Lo que apareció confirmó que el camino era el que se usa en ese
dominio, y precisó su forma, cortar primero por el límite legal y
partir de manera recursiva solo adentro de la unidad. Los números
siguieron saliendo de medir este corpus.

NitiBench, sobre legislación tailandesa, describe el fallo en los
mismos términos en que apareció aquí. Las citas de trabajos
publicados van traducidas del inglés, que es su idioma original, y la
ubicación de cada una está indicada en la sección 17.

> *Como la estrategia ingenua de partición no sabe dónde terminan las
> secciones, el texto partido puede contener varias secciones, si la
> sección es más corta que el tope, o quedar incompleto, si la
> sección es más larga que el tope.*

Incompleto cuando la unidad es más larga que el tope. El artículo 168
mide 1057 caracteres y el tope anterior era 700, así que caía justo
en ese caso.

Ese trabajo mide además cuánta información pierde cada estrategia. La
fila que más importa es la segunda, porque ahí afinaron la mejor
estrategia ingenua hasta su mejor tope y su mejor solape.

```
  estrategia                        Chunks/Seccion   Secciones
                                                     partidas
  jerarquica                            1.000          0.000
  por lineas, afinada a 553 y 50        1.180          0.323
  por lineas                            1.234          0.417
  recursiva                             1.270          0.504
  por caracteres                        1.710          0.675
```

La primera columna es la cantidad media de fragmentos que cubren una
sección y la segunda es la proporción de secciones que no quedan
enteras. Afinar los números mejora el resultado sin arreglarlo, que
es exactamente lo que pasó en los Bloques 24 y 27 de este proyecto.

Los mismos autores advierten que la ventaja de punta a punta es leve,
y la explican porque el modelo alcanza a filtrar el ruido. El caso de
este proyecto es distinto. Lo que faltaba no era ruido, era ausencia,
y un modelo puede descartar ruido pero no puede recuperar lo que
nunca recibió. Aun así, ellos miden sobre un banco de pruebas grande
y este proyecto mide sobre dieciséis preguntas, que alcanzan para una
dirección y no para una magnitud.

Lo que dicen los otros trabajos, con sus citas, está en la sección
17.

---

## 12. La curva de k y por qué k vale 3

Medida con la evaluación del Bloque 27 contra la partición nueva.

```
    k  precision   recall      F1
  --------------------------------
    1      0.625    0.643   0.634
    2      0.344    0.714   0.464
    3      0.271    0.857   0.412   <-- el elegido
    4      0.219    0.893   0.351
    5      0.175    0.893   0.293
    6      0.146    0.893   0.251
    7      0.125    0.893   0.219
    8      0.125    0.964   0.221
```

Contra la configuración anterior.

```
                      precision   recall      F1
  ------------------------------------------------
  antes, 700, k=4         0.203    0.821   0.326
  ahora, 1500, k=3        0.271    0.857   0.412
                         +0.068   +0.036  +0.086
```

**Mejora en las tres a la vez.** No es un intercambio.

### Por qué no se sube al 4

```
  recall sube     +0.036, media pregunta de catorce
  precision baja  -0.052
  costo sube      +14%
```

Esa media pregunta es la **#15**, la del finiquito indefinido o plazo
fijo, que es la que falla de la manera contenida, abstieniéndose en
vez de contestar otra cosa.

Es la misma cuenta de la sección 5 del `limites_bloque27.md`, donde
subir el k arreglaba solo esa pregunta y por eso no se subió. La
regla tiene dos partes y conviene dejarla escrita entera.

> El recall pesa más que la precisión, porque un fragmento que no
> llega no lo compensa ningún prompt. Pero no se paga un recall que
> solo alcanza preguntas que ya fallaban abstieniéndose.

### Un error que arrastraba desde el Bloque 27

La salida de `evaluacion_recuperacion.py` imprimía solo la primera
parte de esa regla, y decía quedarse con el k del recall mientras el
k elegido era otro. En la corrida del Bloque 27 decía *"el recall
deja de subir en k=6"* con el k en 4, y no se lo notó. Quedó
corregido y ahora imprime las tres lecturas, la del recall, la del F1
y la del k del proyecto.

### El costo de subir el tope

```
  config            k  entrada  salida       costo   vs antes
  ------------------------------------------------------------
  antes, 700        4      522     260    0.000156    1.00x
  1500 doble        2      587     260    0.000163    1.04x
  1500 doble        3      830     260    0.000187    1.20x
  1500 doble        4     1073     260    0.000211    1.35x
```

Un veinte por ciento más por consulta. Lo que compra ese veinte por
ciento es que ninguna regla llegue al modelo separada de la condición
que la limita.

---

## 13. Lo que la generación ganó

Verificado contra producción con `src/probar_generacion.py`.

```
  la del calculo   responde, 2059 caracteres, cita 163, 172 y 40 bis D
  el pastel        se abstiene con la frase exacta
  la #11           responde y nombra lo que le falta
  reglas nombradas sin su condicion   0
```

El error del artículo 40 bis D está arreglado. Ahora el modelo
escribe esto.

> ***Casos especiales (jornada no superior a 30 horas semanales):**
> Para contratos de jornada no superior a treinta horas semanales, se
> entiende por última remuneración el promedio de las remuneraciones
> percibidas...*

Nombra la condición y la pone como encabezado del punto.

### Apareció el artículo 172

Con la partición anterior ese artículo no llegaba al contexto de esa
consulta. Ahora llega y se cita, y con él la respuesta trae **el tope
de 90 unidades de fomento**, las remuneraciones variables y qué se
excluye de la base de cálculo. Ese tope es un límite real que el
sistema no mencionaba nunca.

### La pregunta 11 dejó de ser peligrosa

```
  antes
      hablo del juicio en sesenta dias habiles y del recargo del
      treinta por ciento, y se callo lo que la persona preguntaba.
      Fluida, citada y silenciosamente incompleta

  ahora
      "...El contexto no responde ni detalla cuales son los montos
      base ni los componentes exactos de las indemnizaciones
      generales a las que se tiene derecho por necesidades de la
      empresa"
```

**La recuperación de la #11 sigue fallando igual, recall 0.00.** Pero
el modelo ya no lo esconde. El fallo peligroso, el que contesta
otra cosa sin avisar, dejó de estar. Queda un fallo honesto.

---

## 14. Lo que la generación perdió, y por qué no es una pérdida

Una consulta que respondía con la partición anterior ahora se
abstiene, de manera estable, tres corridas de tres.

> tengo un conflicto con una compañera que me hostiga y no tengo
> pruebas, ¿pueden despedirme por eso?

La evaluación le mide recall 1.00, de modo que el fragmento
etiquetado llega.

Pero al leer la respuesta anterior con cuidado, tenía un error.

```
  la respuesta anterior decia
      "el contexto no menciona si se requiere la existencia de
       pruebas para proceder con dicho despido"

  el articulo 160 en el contexto dice
      "1.- Alguna de las conductas indebidas de caracter grave,
       debidamente comprobadas... f) Conductas de acoso laboral"
```

El contexto sí lo menciona. *"Debidamente comprobadas"* es
exactamente el requisito de prueba. La respuesta afirmaba que la ley
no decía algo que la ley sí dice.

```
  antes     respuesta parcial con una afirmacion falsa sobre el
            requisito de prueba
  ahora     abstencion
```

Para una consulta laboral, callarse es mejor que decirle a alguien
que la ley no exige pruebas cuando sí las exige.

### El mecanismo, que sí es un costo real

```
  antes    contexto de 2461 caracteres, 4 fragmentos
  ahora    contexto de 4071 caracteres, 3 fragmentos
```

Sesenta y cinco por ciento más texto, y **dos de los tres fragmentos
son del artículo 168**, que habla del juicio y de los recargos y no
tiene nada que ver con esa pregunta.

Fragmentos más grandes traen más texto irrelevante por fragmento. La
precisión bajando se ve en la tabla de la sección 12, y en la
conducta del modelo se ve así, que con más ruido decide no
contestar.

Ese es el costo de la partición grande, y no estaba en ninguna de las
dos métricas.

---

## 15. La reindexación no borraba

Al reindexar con la configuración nueva, la verificación del Bloque
24 avisó.

```
  indexados 19 fragmentos
  fragmentos guardados   45
```

La cabecera de `indexar_corpus.py` afirmaba que con ids explícitos
volver a indexar sobrescribe en vez de duplicar. Eso es cierto
mientras los ids nuevos incluyan a los viejos.

El artículo 163 daba siete fragmentos y ahora da tres. Los ids
`art_163_3` a `art_163_6` **no se sobrescribieron porque ya no se
generan**, y quedaron en la colección con su texto partido a la
antigua. Veintiséis fragmentos viejos mezclados con diecinueve
nuevos.

Era la primera vez que el número de fragmentos bajaba en lugar de
subir, y por eso nunca había aparecido.

**No se habría notado sin `--verificar`.** La búsqueda no lanza
ningún error ante un fragmento viejo, lo devuelve como cualquier
otro.

La indexación ahora borra, al terminar, los ids que están en la
colección y no están en la tanda que acaba de escribir. Borra después
y no antes para que un fallo a mitad de camino no deje el índice
vacío.

---

## 16. Errores de medición corregidos

Van escritos porque son la razón de que los scripts de este bloque
tengan guardas.

**Un chequeo que confunde ausente con correcto.** El script que
verifica si una regla llega con su condición solo informa cuando la
regla está nombrada. Si el modelo no la nombra, se queda callado, y
callado no es lo mismo que correcto. En la verificación de la
partición nueva eso hizo que el error del aporte figurara como
resuelto cuando en realidad estaba evitado, porque ese fragmento ya
no se recupera para esa consulta. El límite quedó escrito en la
cabecera del script, pero el chequeo en sí no cambió, así que queda
anotado como pendiente 5 de la sección 18.

**Una prueba de fallo que no probaba nada.** Para comprobar que una
corrida interrumpida no escribe líneas sueltas, el primer intento
parcheaba la función desde afuera y el script se volvía a cargar
pisando el parche. Corrió las cinco consultas y escribió cinco líneas
más. Se rehizo haciendo fallar al modelo falso en la tercera llamada,
y ahí sí.

**Un experimento que dejó de reproducir lo suyo.**
`probar_linea_contexto.py` importaba el tope y el solape del
indexador, así que al cambiarlos en este bloque daba cuarenta y seis
fragmentos en vez de los cuarenta y cinco que documentó el Bloque 27.
Quedó fijado en su propia configuración, incluido el texto sin
separar, y vuelve a dar 45, 34 y 379%.

**El k escrito en dos lugares.** `RECUPERADOS` en `recuperacion.py` y
`K_ELEGIDO` en `evaluacion_recuperacion.py` eran el mismo número en
dos archivos. Si uno cambiaba sin el otro, la evaluación mediría un k
que la aplicación no usa. Ahora el segundo importa al primero.

---

## 17. Referencias

Las dos decisiones de este bloque salieron de medir este corpus. Las
referencias se buscaron cuando la solución estaba planteada pero no
confirmada, para ver si alguien había resuelto lo mismo en textos
legales. Sirvieron para confirmar el camino y precisar su forma, no
para fijar ningún número.

Las citas van traducidas del inglés, que es el idioma original de los
tres trabajos, con la ubicación en el original indicada en cada caso.

```
  Anthropic, "Introducing Contextual Retrieval", septiembre de 2024
  anthropic.com/news/contextual-retrieval

  Akarajaradwong et al., "NitiBench, Benchmarking LLM Frameworks on
  Thai Legal Question Answering Capabilities"
  EMNLP 2025, actas principales, 24 paginas
  aclanthology.org/2025.emnlp-main.1739
  la cita y la tabla de la seccion 11 salen de su seccion 4.1 y de
  su tabla 16. El preprint arXiv 2502.10868 es un informe tecnico
  mas largo, con otra redaccion, y no se cita de ahi

  Jove-Ticona, Duarte-Coaquera, Chaparro-Cruz, Cabana-Yupanqui y
  Chaparro-Guerra, "A New Metadata-Aware Retrieval-Augmented
  Generation (RAG) Architecture for Trustworthy Legal Question
  Answering", IJACSA vol. 17 no. 8, 2026
  DOI 10.14569/IJACSA.2026.0170868
  Universidad Nacional Jorge Basadre Grohmann, Tacna, Peru
```

### El trabajo peruano, que es el de dominio más cercano

Es derecho laboral, y ahí la configuración anterior de este proyecto
tiene nombre, porque es la línea base contra la que miden.

> *Una línea base ingenua de RAG parte por lo general los documentos
> en ventanas de largo fijo, con solapes chicos y limpieza mínima.*

Eso era tope 700 y solape 126. Lo que proponen en su lugar es lo que
quedó en este proyecto, y está en su sección IV, en los detalles de
reproducibilidad.

> *El pipeline de partición de documentos usa un corte estructural
> primario basado en los límites legales, por ejemplo decretos, leyes
> o artículos completos, seguido de sub-partición recursiva con una
> ventana máxima de 250 tokens y un solape de 30 tokens, para
> preservar el contexto de los bordes.*

Doscientos cincuenta tokens, a la razón de cinco caracteres por token
que se desprende de la sección 4, son unos 1250 caracteres. El tope
de este proyecto queda en el mismo rango, un quinto más grande.

Subir el tope tiene un riesgo, y ese trabajo lo nombra en su
introducción.

> *Los fragmentos demasiado gruesos diluyen el foco temático. Los
> demasiado finos pierden contexto legal esencial y los anclajes de
> cita.*

Demasiado fino pierde el contexto legal, que es lo que hacía el tope
de 700 con el alcance del artículo 40 bis D. Demasiado grueso diluye
el foco, y la precisión de la sección 12 contesta esa mitad, porque
subió de 0.203 a 0.271 en vez de bajar.

De su sección III.A sale la confirmación de algo que este proyecto ya
hacía desde el Bloque 24.

> *Cada fragmento retiene una copia completa del metadato de su
> documento padre, lo que asegura que el contexto estructural se
> preserve. Esto permite al sistema mantener referencias precisas a
> la fuente de cada fragmento, algo crítico tanto para la exactitud
> como para la trazabilidad en las tareas posteriores.*

Eso es el metadato `articulo`, puesto al partir y heredado por cada
fragmento. En la literatura se llama **metadata inheritance**.

Ese trabajo hay que leerlo sabiendo la diferencia de tamaño. Su
corpus pasa de 3000 páginas y deja más de 6000 sub-fragmentos, con
seis campos de metadato en cada uno. Este tiene once artículos
partidos en diecinueve fragmentos, y un solo campo. Respalda el
diseño y no la escala.

### Contextual retrieval

Agregar contexto al fragmento antes de indexarlo tiene nombre propio,
y Anthropic lo publicó con tres cifras que miden cosas distintas.

```
  contextual embeddings solos                 -35%   5.7% a 3.7%
  mas contextual BM25, busqueda hibrida       -49%   5.7% a 2.9%
  las dos mas un reordenador                  -67%   5.7% a 1.9%
```

Son reducciones del fallo de recuperación sobre los veinte primeros
fragmentos. Las trece notas que este corpus tiene desde el Bloque 21
son una versión a mano de la primera, la del 35%. Las otras dos piden
la búsqueda por palabra clave del Bloque 21 y un reordenador, y
quedan anotadas en la sección 18. Esas cifras se midieron recuperando
veinte fragmentos y este proyecto recupera tres, así que dan la
dirección y no la magnitud.

---

## 18. Lo que queda pendiente

**De este bloque.**

1. La pregunta 11 sigue con recall 0.00 y es la única que queda en
   cero. La causa está identificada desde la sección 11 del
   `limites_bloque27.md`, la referencia cruzada entre artículos. El
   artículo 163 dice *"en conformidad al artículo 161"* y el embedding
   no puede seguir esa referencia.
   Se descartaron cuatro vías midiendo, el tope, el solape, el k y la
   línea de contexto. Las que quedan.
```
  re-ranking        recuperar veinte y reordenar para quedarse
                    con unos pocos. Es lo que hace el trabajo
                    peruano, y art_163_0 podria estar en el top
                    20 aunque no este en el top 8

  busqueda hibrida  juntar la semantica con la de palabras clave
                    del Bloque 21, que devuelve articulos enteros.
                    La mitad ya esta escrita

  expandir la       el modelo saca terminos legales relacionados
  consulta          antes de buscar

  buscar dos veces  se busca, se ve que salio el 161, y como el
                    163 lo referencia se vuelve a buscar
```

   La primera es la que tiene respaldo publicado más directo.

2. La consulta del acoso se abstiene de manera estable con la
   partición nueva. La sección 14 explica por qué no se considera una
   regresión, pero una respuesta parcial correcta sería mejor que una
   abstención.
3. Las preguntas 10 y 15 quedan en recall 0.50, con su fragmento en
   el borde del corte.
4. El registro de latencia no guarda la versión del prompt. Entre la
   primera corrida y la última cambiaron la partición y el prompt, y
   el archivo solo distingue la primera. Si el prompt vuelve a
   cambiar, convendría que también quede en el registro.
5. El chequeo de alcance de `probar_generacion.py` confunde ausente
   con correcto. Solo informa de una regla cuando el modelo la
   nombra, así que una regla que el modelo nunca menciona deja el
   chequeo callado, y callado no es correcto. El límite está escrito
   en la cabecera del script, pero el chequeo en sí sigue igual.
   Arreglarlo pide distinguir las tres salidas, regla presente y
   correcta, regla presente y equivocada, y regla ausente.
**Que vienen de bloques anteriores y siguen abiertos.**
6. Apretar o afinar la abstención, planteado en el Bloque 27. La
   plantilla de tres salidas cubrió parte, pero el caso del acoso
   muestra que queda trabajo.
7. Migrar el corpus de `src/soporte_corpus_legal.py` a archivos
   `.md`. Esto dejó de ser una idea propia. El trabajo peruano de la
   sección 17 convierte los documentos a Markdown como formato
   intermedio antes de segmentarlos, y limpia encabezados y pies en
   ese paso.
   > *En una etapa inicial, estos archivos se convierten a un
   > formato intermedio, como Markdown (.md).*
8. El empate de cuatro milésimas de la sección 6 del
   `limites_bloque27.md` no tiene tratamiento. El corte en k es duro
   y parte empates que no significan nada.
9. Volver a medir la línea de contexto del Bloque 27 cuando el corpus
   crezca.
10. Cerrar el hueco de `--verificar`, planteado en el Bloque 26 y
   todavía abierto. Compara cuántos fragmentos hay guardados contra
   cuántos daría el corpus de hoy, así que atrapa que se agregue o se
   saque un artículo, y no atrapa un cambio de texto que no cambie la
   cuenta. Cerrarlo pide comparar el contenido y no la cuenta.
