# Límites y métricas, Bloque 24

Indexación del corpus con chunking, embeddings y persistencia en
Chroma. La medición del tamaño del fragmento está en
`src/medir_chunks.py` y se corrió el 10 de noviembre de 2026 sobre
el corpus de once artículos de `src/soporte_corpus_legal.py`.

Esa medición no llama a ningún modelo y no gasta tokens. El chunking
es una operación local sobre texto que ya está en memoria. Se pudo
repetir sin costo cada vez que cambió el corpus o la medición.

Las dos corridas del agente que se citan más abajo son del mismo
día, a las 21:57 y a las 21:58. Modelo el configurado en `AI_MODEL`,
sin cambios en el `.env` durante la serie.

---

## 1. El corpus que se indexa

Once artículos del Código del Trabajo, 20.480 caracteres, repartidos
en 66 incisos. Cada artículo entra como un documento propio, así que
un fragmento nunca cruza de un artículo a otro.

Los incisos están separados por un salto de línea simple y nunca por
uno doble. El `RecursiveCharacterTextSplitter` prueba sus
separadores en orden, `\n\n` primero y `\n` después. El doble no
encuentra nada en este corpus y el corte cae en el salto de línea
simple. Por eso la unidad de la medición es el inciso.

```
largos de los 66 incisos
  mínimo 26   p25 112   mediana 244   p75 457   máximo 1003
```

**Lo que la actividad pide del corpus.** Al menos cinco documentos
cortos, relacionados entre sí, y no párrafos genéricos sin relación.
Son once, así que el mínimo está cubierto. La relación entre ellos
es que se citan, y eso se midió, los once remiten a otros once del
Código que no están y además se remiten entre ellos.

Lo que no cumplen es lo de cortos. El 162 son 4.763 caracteres. La
lección contempla el caso y dice que si el corpus tiene documentos
más largos, el número de fragmentos va a ser mayor que el de
documentos y eso es normal. Once documentos dan 45 fragmentos.

---

## 2. La tabla con que se eligió el tamaño

La actividad no impone un `chunk_size` y pide elegirlo con criterio.
El `chunk_overlap` va fijo en el dieciocho por ciento del tope en
todas las filas, que es la proporción del ejemplo de la lección,
veinte sobre ciento diez, para que lo único que cambie entre filas
sea el tope.

```
  tope  chunks   corto  mediana   largo     limpios   mezclados
  ---------------------------------------------------------------
   200     138      36      193     200   59 de 138    7 de 138
   300      94      59      278     300   52 de 94    10 de 94
   400      75      68      322     399   51 de 75     9 de 75
   500      60      89      400     500   45 de 60    10 de 60
   700      45      68      489     700   40 de 45    13 de 45
  1000      30     186      829     996   29 de 30    18 de 30
```

`limpios` cuenta los fragmentos que empiezan donde empieza un
inciso. `mezclados` cuenta los que traen dos o más incisos adentro.

**El valor elegido es 700, con un overlap de 126.**

---

## 3. El problema de la columna de limpios

La fila de 1000 da 29 de 30, un 97 por ciento. Es el mejor número de
la columna y es el peor tope de los seis. Esa contradicción es el
problema de esta columna.

`limpios` mejora cuando el tope crece, pero no porque el corpus
quede mejor partido. Mejora porque hay menos fragmentos. Con 30
fragmentos hay 30 comienzos que pueden estar mal, y con 138 hay 138.
El tope grande tiene menos oportunidades de fallar.

El caso extremo lo muestra mejor. Un tope de 5000 metería cada
artículo completo en un fragmento, porque el más largo del corpus es
el 162 con 4.763 caracteres. Los once comienzos serían comienzos de
artículo y la columna marcaría 11 de 11. Cien por ciento, con el
corpus sin partir y sin haber hecho el ejercicio.

Entonces esta columna no alcanza para decidir. Leída sola manda a
elegir 1000, y lo que lo descarta está en la sección 7.

Conviene aclarar qué hace cada sección, porque no todas empujan para
el mismo lado. La 4 descarta los topes chicos. La 7 descarta el
1000. La 5 elige entre 500 y 700. Y la 6 no empuja, lo que hace es
medir cuánto de la objeción de mezcla es real.

Hay una segunda cosa que no ve. Mide dónde empieza el fragmento, no
si la norma llegó completa. Un fragmento que arranca cortado pero
que trae la regla entera por el overlap cuenta como no limpio igual.
La sección 8 tiene ese caso.

---

## 4. La segunda medición, cuántas reglas no caben

Un inciso más largo que el tope no tiene cómo caber en un fragmento
y se corta siempre. Eso es exacto y se cuenta sin correr el
splitter.

```
  tope   reglas que no caben
   200          40 de 66   61%
   300          29 de 66   44%
   400          19 de 66   29%
   500          13 de 66   20%
   700           5 de 66    8%
  1000           1 de 66    2%
```

Con 200, el 61 por ciento de las reglas del corpus se parte. Esa
fila queda descartada por este número y no por el de limpios.

Las cinco que no caben en 700 son las cinco más largas del corpus,
el artículo 40 bis D completo con 933 caracteres, el inciso 2 del
161 con 867, el inciso 4 del 162 con 824, el inciso 3 del 163 con
1003 y el inciso 1 del 172 con 779.

---

## 5. Por qué no 500, que es el competidor real

Entre 500 y 700 está el cruce. 700 corta cinco reglas y mezcla el 29
por ciento de los fragmentos. 500 corta trece y mezcla el 17 por
ciento. Ninguno gana en las dos columnas.

Lo que decide es cuáles son las ocho reglas que 500 corta de más.

```
  161 inciso 1   530   la causal de necesidades de la empresa
  162 inciso 1   606   la obligación de comunicar por escrito
  162 inciso 5   524   el estado de pago de las cotizaciones
  162 inciso 7   651   las remuneraciones por el período moroso
  163 inciso 2   523   los treinta días por año de servicio
  168 inciso 1   656   el plazo de sesenta días hábiles
  168 inciso 5   513   el plazo del inciso primero
  177 inciso 1   597   el plazo de diez días del finiquito
```

El inciso 2 del artículo 163 es la regla que esta aplicación existe
para responder. Es la que fija los treinta días de la última
remuneración por cada año de servicio y es la que la herramienta de
cálculo implementa. Con tope 500 se parte en dos.

Lo mismo pasa con el inciso 5 del 162, el de las cotizaciones
previsionales, que el modelo citó en las respuestas de este día, y
con los dos plazos, el de sesenta días hábiles del 168 y el de diez
días hábiles del 177.

**Por eso gana 700.** No porque tenga mejor `limpios`, sino porque
las ocho reglas que 500 corta de más son las que el proyecto
responde.

---

## 6. Qué juntan los trece fragmentos mezclados de 700

La columna `mezclados` cuenta por igual dos cosas que no son
equivalentes. Juntar dos reglas independientes degrada el embedding,
que queda a medio camino entre las dos. Juntar dos números de una
misma enumeración no, porque los números del 159 y del 160 son una
lista bajo un mismo encabezado y quien pregunta por las causales las
quiere juntas.

Se imprimieron los trece con los largos de lo que juntan, y la
clasificación sale de ahí.

```
  enumeraciones bajo un encabezado           6 de 13
    fragmento  6   159, el encabezado y los números 1 al 4
    fragmento  8   159, el último párrafo del 4 y los números 5 y 6
    fragmento  9   160, el encabezado, el número 1 y las letras a) a f)
    fragmento 10   160, las letras e) y f) y los números 2 y 3
    fragmento 11   160, los números 4 al 6 y las letras a) y b)
    fragmento 35   168, las letras a), b) y c) del recargo

  reglas independientes fusionadas           5 de 13
    fragmento  3   66, incisos 1 y 2
    fragmento  5   66, incisos 4 y 5
    fragmento 18   162, incisos 2 y 3
    fragmento 31   163, incisos 4 y 5
    fragmento 42   172, incisos 2 y 3

  discutibles                                2 de 13
    fragmento  7   159, dos párrafos que desarrollan el número 4
    fragmento 36   168, la letra c) y el inciso 2
```

**Cómo se clasificó, que no fue por el largo.** Los largos sirven
para identificar de qué inciso se trata, comparándolos contra el
inventario de los 66, y la clasificación sale de ver si los incisos
identificados pertenecen a la misma enumeración. Por largo solo no
se distinguirían, porque los dos grupos se solapan. El primero va de
26 a 393 caracteres y el segundo de 89 a 486.

**El costo real de mezcla con tope 700 está entre 5 y 7 fragmentos
sobre 45, un 11 a 16 por ciento, y no el 29 por ciento que muestra
la columna.** Lo que eso hace es quitarle a la columna el peso de
objeción decisiva contra el 700. La decisión la toma la sección 5.

**Lo que esto no mide.** El desglose se hizo solo para 700. Los diez
mezclados del 500 y los dieciocho del 1000 no se clasificaron, de
modo que sus porcentajes se leen como vienen. No se puede afirmar
que el 700 mezcle menos que el 500, solo que mezcla menos de lo que
su columna indica.

---

## 7. Por qué no 1000

Dieciocho de treinta fragmentos traen dos o más incisos, un 60 por
ciento, con mediana de 829 caracteres.

Las enumeraciones del 159 y del 160 son las que explican seis de los
trece mezclados del 700, y son finitas. A 1000 hay cinco fragmentos
mezclados más sobre quince fragmentos menos, de modo que lo que se
suma tiene que venir de incisos largos. Eso es deducción y no
medición, porque el desglose de esta fila no se corrió.

Y queda fuera de lo que la lección sugiere, que habla de unos pocos
cientos de caracteres con un overlap del quince al veinte por
ciento.

**Hasta dónde llega ese argumento.** La frase de la lección es
vaga. Setecientos está en el borde de arriba de unos pocos cientos y
mil está claramente afuera, pero nadie puede fijar el límite exacto
con esa redacción. Por eso este no es el argumento que descarta el
1000, es el que lo acompaña. El que decide es el 60 por ciento de
mezcla.

---

## 8. El overlap, dónde interviene y si alcanza

El overlap solo sirve cuando el partidor tiene que cortar algo por
la mitad. Donde un inciso cabe entero no hay nada que rescatar. En
este corpus eso pasa en cinco lugares, los cinco incisos que pasan
de 700 caracteres.

**El caso que se puede ver.** El artículo 40 bis D son 933
caracteres en un inciso único, sin ningún salto de línea adentro.
Con tope 700 el partidor no tiene separador natural donde cortar y
baja al espacio entre palabras.

```
fragmento 1, 700 caracteres, termina en
  "...si la indemnización que le correspondiere por aplicación
   del artículo 163 fuere superior, se le"

fragmento 2, 352 caracteres, empieza en
  "del contrato. Con todo, si la indemnización que le
   correspondiere por aplicación del artículo 163 fuere superior,
   se le aplicará ésta."
```

El fragmento 1 corta la regla en "se le". El fragmento 2 arranca 119
caracteres antes de ese corte y trae la oración completa.

Se pidieron 126 de overlap y vinieron 119. La diferencia está en que
el corte cae en un espacio entre palabras y no en el carácter
exacto. 126 es el máximo que se pide, no una cantidad garantizada.

El fragmento 2 cuenta como no limpio, porque empieza con "del
contrato" y no donde empieza un inciso. Es el caso de la sección 3.
La columna castiga un fragmento que entrega la norma entera.

**Si los 126 alcanzan en los cinco casos.** Para cada corte se buscó
en qué posición cae y qué largo tiene la oración que parte. Si esa
oración mide menos de 126 caracteres antes del corte, el overlap la
trae completa al fragmento siguiente.

```
  art 172 inciso 1     779 caract.   la oración mide  41   alcanza
  art 162 inciso 4     824           la oración mide 111   alcanza
  art 40 bis D         933           la oración mide 105   alcanza
  art 163 inciso 3   1.003           la oración mide  97   alcanza
  art 161 inciso 2     867           la oración mide 200   no alcanza
```

**El caso que no alcanza.** Es el inciso 2 del artículo 161, el del
desahucio. El corte cae en la posición 697 y la oración que se parte
empieza en la 497. El overlap rescata los últimos 126 caracteres y
deja afuera los primeros 74.

Lo que queda afuera es "Sin embargo, no se requerirá esta
anticipación cuando el empleador pagare al". Y el fragmento
siguiente arranca en "trabajador, al momento de la terminación, una
indemnización en dinero efectivo equivalente a la última
remuneración mensual devengada".

Se perdió la condición. Ese fragmento afirma un pago que en realidad
es la alternativa a dar los treinta días de aviso. Es el mismo
problema que resuelven las notas del corpus, producido por el corte
en vez de por el resumen.

**Lo que atenúa el caso.** El fragmento anterior tiene la oración
casi completa, le faltan las palabras del final. La regla no
desaparece del índice. Lo que queda degradado es el fragmento
siguiente, que es la mitad menor.

**Por qué no se subió el overlap.** Cubrir esa oración pide 200, que
sobre 700 es un 29 por ciento y queda fuera del rango del 15 al 20
que da la lección. Y el overlap no actúa solo en esos cinco cortes,
actúa en todos los límites entre fragmentos. El fragmento 9 trae las
letras a) a f) del artículo 160 y el fragmento 10 vuelve a traer la
e) y la f). Subirlo a 200 duplicaría más texto en todo el índice, y
cuánto más no se midió.

Queda en 126, con la falla anotada. Si el Bloque 27 muestra que ese
fragmento se recupera y confunde, el arreglo es una nota en el
corpus y no un overlap más grande.

---

## 9. El corpus creció entre la medición del Bloque 23 y esta

Esta medición se hizo sobre once artículos. La del Bloque 23, que
está en `docs/limites_autonomia_agente.md`, se hizo sobre nueve.

El 159 y el 172 entraron por una medición del propio corpus. El 159
era el artículo ausente más citado por los que ya estaban, con seis
menciones, dos en el 162, una en el 163 y tres en el 168, y ningún
otro ausente pasaba de una. El 172 trae el tope de noventa unidades
de fomento sobre la base de cálculo, que la herramienta de cálculo
nombra y que hasta entonces no estaba en el texto cargado.

El cambio al corpus quedó en un commit aparte del de esta actividad,
para que no se confunda qué tabla de fragmentos corresponde a qué
corpus.

**Lo que el cambio movió en los números.** Los incisos pasaron de 53
a 66 y la mediana de sus largos bajó de 302 a 244 caracteres. Con
todo, los porcentajes de la tabla casi no se movieron. Con nueve
artículos, 700 daba 39 fragmentos y 90 por ciento de limpios. Con
once da 45 y 89 por ciento. La elección aguantó el cambio de corpus,
que es lo que había que comprobar antes de fijarla.

---

## 10. La nota del artículo 162 resolvió la remisión, y se midió

Es un hallazgo del corpus y no del chunking, pero sale de las
corridas de este día y por eso queda en esta página.

El inciso 1 del artículo 162 remite a los números 4, 5 y 6 del 159
sin decir qué dicen. Mientras el 159 no estuvo cargado, la nota de
este proyecto avisaba que esos números no estaban en el corpus. En
una corrida del Bloque 23 el agente describió el número 6 como la
salida intempestiva del trabajador, que es el 160 número 4 letra a).
El 6 es el caso fortuito o fuerza mayor. Tomó una frase de un
artículo que tenía y la pegó a un número de uno que no.

Con el 159 cargado, la nota se cambió para que resuelva la remisión
y nombre las tres causales.

**El dato que lo confirma.** En la corrida de las 21:58, sesión
`consulta_004`, la búsqueda se llamó con "aviso de termino de
contrato anticipacion plazo articulo 162" y devolvió solo el
artículo 162. El 159 no salió. Con eso el modelo contestó que para
el vencimiento del plazo convenido, la conclusión del trabajo que
dio origen al contrato y el caso fortuito o fuerza mayor la ley no
exige anticipación, y que el plazo es de seis días hábiles para el
caso fortuito o fuerza mayor.

Esos tres nombres no estaban en nada más de lo que recibió. Salieron
de la nota.

---

## 11. Los dos artículos nuevos son alcanzables

La búsqueda es una función común y no llama al modelo, así que se
comprobó sin gastar tokens.

```
"se me vencio el contrato a plazo fijo"        devuelve el 159
"la base de calculo incluye el sobretiempo"    devuelve el 172
```

**Por qué hizo falta comprobarlo aparte.** En las dos corridas del
agente de este día, la búsqueda nunca devolvió ninguno de los dos.
El 172 aparece nombrado muchas veces en las respuestas, pero eso
sale del texto que devuelve la herramienta de cálculo y no del
corpus.

---

## 12. Lo que esta medición no prueba

El tamaño del fragmento se eligió por cómo queda partido el corpus,
no por cómo responde la búsqueda por significado. Esta medición no
dice nada sobre si una consulta recupera el fragmento correcto,
porque para eso hace falta calcular los embeddings y consultar el
índice.

La lección lo plantea igual, dice que el tamaño es un punto de
partida razonable y ajustable si la recuperación, que se mide en el
Bloque 27, sale mal.

Si ahí resulta que 700 recupera mal, el valor cambia en dos lugares
a la vez, en `src/indexar_corpus.py` y en la constante de muestra de
`src/medir_chunks.py`, y hay que volver a indexar, porque los
fragmentos guardados en el vector store son los del tope con que se
indexó.

---

## 13. Las advertencias de deprecación de las corridas del agente

Las dos corridas de este día imprimieron dos
`LangChainDeprecationWarning`, una por `RunnableWithMessageHistory` y
otra por `InMemoryChatMessageHistory`.

No interrumpen nada y van a la salida de error. Las dos clases son
las que prescribe la lección del Bloque 22, y cambiarlas por la
persistencia de LangGraph sería alejarse de lo que el curso pide. La
advertencia anuncia una versión futura, no un error de este código.
