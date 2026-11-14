# Límites de la evaluación de la recuperación (Bloque 27)

Observaciones de las corridas del Bloque 27. El diseño del código está
documentado en la cabecera de `src/evaluacion_recuperacion.py`. Lo que
sigue son los hallazgos medidos, las decisiones que tomamos con ellos y
lo que quedó sin resolver.

---

## 1. Qué se corrió

Dieciséis preguntas contra el índice del corpus legal, con los parámetros
que ya venían del Bloque 24.

```
  fragmentos indexados    45
  tope del fragmento      700
  solape                  126
  modelo de embeddings    models/gemini-embedding-001
  coleccion               corpus_legal_chile
  k evaluado              4, y la curva de 1 a 8
```

De las dieciséis preguntas, catorce tienen respuesta en el corpus y dos
no. Las dos sin respuesta están ahí a propósito, para ver si el sistema
se abstiene cuando no tiene con qué contestar.

En total hay dieciocho fragmentos etiquetados como relevantes, repartidos
entre las catorce preguntas con respuesta. Cuatro preguntas necesitan dos
fragmentos cada una, porque la respuesta completa está partida entre dos
artículos.

---

## 2. Las dos medidas, y por qué no dicen lo mismo

La fórmula es la de la plataforma, copiada sin cambios.

La **precisión** mira lo que trajo la búsqueda y pregunta cuánto de eso
servía. Si trae cuatro fragmentos y dos eran los buenos, la precisión es
0.50.

El **recall** mira lo que hacía falta y pregunta cuánto de eso llegó. Si
hacían falta dos fragmentos y llegaron los dos, el recall es 1.00, sin
importar que además hayan llegado otros dos de relleno.

Las dos se mueven en contra. Traer más fragmentos sube el recall, porque
es más difícil que se quede algo afuera, y baja la precisión, porque la
proporción de relleno crece.

Para una consulta legal el recall pesa más. Una respuesta a la que le
falta el artículo que decide el caso está mal, y el usuario no tiene cómo
saberlo. Un fragmento de relleno en el contexto, en cambio, lo descarta
el modelo al redactar.

### Las dos sin respuesta cuentan distinto

Esto importa para leer los números y no estaba a la vista.

Cuando una pregunta no tiene respuesta en el corpus, no hay ningún
fragmento relevante. Entonces la precisión de esa pregunta es 0.0, porque
todo lo que trajo era relleno, y ese 0.0 **entra al promedio**. El recall,
en cambio, devuelve `None`, porque dividir por cero fragmentos relevantes
no significa nada, y queda fuera del promedio.

Con dos de dieciséis preguntas sin respuesta, la precisión arrastra un
lastre de origen. Dos ceros forzados sobre dieciséis es un techo de 0.875
que esa medida nunca va a pasar, por buena que sea la búsqueda.

El recall se promedia sobre catorce. Por eso cada punto de recall vale
una catorceava parte, 0.071, y eso vuelve a aparecer más abajo.

---

## 3. El resultado en k=4

```
  precision    0.203
  recall       0.821
  F1           0.326
```

Visto pregunta por pregunta, el 0.821 se arma así.

```
  once preguntas en 1.00
  una  pregunta  en 0.50     la #10
  dos  preguntas en 0.00     la #11 y la #15
  dos  preguntas sin medir   no tienen respuesta en el corpus

  11.5 / 14 = 0.821
```

Diez de las catorce traen todo lo que necesitan. El problema está
concentrado en tres.

---

## 4. La curva de k, de 1 a 8

La curva no cuesta ninguna llamada extra. Se recupera una vez pidiendo
ocho fragmentos y después se va cortando la lista, `ranked[:k]`, para
cada k. Los números son los mismos que si se hubiera consultado ocho
veces.

```
  k    precision   recall      F1
  --------------------------------
  1       0.500    0.536    0.517
  2       0.312    0.643    0.421
  3       0.250    0.750    0.375
  4       0.203    0.821    0.326
  5       0.175    0.857    0.291
  6       0.156    0.893    0.266
```

Entre k=6 y k=8 el recall no se mueve, se queda en 0.893. Eso significa
que lo que falta no aparece en el top 8 de ninguna manera, y por eso la
tabla se corta en el 6. La precisión de esas dos filas no quedó anotada,
y el motivo está en la sección 16.

La curva dice dos cosas distintas según qué medida se mire.

El **F1 tiene su máximo en k=1**, con 0.517, y baja desde ahí sin
recuperarse. Si la decisión se tomara por el F1, habría que traer un solo
fragmento.

El **recall sigue subiendo hasta k=6** y ahí se planta. Entre el 6 y el 8
no se mueve, 0.893, lo que significa que lo que falta no está en el top 8
de ninguna manera.

Elegimos el recall por lo que dice la sección 2. Un F1 alto con un solo
fragmento significa que ese fragmento viene limpio, no que la respuesta
esté completa.

---

## 5. Por qué el k se queda en 4

El k=4 viene del Bloque 26, donde se eligió midiendo distancias. La
pregunta de este bloque es si la evaluación lo cambia.

La curva invita a subirlo a 6, porque el recall pasa de 0.821 a 0.893.
Pero hay que mirar **de dónde sale esa ganancia**.

```
  de k=4 a k=6 el recall sube 0.071
  0.071 es una catorceava parte
  es una sola pregunta, la #15
```

La #15 es la única que gana algo. La #11 se queda en 0.00 incluso con
ocho fragmentos, y la #10 se queda en 0.50.

Y la #15, como se ve en la sección 7, es la pregunta en la que el sistema
**se abstuvo**. Falló de la manera contenida.

Entonces subir el k arregla la pregunta que ya estaba a salvo y no hace
nada por la peligrosa, mientras la precisión baja de 0.203 a 0.156. No es
un intercambio que convenga.

**El k se queda en 4, ahora con una cuenta detrás y no solo con las
distancias del Bloque 26.**

---

## 6. Las tres que fallan

```
  #10   recall 0.50
        "trabajo veinte horas a la semana, como se calcula mi
         indemnizacion?"
        falta art_40_bis_0, fuera del top 8

  #11   recall 0.00
        "me despidieron por necesidades de la empresa, a que
         tengo derecho?"
        faltan art_163_1 y art_162_2, los dos fuera del top 8

  #15   recall 0.00
        "hay diferencia en el finiquito si mi contrato es
         indefinido o a plazo fijo?"
        faltan art_159_0 y art_163_0, en las posiciones 6 y 5
```

La #15 es un empate perdido por cuatro milésimas.

```
  posicion 4    0.6164    entro
  posicion 5    0.6206    art_163_0, quedo afuera
  posicion 6    0.6207    art_159_0, quedo afuera
```

Entre el cuarto y el quinto hay 0.0042 de diferencia. Entre el quinto y
el sexto, 0.0001. El corte en cuatro los parte por un margen que no
representa ninguna diferencia real de pertinencia.

---

## 7. Fallar y fallar peligrosamente no son lo mismo

Las dos preguntas en 0.00 tienen la misma nota y consecuencias opuestas.

En la **#15**, el modelo no encontró con qué contestar y se abstuvo. Usó
la frase exacta que el prompt le da para eso. El usuario queda sin
respuesta, que es molesto, pero no queda con una respuesta equivocada.

En la **#11**, el modelo contestó. Habló del reclamo judicial del
artículo 168, del plazo de sesenta días hábiles y del recargo del treinta
por ciento, todo correcto y todo citado. Y se calló justamente lo que la
persona preguntó, que es a qué tiene derecho cuando la despiden por
necesidades de la empresa.

**Una respuesta fluida, citada y que omite lo central es peor que no
responder**, porque no se nota. El usuario no tiene manera de saber que
le falta algo.

Esta distinción no sale de la fórmula. Las dos preguntas valen 0.00 para
el recall. Sale de leer las respuestas.

---

## 8. Setenta y seis de cada cien fragmentos no saben de qué artículo son

Medido con `src/probar_linea_contexto.py --solo-revisar`.

```
  Fragmentos en total                      45
  Fragmentos que nombran a su articulo     11
  Fragmentos que no lo nombran             34
  Proporcion sin identificar               76%
```

Once de cuarenta y cinco, uno por artículo. La razón es de formato. El
rótulo del artículo vive en su propia línea, y el corte de 700 lo deja
solo en el primer fragmento. Del segundo en adelante el texto habla de
plazos, montos y condiciones sin decir nunca de qué artículo viene.

La etiqueta del artículo sí está en el metadato, y por eso las citas
salen bien. Pero **el metadato no se convierte en embedding**. Solo el
texto se convierte. Para la búsqueda, esos treinta y cuatro fragmentos
son anónimos.

---

## 9. El experimento de la línea de contexto

Con el 76% a la vista, la hipótesis era que si cada fragmento llevara
arriba una línea diciendo de qué artículo es y de qué trata, la búsqueda
los encontraría mejor.

### La línea no la redactó nadie

Una línea escrita a mano resumiendo el artículo no se puede comprobar sin
leer el artículo completo, y con un corpus de cien artículos eso no
escala. Así que la línea se **extrae del corpus**, con una regla.

```
  la linea = el rotulo del articulo + la primera frase de su contenido
```

Las dos partes son texto copiado. El script busca cada una dentro de su
artículo y confirma que esté, carácter por carácter. Si pasa, la línea no
puede decir nada que el artículo no diga.

Las once salieron copiadas. Diez son un solo pedazo contiguo del original.
La del artículo 66 son dos pedazos, porque ese artículo separa el rótulo
del texto con un guión y las demás con un salto de línea.

```
  largo de la linea     de 83 a 194 caracteres
  promedio              157
  recorte aplicado      180
```

### Cómo se evitó que el experimento se falseara solo

La línea se pega **después** de fragmentar, así que el corte de 700 no
cambia y los cuarenta y cinco fragmentos siguen siendo cuarenta y cinco.

Pero hay una trampa menos visible. Las etiquetas de relevancia se
resuelven buscando frases del corpus dentro de los documentos guardados.
Si la primera frase de un artículo queda pegada arriba de todos sus
fragmentos, una frase que antes resolvía a un fragmento resolvería a
cinco, y el recall subiría sin que la búsqueda hubiera mejorado nada.

Por eso las etiquetas se resuelven contra los fragmentos **sin línea** y
quedan fijas. Lo que se compara después es solamente la recuperación.

La prueba se indexó en una carpeta y una colección aparte,
`vectorstore_pruebas/corpus_con_linea`. La colección de producción no se
abrió ni para leer.

---

## 10. La línea costó recall

```
                   precision    recall        F1
  ----------------------------------------------
  sin linea            0.203     0.821     0.326
  con linea            0.188     0.750     0.300
  diferencia          -0.016    -0.071    -0.026
```

Ese 0.071 es, otra vez, una catorceava parte. **Cambió exactamente una
pregunta.** Trece quedaron idénticas y la #4 pasó de 1.00 a 0.00.

```
  0.821 = 11.5 / 14        0.750 = 10.5 / 14
```

### Por qué se rompió la #4

La pregunta es *"me avisaron el despido con una carta común, no
certificada, ¿vale igual?"* y el fragmento que necesita es `art_162_0`,
el que habla de la carta certificada.

La línea que le quedó encima es esta.

```
  "Art. 162. Si el contrato de trabajo termina de acuerdo con
   los numeros 4, 5 o 6 del articulo 159, o si el empleador le
   pusiere termino por aplicacion de una o mas de las causales
   senaladas"
```

Ahí no se menciona ninguna carta. Son ciento ochenta y ocho caracteres
sobre causales de término pegados arriba de un fragmento que trataba del
aviso. El embedding del fragmento se corrió hacia las causales y
`art_162_0` cayó a la posición 5.

**La línea no lo ubicó, lo diluyó.** El efecto es mayor donde el
fragmento es corto, porque la línea pasa a ser la mayor parte de lo que
se convierte en embedding. Los fragmentos crecieron entre 114% y 379% de
su largo original, y el 379% es un fragmento de sesenta y ocho caracteres
del artículo 160.

---

## 11. Por qué la pregunta 11 no se movió ni un lugar

Este es el hallazgo que importa del experimento.

```
  #11   antes    art_163_1 y art_162_2 fuera del top 8
        despues  art_163_1 y art_162_2 fuera del top 8
```

La línea del artículo 161 **sí** contiene las palabras exactas de la
pregunta.

```
  "Art. 161. Sin perjuicio de lo senalado en los articulos
   precedentes, el empleador podra poner termino al contrato de
   trabajo invocando como causal las necesidades de la empresa,"
```

Pero esa línea va arriba de los fragmentos **del 161**. Los fragmentos
que hacen falta son del 163 y del 162, y sus líneas dicen otra cosa. La
del 163 dice *"en conformidad al artículo 161"*, que es una referencia a
otro artículo.

La búsqueda semántica compara texto contra texto. Convierte la pregunta
en números, convierte cada fragmento en números y mide qué queda cerca.
Cuando el artículo 163 dice *"en conformidad al artículo 161"*, para la
búsqueda es una frase más. **No sabe que hay otro artículo del otro lado
de esa referencia y no lo va a ir a buscar.**

De ahí el límite, enunciado con precisión.

> Una línea de contexto solo puede agregar palabras que estén en el
> propio artículo. La condición que la pregunta 11 necesita vive en otro
> artículo, y ninguna línea por artículo va a meter las palabras del 161
> adentro de los fragmentos del 163.

Eso no se arregla con el tope, ni con el solape, ni con el k, ni con
líneas de contexto. Es otra clase de problema y está anotado en la
sección 14.

---

## 12. Un defecto del propio experimento

La línea del artículo 40 bis quedó cortada.

```
  "Art. 40 bis. Se podran pactar contratos de trabajo con jornada
   a tiempo parcial, considerandose afectos a la normativa del
   presente parrafo, aquellos en que se ha convenido una jornada
   de"
```

Termina en *"una jornada de"*. El recorte en ciento ochenta caracteres se
llevó justo las palabras que seguían, *"no superior a treinta horas
semanales"*. Y la pregunta #10 es *"trabajo veinte horas a la semana"*.

Es el mismo patrón de los diecinueve caracteres del Bloque 26. Un corte
que cae justo antes de lo que decide.

Así que al experimento le falta decir que la #10 no tuvo su mejor
oportunidad.

---

## 13. Por qué no se insistió

Antes de pedir otra indexación se hizo la cuenta.

```
  perdida de la #4                    -0.071
  ganancia maxima posible de la #10   +0.036
  mejor caso imaginable                0.786   contra 0.821
```

Aun arreglando el recorte, y suponiendo que la #10 llegara a 1.00, el
resultado queda por debajo de la base. La dilución de la #4 es
independiente del recorte, así que no se compensa. Media catorceava parte
no alcanza a cubrir una catorceava parte entera.

La única manera de que el experimento diera mejor sería poner la línea en
algunos artículos y no en otros, eligiendo según cuáles preguntas fallan.
Eso es acomodar el corpus a estas dieciséis preguntas, y es la misma
objeción que descartó subir el tope a 1000 en el Bloque 26.

**La línea de contexto se descarta.** El código que la prueba queda en el
repositorio, en `src/probar_linea_contexto.py`, para que la medición se
pueda repetir.

Con once artículos la confusión entre artículos es chica, y por eso la
línea solo molesta. Con cien podría pagar. Eso no se puede medir todavía
y queda anotado como pendiente, no como conclusión.

---

## 14. Dos errores de medición que se corrigieron antes de concluir

Vale la pena dejarlos escritos, porque son la razón de que el script de
prueba tenga guardas.

**El primero.** Una corrida del experimento dio 0.000 en las tres
medidas, en las dieciséis preguntas. No era un resultado de búsqueda. La
función que resuelve las etiquetas devuelve los casos con sus campos, no
listas de ids, y el script estaba comparando ids de fragmentos contra
nombres de campo. El síntoma quedó a la vista en el detalle, que en vez
de un id imprimía `pregunta, ids_relevantes`, que son los dos campos.

Un cero exacto en las dieciséis preguntas no es un hallazgo, es una
comparación mal armada.

**El segundo.** El primer conteo de fragmentos sin identificar dio 35 de
45. La comparación buscaba la palabra `articulo` sin tilde, y el artículo
66 es el único que escribe su rótulo como `Artículo 66.-`, así que lo
contaba como anónimo cuando no lo es. El número correcto es 34, y la
comparación ahora quita las tildes antes de comparar.

Las guardas que quedaron en `src/probar_linea_contexto.py`, y que se
revisan antes de calcular cualquier medida.

```
  1   las lineas son copia literal del articulo y sin corchetes
      que el parser de citas confundiria
  2   el caso resuelto en la posicion i es la misma pregunta que
      CASOS en la posicion i
  3   todos los ids etiquetados existen en el corpus
  4   las preguntas sin respuesta son dos, no cero
  5   lo indexado en disco es lo mismo que arma la corrida
  6   hay cruce entre lo recuperado y lo etiquetado
```

La **4** habría detenido la corrida mala. La **6** habría evitado que
imprimiera un número.

---

## 15. El formato del corpus no es uniforme

Hallazgo que no se estaba buscando.

```
  diez articulos    Art. 163.
                    (rotulo en su propia linea)

  el articulo 66    [1] Articulo 66.- En caso de muerte de un hijo
                    (rotulo pegado al texto con un guion)
```

Hoy no causa ningún problema medible. Importa para cuando el corpus
crezca, porque cualquier regla que dependa de encontrar el rótulo va a
tener que tolerar las dos formas. Las dos las cubre la `ETIQUETA` de
`src/indexar_corpus.py`, y conviene que siga siendo así.

---

## 16. Lo que queda pendiente

**De este bloque.**

1. La pregunta 11 sigue fallando, y falla de la manera peligrosa. La
   causa está identificada en la sección 11, la referencia cruzada entre
   artículos. Tres vías conocidas para atacarla, ninguna de este bloque.
```
     expandir la consulta    el modelo saca terminos legales
                             relacionados y se busca con cada uno

     buscar dos veces        se busca, se ve que salio el 161, y
                             como el 163 lo referencia, se vuelve
                             a buscar por los referenciados

     busqueda hibrida        juntar la semantica con la busqueda
                             por palabras clave del Bloque 21, que
                             devuelve articulos enteros en vez de
                             fragmentos
```

   La tercera se puede probar sin escribir código nuevo, porque la mitad
   ya existe en el repositorio.

2. Apretar la abstención, para que la #11 se abstenga en vez de contestar
   de otra cosa. Es la contención correcta para ese caso, y no arregla la
   búsqueda. Tiene un costo que habría que medir, porque una abstención
   más estricta puede empezar a abstenerse en preguntas que hoy contesta
   bien.
3. El empate de cuatro milésimas de la sección 6 no tiene tratamiento. El
   corte en k es duro y parte empates que no significan nada.
4. Volver a medir la línea de contexto cuando el corpus crezca, por la
   razón de la sección 13.
5. `escribir_resultados` guarda la tabla de k=4 y los promedios, pero no
   guarda la curva de k. La curva se imprime en pantalla y se pierde al
   cerrar la terminal. Por eso la tabla de la sección 4 llega hasta el 6,
   que es lo que quedó anotado. Conviene que el archivo de resultados
   guarde también la curva, ya que es lo que justifica el k elegido.
**Que vienen del Bloque 26 y siguen abiertos.**

6. Mover la nota de alcance del artículo 40 bis D al principio, donde
   todos sus fragmentos la lleven, en vez del final, donde el corte la
   deja afuera.
7. Revisar si otros artículos tienen la misma separación entre la regla y
   su condición.
8. Cerrar el hueco de contenido de `--verificar`.
9. Migrar el corpus de `src/soporte_corpus_legal.py` a archivos `.md`.
