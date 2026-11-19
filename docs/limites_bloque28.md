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

La actividad nombra dos archivos en su comando de entrega.

```
  registro_rag.py                  la instrumentacion
  registros_latencia_costo.jsonl   una linea por corrida
```

Y nombra un tercero en su texto, sin incluirlo en la entrega.

```
  leer_registros.py   para leer el historial del registro
```

### Las tres comprobaciones que pide la actividad

```
  1  tres preguntas distintas, tres lineas nuevas   cumple, son
                                                    cuatro con la
                                                    del k=6

  2  la misma pregunta con k=3 y k=6, y los tokens
     de entrada crecieron                           cumple, 811
                                                    a 1726

  3  la generacion es consistentemente la etapa
     mas lenta                                      en tres de
                                                    las cuatro
```

La tercera no se cumple del todo y conviene decirlo contra lo que la
lección espera. La actividad dice que la generación es mucho mayor
que el embed y la búsqueda *"todas las veces"*, y que eso es lo
esperable y no un error.

El ejemplo de la lección muestra el embed y la búsqueda en **17
milisegundos**. Con una llamada real de embeddings ese tiempo no se
alcanza. En este proyecto esa etapa ronda los **1200 milisegundos** y
es casi constante, mientras la generación depende de cuánto escribe
el modelo. Con un embed realista, una respuesta muy corta puede ser
más rápida que él.

Eso es lo que pasó en una de las cuatro corridas, la consulta que
responde más corto. No es un error de medición, es que el ejemplo de
la lección es ilustrativo y estos números son reales. El script
nombra cuál corrida fue y con cuántos tokens de salida, en vez de
suponer la causa.

### Qué más va en el repositorio, y qué no

Este bloque cambió además el tope de partición del Bloque 24 y la
plantilla del prompt del Bloque 26, con sus mediciones. De esas
mediciones va al repositorio la del tope, en `src/comparar_topes.py`,
porque el tope vive en un archivo que la actividad del Bloque 24
nombra en su entrega.

Las demás se hicieron con scripts de trabajo que **no van al
repositorio**. Sus tablas y sus números están completos en las
secciones de este documento, y volver a correrlos costaría más de
cincuenta generaciones.

```
  la fuga de la plantilla y sus cuatro variantes   seccion 8
  la validacion de la plantilla adoptada           seccion 8
  que articulos llegan con cada tope               seccion 11
  la regla suelta de la pregunta compuesta         seccion 18
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

Ese campo hizo su trabajo y además dejó al descubierto un error
propio, que está en la sección 16.

---

## 3. Las cuatro corridas

Con la configuración entregada, tope 1300 y solape 234.

```
    k   embed+busq   generacion      total   entrada  salida
  ---------------------------------------------------------
    3      1245.63      3019.87    4265.50       848     111
    3      1188.10      2592.85    3780.94       811     253
    3      1256.94      1127.45    2384.39      1047      48
    6      1096.72      2462.65    3559.37      1726     295
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
  k=3    811 tokens de entrada
  k=6   1726 tokens de entrada
         +915, unos 305 por cada fragmento extra
```

Con el tope de 700 cada fragmento extra costaba unos 140 tokens. Con
el de 1500 costaba 311 y con el de 1300 cuesta 305. Entre esos dos
últimos casi no se movió, aunque el fragmento promedio bajó de 1092 a
931 caracteres. El costo marginal depende de qué traen los fragmentos
que caen en las posiciones cuarta, quinta y sexta de esa consulta, y
eso no es el fragmento promedio.

El tiempo no acompaña, y de eso hay una prueba mejor que la anterior.

Entre la corrida de las 06:32 y la de las 06:36 pasaron cuatro
minutos, con la misma plantilla y las mismas preguntas.

```
  pregunta   salida   generacion   ms por token de salida

  acoso          10      8709.91                   871.0
  acoso          48      1127.45                    23.5

  fuero          60     14534.91                   242.2
  fuero         111      3019.87                    27.2
```

En la del fuero, la corrida posterior devolvió un ochenta y cinco por
ciento más de tokens y tardó cinco veces menos. Treinta y siete veces
de diferencia por token en la del acoso.

Lo que mueve el tiempo de generación es la API y no nada que este
proyecto controle. Es lo que dice la lección 13, y queda confirmado
con dos corridas separadas por cuatro minutos.

De ahí sale una advertencia para el documento mismo. Los tiempos de
la sección 3 sirven para ver el reparto entre etapas de esa corrida y
no sirven para comparar configuraciones. Lo que sí se puede comparar
son los tokens, que son deterministas dado el contexto.

---

## 5. La palanca del costo está en la salida, no en el prompt

Con las tarifas de ejemplo de la lección 13, que no son las reales de
Google y sirven para la proporción y no para el monto. La salida
cuesta cuatro veces más por token que la entrada, y de ahí sale todo
lo demás de esta sección.

```
  pregunta         k  entrada  salida      costo   % salida
  ---------------------------------------------------------
  fuero laboral    3      848     111   0.000129      34%
  indemnizacion    3      811     253   0.000182      56%
  acoso            3     1047      48   0.000124      15%
  indemnizacion    6     1726     295   0.000291      41%
  ---------------------------------------------------------
  las cuatro                            0.000726      39%
```

Mil consultas con `k=3` cuestan 0.1451 contra 0.1685 de la
configuración anterior.

### Una afirmación anterior que la medición da vuelta

La versión anterior de esta sección decía que en las preguntas que
responden de verdad la salida pesa el cincuenta y uno por ciento del
costo. Con la configuración de ahora pesa el treinta y nueve por
ciento sobre las cuatro corridas, y el cincuenta y seis solo en la
respuesta más larga. La entrada volvió a pesar más.

Lo que cambió es que las respuestas se acortaron. El enunciado que
sobrevive no es cuál de las dos pesa más, que depende de qué se
pregunta, sino que un token de salida cuesta cuatro veces uno de
entrada.

### Qué ahorró cada cosa, separado

Entre la configuración anterior y la entregada cambiaron dos cosas al
mismo tiempo, la plantilla del prompt y el tope. Hubo una corrida
intermedia, con el tope viejo y la plantilla nueva, que permite
separarlas. Esa corrida está explicada en la sección 16 porque quedó
guardada con una etiqueta equivocada, pero como medición sirve.

```
  estado                        entrada  salida      costo
  --------------------------------------------------------
  A  tope 1500, plantilla vieja    4748     968   0.000862
  B  tope 1500, plantilla nueva    4872     670   0.000755
  C  tope 1300, plantilla nueva    4432     707   0.000726
```

```
  A a B, solo la plantilla    0.876x
  B a C, solo el tope         0.961x
  A a C, las dos              0.842x
```

**La plantilla ahorró tres veces más que el tope.** El tope achica el
prompt, que es la parte barata. La plantilla acortó las respuestas
largas entre un veintidós y un cuarenta y cinco por ciento, y esa es
la parte que cuesta cuatro veces más.

Sobre los tokens de entrada el tope sí es el que manda. Las tres
corridas con `k=3` bajan de 1002 a 902 tokens promedio, que es
**0.90x**, mientras el costo total baja a 0.961x. Las dos cifras son
verdaderas y miden cosas distintas, el tope baja la entrada un diez
por ciento y el costo total un cuatro.

Esos 0.90x no se comparan con los factores que proyectó
`comparar_topes.py`. Esa grilla midió los topes 1100, 1250 y 1500 en
0.87x, 0.91x y 1.00x, estimando la entrada a partir de los caracteres
del prompt sobre las catorce preguntas que el corpus responde. Estos
son tokens reales sobre tres. Las dos mediciones van en la misma
dirección y no son el mismo número, y el 0.91x de esa grilla es del
tope 1250 y no del 1300.

La entrada se descompone exacta, porque es determinista.

```
  pregunta         k       A       B       C   plantilla   tope
  -------------------------------------------------------------
  fuero            3     882     913     848         +31    -65
  indemnizacion    3     902     933     811         +31   -122
  acoso            3    1130    1161    1047         +31   -114
  indemnizacion    6    1834    1865    1726         +31   -139
```

Los mismos treinta y un tokens en las cuatro. Es el largo de la
plantilla nueva, que tiene sus tres salidas enumeradas y es más larga
que la anterior.

En la salida la separación no es tan limpia. La plantilla acortó las
tres respuestas largas, de 416 a 324, de 433 a 276 y de 109 a 60. El
efecto del tope sobre la salida cambia de signo según la pregunta, así
que no se distingue de la variación propia del modelo, salvo en un
caso, que es el de la sección 14.

### La consecuencia práctica del bloque

> Mirar solo cuánto creció el prompt engaña. Lo que más mueve el costo
> de este flujo es cuánto escribe el modelo, y eso se controla desde
> el prompt y no desde el tamaño del fragmento.

### La proyección aguantó

Antes de medir se proyectó el costo de la configuración de tope 1500
a partir de la relación de caracteres por token de la configuración de
tope 700.

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

Los diez tokens se siguieron usando como señal después. La consulta
del acoso quedó en la lista de `probar_generacion.py` por haber dado
ese número, y la sección 14 cuenta en qué terminó.

**Dónde está esa evidencia.** Esas cinco líneas no están en el
`registros_latencia_costo.jsonl` de hoy, que tiene ocho, cuatro del
tope 1500 y cuatro del 1300. Son de una corrida con el tope de 700 que
se limpió al rehacer el archivo, y la que la pisó está contada en la
sección 16. Esta tabla es el único registro de ese hallazgo, y se deja
dicho para que nadie la busque en el archivo.

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

## 8. La plantilla de tres salidas, y por qué van enumeradas

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

### La tercera salida se filtraba a la respuesta

La primera redacción de esa plantilla explicaba las tres salidas en
prosa, un párrafo cada una. Al repetir la verificación tres veces, que
es la disciplina que viene del Bloque 26, apareció un fallo que una
sola corrida no habría mostrado.

Ante una consulta fuera del corpus, el modelo devolvía la tercera
instrucción convertida en afirmación, y después la frase.

```
  lo esperado    63 caracteres, la frase de abstencion sola
  lo devuelto   164 caracteres, la instruccion y despues la frase
```

El chequeo que había no lo atrapaba, porque preguntaba si la frase
estaba en la respuesta y la frase estaba. Lo que sobraba era lo de
antes.

### El diagnóstico equivocado, y lo que sí funcionó

La primera explicación fue que el problema era la redacción, que la
frase copiable y la referencia hacia adelante invitaban al modelo a
repetir la instrucción. Se escribió una variante contra esa
explicación y **se filtró igual**, repitiendo la redacción nueva.

Se aislaron las tres instrucciones con el mismo contexto en seis
llamadas, y la del medio resultó ser el disparador. Después se
probaron cinco variantes sobre ese contexto idéntico.

```
  variante                                  se filtro
  -----------------------------------------------------
  A  la redaccion corregida                 si
  B  otra redaccion                         si
  C  instrucciones despues del contexto     no
  D  las tres salidas enumeradas            no
```

**La causa era la estructura y no las palabras.** Enumerar las tres
salidas como 1, 2 y 3 cierra cada una en su número, y la del medio
deja de poder arrastrar a la tercera.

Se adoptó la D, que es la que menos cambia el orden del prompt. Se
validó con trece generaciones repartidas en cuatro casos, con
distinta cantidad de corridas según lo que cada uno tenía que
demostrar.

```
  caso                                corridas   resultado
  ---------------------------------------------------------
  el acoso, donde aparecia la fuga        6       0 fugas
  la compuesta, responde                  3       3 de 3
  vacaciones, abstencion limpia           2       2 de 2
  la del Bloque 26, responde              2       2 de 2
```

El acoso lleva seis y no tres porque es el caso donde la fuga
aparecía, y seis más las tres de la comparación de variantes dan
**nueve corridas sin una sola fuga**. Contra una tasa de fuga cercana a la
mitad, nueve llamadas limpias dan una probabilidad de coincidencia de
alrededor de uno en quinientos.

Los otros tres son controles y llevan las corridas que alcanzan para
ver si algo se rompió, no las que harían falta para medir una tasa.

La frase de abstención quedó sin comillas a propósito. Con comillas el
modelo las copiaba, y la respuesta salía entrecomillada.

Esa validación se hizo contra el índice de diecinueve fragmentos, así
que al adoptar el tope de 1300 se repitió contra el de veintidós. El
control de fuera del corpus devolvió los 63 caracteres exactos, con
cero fuentes citadas, y está en la sección 13.

### Para qué sirve la salida del medio

La respuesta a la pregunta con premisa lo muestra.

> *El contrato de trabajo termina sin derecho a indemnización cuando
> el empleador le ponga término invocando conductas de acoso laboral,
> siempre y cuando estas se encuentren debidamente comprobadas [1].
> **La parte del contexto que no se puede responder es** si pueden
> despedirte específicamente si no tienes pruebas de dicho
> hostigamiento, ya que el texto solo menciona que las conductas
> deben estar "debidamente comprobadas" [1], pero no especifica qué
> sucede si faltan dichas pruebas.*

Responde lo que está y nombra lo que falta. Para una consulta laboral
eso es mejor que las dos salidas anteriores, porque callarse entero
deja a la persona sin nada que sí estaba en la ley, y media respuesta
sin avisar la deja creyendo que tiene todo.

Esa respuesta tiene una historia larga, porque una versión anterior
de ella contenía un error. Está en la sección 14.

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

Los trece, uno por uno, con el comienzo de cada fragmento.

```
  articulo    frag   car   empieza en
  -----------------------------------------------------------------------------
  40 bis D       1   352   'del contrato. Con todo, si la indemnización que le'
  159            1   489   'El trabajador que hubiere prestado servicios disco'
  159            2   341   'El hecho de continuar el trabajador prestando serv'
  160            1   664   'e) Conducta inmoral del trabajador que afecte a la'
  161            2   293   'trabajador, al momento de la terminación, una inde'
  162            3   252   'siguiente. Igual indicación deberá contener la com'
  163            3   425   '13 de la ley N° 19.728. Sólo corresponderá el pago'
  163            5   336   'a) Tendrán derecho, cualquiera que sea la causa qu'
  163            6   387   'b) La obligación de efectuar el aporte tendrá una '
  168            1   400   'a) En un treinta por ciento, si se hubiere dado té'
  168            2   436   'c) En un ochenta por ciento, si se hubiere dado té'
  172            1   203   'o por una sola vez al año, tales como gratificacio'
  177            1   231   '[nota: el artículo continúa con doce incisos más, '
```

De esos trece, cuatro traen una regla sin la condición que la limita.

```
  163 frag 6   "b) La obligacion del aporte..."   casa particular
  163 frag 3   "la prestacion antes señalada"     obra o faena
  161 frag 2   "Regira tambien esta norma"        gerentes y casa
                                                  particular
  168 frag 1   "a) En un treinta por ciento"      recargo judicial
```

Dos filas de esa lista valen la pena aparte, porque son las dos que
el bloque siguió hasta el final.

La del artículo 163, fragmento 6, empieza en la letra b). Esa letra
es la obligación del aporte del empleador, y su condición, que rige
solo para los trabajadores de casa particular, vive en el encabezado
del inciso 5. La regla llegaba sola. Es la segunda de las dos reglas
que vigila `probar_generacion.py`.

La del artículo 172, fragmento 1, son los 203 caracteres que quedaron
del inciso 1 partido, y empiezan a mitad de la lista de exclusiones
de la última remuneración. Ese inciso completo mide 779 caracteres, y
con el tope en 700 no entraba.

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
  tope  700, sin separar incisos           45       13
  tope  700, separando incisos             46        9
  tope 1000, separando incisos             32        2
  tope 1056, separando incisos             31        1
  tope 1057, separando incisos             30        0
  tope 1100, separando incisos             30        0
  tope 1300, separando incisos             22        0   el de hoy
  tope 1500, separando incisos             19        0
  tope 2000, separando incisos             16        0
```

Separar los incisos sin subir el tope baja los fragmentos a media
unidad de trece a nueve y no los elimina, porque con el tope en 700
hay nueve unidades que no caben enteras y se parten igual. Las dos
partes del arreglo hacen falta.

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

### Los fragmentos tienen menos caracteres que el corpus

La verificación del índice imprime los dos números y la resta puede
inquietar, porque los fragmentos tienen menos.

```
  caracteres en los fragmentos  20496
  caracteres en el corpus       20518
  diferencia                    22, uno por fragmento
```

Son los saltos de línea que el splitter recorta en los bordes de cada
fragmento. El texto legal no pierde nada, y eso se comprobó
comparando el contenido sin espacios de los dos lados.

```
  corpus sin espacios       17128 caracteres
  fragmentos sin espacios   17128 caracteres
  identicos caracter por caracter
```

---

## 11. Por qué el tope es 1300 y el solape 234

Este número no se eligió mirando qué preguntas fallaban. Esa objeción
ya había descartado subir el tope a 1000 en el Bloque 27, y vale
igual para esta decisión.

El criterio estructural da un piso y no un valor. Por encima del piso
ninguna unidad se parte por dentro, y lo único que el tope decide es
cuántas unidades enteras se empaquetan en un mismo fragmento. Hacen
falta dos pasos, uno para el piso y otro para el valor.

### Dónde está el piso, medido

```
  unidades estructurales del corpus   49
  la mas larga                        1057 caracteres, art. 168

  cuantas caben enteras
      tope  700    40 de 49    82%
      tope 1000    47 de 49    96%
      tope 1056    48 de 49    98%
      tope 1057    49 de 49   100%
      tope 1100    49 de 49   100%
      tope 1300    49 de 49   100%
      tope 1500    49 de 49   100%
      tope 2000    49 de 49   100%
```

El piso es **1057**, que es el largo de la unidad más larga y no ese
largo más uno. En 1056 se parte una unidad y en 1057 ninguna. El
splitter deja una pieza entera cuando mide menos que el tope, y
cuando no, baja al separador siguiente, donde una unidad sin cortes
internos aprovechables vuelve a salir completa.

Las dos filas del 1056 y el 1057 están en la grilla de
`src/medir_incisos.py` por eso, para que el piso se vea medido y no
afirmado.

### Por qué son 49 unidades y en el Bloque 24 eran 66 incisos

Las dos cuentas son correctas y cuentan cosas distintas. Conviene
dejarlo escrito, porque la sección 1 del `docs/limites_bloque24.md`
dice sesenta y seis incisos con un máximo de 1003 caracteres y esta
dice cuarenta y nueve unidades con un máximo de 1057.

```
  separando por salto de linea simple    66 piezas, maximo 1003
  separando por linea en blanco          49 unidades, maximo 1057
```

El Bloque 24 contó toda línea separada por un salto simple, y eso
cuenta aparte las letras a), b) y c) que viven adentro de un inciso.
El Bloque 28 cuenta la unidad estructural, de modo que esas letras van
con el inciso al que pertenecen.

Por eso cambia cuál es el máximo y de qué artículo es.

```
  la linea mas larga      1003   art. 163 inciso 3, una sola
                                 linea, sin letras adentro

  la unidad mas larga     1057   art. 168 inciso 1, que son
                                 cuatro lineas, el encabezado de
                                 656 y las letras a), b) y c) de
                                 101, 184 y 113
```

Ninguna de esas cuatro líneas del artículo 168 llegaba a 1003, así que
con el conteo del Bloque 24 ese inciso no aparecía como el más largo
del corpus. Con el conteo de ahora sí, y es el que fija el piso.

Y la unidad es lo que hay que medir, no la línea. La letra a) del
recargo del treinta por ciento mide 101 caracteres y su condición vive
en el encabezado de 656. Suelta no dice de qué habla, y es justamente
uno de los trece fragmentos de la sección 9.

### Las dos razones del piso, las dos medidas

**La primera es de estructura.** Una unidad partida por dentro puede
entregar una regla sin la condición que la limita, que es lo que
produjo las dos respuestas legalmente equivocadas de la sección 5 del
`docs/limites_bloque26.md` y lo que muestra la lista de la sección 9.

**La segunda es de recuperación.** Una unidad partida se recupera peor
que la unidad entera, porque el embedding representa lo que hay en ese
pedazo. El inciso 1 del artículo 172 mide 779 caracteres, con tope 700
se parte y no alcanza el top 3 de la consulta del cálculo. Con
cualquier tope por encima del piso cabe entero y sí lo alcanza.

### Cómo cambia la partición por encima del piso

No cambia de a un carácter. Se barrió el tope de uno en uno, desde el
piso hasta 1600.

```
  rango del tope   fragmentos
  ---------------------------
  1057 a 1069          30
  1070 a 1070          29
  1071 a 1153          30
  1154 a 1171          29
  1172 a 1220          27
  1221 a 1221          26
  1222 a 1228          25
  1229 a 1273          24
  1274 a 1292          23
  1293 a 1351          22
  1352 a 1436          21
  1437 a 1446          20
  1447 a 1600          19
```

El conteo no es estrictamente decreciente. En 1070 baja a veintinueve
y en 1071 vuelve a treinta. No se persiguió esa anomalía porque está
muy por debajo del valor adoptado, pero queda escrita para no dar a
entender que la curva es limpia.

### La condición que elige el valor

De los tramos de arriba se eligió midiendo cuatro cosas.

```
  el recall es plano arriba del piso, 0.857 en 1100, 1250 y
  1500, y fallan las mismas tres preguntas

  el costo de la entrada baja cuando baja el tope, 0.87x,
  0.91x y 1.00x

  el primer fragmento es relevante en doce preguntas de
  dieciseis con 1300 y en diez con 1500

  el tope de noventa unidades de fomento del articulo 172
  solo viaja junto a la base de calculo desde 1293
```

La última es la que decide, y la primera tabla la explica entera.

El artículo 172 con sus incisos separados mide **1293 caracteres**. Su
tope de noventa unidades de fomento vive en el tercer inciso y su base
de cálculo en el primero. Por debajo de 1293 el artículo no cabe
entero, el tercer inciso queda en otro fragmento, y la consulta del
cálculo recupera la base sin el tope. Es un límite legal real sobre lo
que se paga.

Y 1293 es exactamente donde el tramo de veintidós fragmentos empieza.
El conteo baja a veintidós **porque** ese artículo pasa a caber en un
fragmento. La frontera del tramo y el largo del artículo son el mismo
número.

### Por qué 1300 y no 1293, ni 1310

Porque dan el mismo índice. Se comparó fragmento por fragmento.

```
  desde 1293 hasta 1345 la particion es identica, no solo en
  cantidad sino en contenido, 53 valores de tope que producen
  exactamente los mismos 22 fragmentos
```

Dentro de esa banda el tope no decide nada. Lo que se midió es la
banda, y 1300 es un número redondo adentro. Elegir 1294 o 1330 habría
dado el mismo sistema, el mismo costo y las mismas respuestas.

Eso es lo que hay que contestar si alguien pregunta por qué no 1294.
No es que 1300 sea mejor, es que es el mismo.

El solape sale de la banda también. El dieciocho por ciento de 1300 da
234, y es la misma proporción que usaba la configuración anterior.

### El solape no hace nada con este tope

Se midió, fragmento contra fragmento consecutivo.

```
  tope   solape   caracteres repetidos   pares con solape
  --------------------------------------------------------
   700      126                    605                  5
  1000      180                    531                  4
  1080      194                    646                  4
  1230      221                    169                  1
  1300      234                      0                  0
  1500      270                    248                  1
```

Con el tope entregado el solape repite **cero** caracteres. Ningún par
de fragmentos consecutivos comparte texto.

El splitter arrastra solape solo si lo que queda al cerrar un
fragmento cabe en los 234 caracteres del presupuesto, y en este tope
la unidad del borde siempre es más larga que eso.

No es un defecto, es una consecuencia del piso. El solape existe para
que un concepto cortado sobreviva en los dos pedazos, y por encima del
piso no se corta nada. Queda definido por la proporción del Bloque 24
para que lo fije la misma regla, y vuelve a servir solo si alguna
unidad llegara a superar el tope.

La versión anterior de esta sección decía que el solape repetía entre
el uno y el tres por ciento del corpus. Eso era cierto en otros topes
y falso en el nuestro. Queda anotado en la sección 16.

### Esto queda fuera de lo que la lección sugiere

La lección del Bloque 24 habla de unos pocos cientos de caracteres con
un solape del quince al veinte por ciento, y la actividad no impone un
`chunk_size` y pide elegirlo con criterio. La sección 7 del
`docs/limites_bloque24.md` usó esa sugerencia como argumento para
descartar el tope de 1000.

Este corpus no permite quedarse en ese rango. Su unidad legal más
larga mide 1057 caracteres y partirla por dentro produce los errores
de la sección 9. De los tramos por encima del piso se toma el que
cumple las cuatro condiciones, que es la menor desviación posible que
sirve.

El solape sí queda dentro de lo sugerido, en el dieciocho por ciento.

### Qué hacer cuando el corpus cambie

Este procedimiento es propio. Ni la plataforma ni los trabajos citados
en la sección 17 lo prescriben, y existe porque esta implementación
hace que el tope decida la integridad de la unidad.

Agregar o editar un artículo puede alargar la unidad más larga, así
que hay que volver a correr `src/medir_incisos.py` y subir el tope si
el piso se movió. Puede además alargar un artículo completo, y si ese
artículo tiene una condición y un límite en incisos distintos, hay que
revisar que siga cabiendo entero, que es la cuenta del artículo 172.

Sacar un artículo no puede romper el piso, pero puede dejar el tope
más alto de lo necesario, y eso cuesta sin dar nada.

Cortando por estructura de forma explícita, como hacen los trabajos de
la sección 17, el tope dejaría de decidir esto. Eso está anotado como
pendiente.

### Por qué se buscaron referencias

La opción de cortar por la unidad legal se planteó al ver los trece
fragmentos de la sección 9, pero no había seguridad de que fuera el
camino correcto. Los intentos anteriores habían fallado, el tope y el
solape en el Bloque 24, el k y la línea de contexto en el Bloque 27,
los cuatro medidos y los cuatro descartados, y nada garantizaba que
este no fuera otro ajuste más. Antes de reescribir el indexador se
buscó si alguien había resuelto este mismo problema en proyectos de
este tipo, sobre textos legales.

Lo que apareció confirmó que el camino era el que se usa en ese
dominio, y precisó su forma, cortar primero por el límite legal y
partir de manera recursiva solo adentro de la unidad. Los números
siguieron saliendo de medir este corpus.

**Lo que la literatura respalda es el procedimiento y no el número.**
El 1293 sale de medir el artículo 172 de este corpus y de ninguna otra
parte. Las citas, con su ubicación en el original y traducidas del
inglés, están en la sección 17.

---

## 12. La curva de k y por qué k vale 3

Medida con la evaluación del Bloque 27 contra la partición de 1300.

```
    k  precision   recall      F1
  --------------------------------
    1      0.750    0.786   0.767
    2      0.375    0.786   0.508
    3      0.271    0.857   0.412   <-- el elegido
    4      0.219    0.893   0.351
    5      0.175    0.893   0.293
    6      0.146    0.893   0.251
    7      0.125    0.893   0.219
    8      0.117    0.929   0.208
```

Contra la configuración de tope 700.

```
                      precision   recall      F1
  ------------------------------------------------
  antes, 700, k=4         0.203    0.821   0.326
  ahora, 1300, k=3        0.271    0.857   0.412
                         +0.068   +0.036  +0.086
```

**Mejora en las tres a la vez.** No es un intercambio.

### Qué se movió al bajar el tope de 1500 a 1300

```
    k   precision 1500   precision 1300   recall 1500   recall 1300
  ------------------------------------------------------------------
    1            0.625            0.750         0.643         0.786
    2            0.344            0.375         0.714         0.786
    3            0.271            0.271         0.857         0.857
  4 a 7         iguales          iguales       iguales       iguales
    8            0.125            0.117         0.964         0.929
```

Del tres al siete no se movió nada. Lo que se movió es el `k=1`, y
hacia arriba.

Esa fila confirma una de las cuatro condiciones de la sección 11 desde
otra medición. La condición decía que el primer fragmento es relevante
en doce preguntas de dieciséis con 1300 y en diez con 1500. La
precisión con `k=1` vale 0.750 sobre dieciséis preguntas, que son doce,
y 0.625 son diez.

### Por qué no se baja al 1

El F1 tiene su máximo en `k=1` y ahora vale 0.767 en vez de 0.634. La
distancia de recall contra el `k=3` se angostó de 0.214 a 0.071, que
sobre catorce preguntas con respuesta es una pregunta. Antes eran tres.

**El recall promedio ya no alcanza para defender la decisión**, y
conviene decirlo en vez de repetir el argumento viejo con números
nuevos.

Lo que la defiende es el mismo límite legal que fijó el tope. En la
consulta del cálculo los tres fragmentos llegan en este orden.

```
  posicion   articulo
  -------------------
    [1]      163
    [2]      40 bis D
    [3]      172
```

Los números de posición los asigna el armado del contexto en orden de
recuperación, y un fragmento nunca mezcla dos artículos, porque cada
artículo entra al splitter como un documento aparte. El tope de
noventa unidades de fomento vive en el artículo 172, que llega
tercero, así que con `k=1` o con `k=2` no llega.

**El 3 es el mínimo que lo trae.** Se ve en la corrida de
`src/probar_generacion.py`, donde la respuesta cita ese límite con la
fuente `[3]`.

El tope y el k quedan entonces fijados por la misma condición. El tope
de 1300 para que el artículo 172 quepa entero en un fragmento, y el k
de 3 para que ese fragmento llegue.

### Por qué no se sube al 4

```
  recall sube     +0.036, media pregunta de catorce
  precision baja  -0.052
  entrada sube    +305 tokens, un 38% sobre la pregunta del medio
  costo sube      +17%
```

El recargo de costo sale de los tokens medidos al tope 1300. Cada
fragmento extra agrega unos 305 tokens de entrada, y con la salida
igual eso da un diecisiete por ciento más por consulta. La versión
anterior de esta sección decía catorce, que no se reproduce con
ninguna de las dos mediciones. La proyección de más abajo da trece
para ese mismo salto al tope 1500, y los tokens medidos al 1300 dan
diecisiete.

Esa media pregunta era la **#15**, la del finiquito indefinido o plazo
fijo, que es la que falla de la manera contenida, abstieniéndose en
vez de contestar otra cosa.

**Eso último no está reverificado al tope 1300.** Se midió con el tope
de 700. Con la partición de ahora las dos preguntas que quedan en
recall 0.50 son la #10 y la #15, y de la curva no se puede saber cuál
de las dos es la que gana al pasar a `k=4`. La cuenta del costo vale
igual, porque media pregunta de catorce es media pregunta
independientemente de cuál sea, pero el argumento de que es la que
falla a salvo pide saber cuál es.

Es la misma cuenta de la sección 5 del `limites_bloque27.md`, donde
subir el k arreglaba solo esa pregunta y por eso no se subió. La regla
tiene dos partes y conviene dejarla escrita entera.

> El recall pesa más que la precisión, porque un fragmento que no
> llega no lo compensa ningún prompt. Pero no se paga un recall que
> solo alcanza preguntas que ya fallaban abstieniéndose.

### Un error que arrastraba desde el Bloque 27

La salida de `evaluacion_recuperacion.py` imprimía solo la primera
parte de esa regla, y decía quedarse con el k del recall mientras el k
elegido era otro. En la corrida del Bloque 27 decía *"el recall deja
de subir en k=6"* con el k en 4, y no se lo notó. Quedó corregido y
ahora imprime las tres lecturas, la del recall, la del F1 y la del k
del proyecto.

### El costo de subir el tope

```
  config            k  entrada  salida       costo   vs antes
  ------------------------------------------------------------
  antes, 700        4      522     260    0.000156    1.00x
  1500 doble        2      587     260    0.000163    1.04x
  1500 doble        3      830     260    0.000187    1.20x
  1500 doble        4     1073     260    0.000211    1.35x
```

Esa tabla es la proyección que se hizo al subir de 700 a 1500. Con el
tope en 1300 la entrada del `k=3` medida es de 902 tokens promedio en
vez de los 971 del 1500, de modo que el recargo contra el tope de 700
queda por debajo del veinte por ciento proyectado.

Lo que compra ese recargo es que ninguna regla llegue al modelo
separada de la condición que la limita.

---

## 13. Lo que la generación ganó

Verificado contra producción con `src/probar_generacion.py`, cinco
casos y cinco generaciones.

```
  caso                        resultado
  -------------------------------------------------------------
  la del calculo              responde, 1846 car, cita 163, 172
                              y 40 bis D, regla con su condicion
  la del acoso                responde, 483 car, cita 160
  control fuera del corpus    se abstiene, 63 car, 0 fuentes
  la #11                      responde, 1021 car, cita 161 y 168
  la compuesta                responde, 792 car, cita 163 y
                              40 bis D, regla SIN su condicion

  casos que se comportaron como se esperaba   5 de 5
  reglas nombradas sin su condicion           1
```

### El tope de 90 unidades de fomento llegó a la respuesta

Esta línea de la consulta del cálculo es la decisión del tope,
completa.

> *Además, la base de cálculo no considerará una remuneración mensual
> superior a 90 unidades de fomento del último día del mes anterior al
> pago* **[3]**.

Es el tercer inciso del artículo 172. Con la partición anterior ese
artículo no llegaba a esa consulta, y con un tope por debajo de 1293
llegaría sin ese inciso. Ya no se trata de que el fragmento llegue, se
trata de que el límite esté en la respuesta que lee la persona.

Con él llegan también las remuneraciones variables y qué se excluye de
la base de cálculo.

### El error del artículo 40 bis D, en esa consulta, está arreglado

> *Para los contratos de jornada no superior a treinta horas
> semanales (jornada parcial), para el cálculo de la indemnización se
> entenderá por última remuneración el promedio de las remuneraciones
> percibidas... durante la vigencia de su contrato o de los últimos
> once años* **[2]**.

Nombra la condición y la pone al principio de la frase. En la pregunta
compuesta eso no pasa, y está en la sección 18 como pendiente.

### La pregunta 11 dejó de ser peligrosa

```
  antes
      hablo del juicio en sesenta dias habiles y del recargo del
      treinta por ciento, y se callo lo que la persona preguntaba.
      Fluida, citada y silenciosamente incompleta

  ahora
      "...el contexto no detalla cuales son los montos base exactos
      ni la forma de calculo de las indemnizaciones de los articulos
      162 y 163, ni menciona otras prestaciones basicas asociadas al
      despido por necesidades de la empresa"
```

**La recuperación de la #11 sigue fallando igual, recall 0.00.** Pero
el modelo ya no lo esconde. El fallo peligroso, el que contesta otra
cosa sin avisar, dejó de estar. Queda un fallo honesto.

Y esa pregunta deja una lectura sobre las métricas. Tiene recall 0.00,
de modo que el fragmento etiquetado no llegó, y la respuesta es
legalmente correcta y acotada, construida con los artículos 161 y 168
y diciendo qué no cubre el contexto. El cero habla de la etiqueta y no
de la respuesta.

---

## 14. La abstención del acoso, y qué la resolvió

Esta sección cuenta tres estados de la misma consulta, porque la
historia completa es el hallazgo.

> tengo un conflicto con una compañera que me hostiga y no tengo
> pruebas, ¿pueden despedirme por eso?

La evaluación le mide recall 1.00, de modo que el fragmento etiquetado
llega en los tres estados.

### Con el tope de 700 respondía, y la respuesta tenía un error

```
  la respuesta de entonces decia
      "el contexto no menciona si se requiere la existencia de
       pruebas para proceder con dicho despido"

  el articulo 160 en el contexto dice
      "1.- Alguna de las conductas indebidas de caracter grave,
       debidamente comprobadas... f) Conductas de acoso laboral"
```

El contexto sí lo menciona. *"Debidamente comprobadas"* es exactamente
el requisito de prueba. La respuesta afirmaba que la ley no decía algo
que la ley sí dice.

### Con el tope de 1500 se abstenía, de manera estable

Tres corridas de tres, diez tokens de salida. Se escribió entonces que
callarse era mejor que decirle a alguien que la ley no exige pruebas
cuando sí las exige, y se dejó anotado como pendiente que una
respuesta parcial correcta sería mejor que las dos.

El mecanismo que se propuso para esa abstención fue el ruido por
fragmento.

```
  tope  700, k=4   contexto de 2461 caracteres, 4 fragmentos
  tope 1500, k=3   contexto de 4071 caracteres, 3 fragmentos
```

Sesenta y cinco por ciento más texto, y **dos de los tres fragmentos
eran del artículo 168**, que habla del juicio y de los recargos y no
tiene nada que ver con esa pregunta. Fragmentos más grandes traen más
texto irrelevante por fragmento, y con más ruido el modelo decidía no
contestar.

### Con el tope de 1300 responde, y responde bien

> *El contrato de trabajo termina sin derecho a indemnización cuando
> el empleador le ponga término invocando conductas de acoso laboral,
> siempre y cuando estas se encuentren **debidamente comprobadas**
> [1]. La parte del contexto que no se puede responder es si pueden
> despedirte específicamente si no tienes pruebas de dicho
> hostigamiento, ya que el texto solo menciona que las conductas deben
> estar "debidamente comprobadas" [1], pero no especifica qué sucede
> si faltan dichas pruebas.*

Nombra el requisito de prueba en vez de negarlo, y acota el hueco real,
que es qué pasa cuando las pruebas faltan. Eso es legalmente correcto y
es exactamente la respuesta parcial que el pendiente pedía.

### Lo que la hizo volver fue el tope y no la plantilla

Esto se puede separar porque hay una corrida intermedia con el tope
viejo y la plantilla nueva.

```
  estado                        tokens de salida del acoso
  --------------------------------------------------------
  A  tope 1500, plantilla vieja                        10
  B  tope 1500, plantilla nueva                        10
  C  tope 1300, plantilla nueva                        48
```

Con la plantilla enumerada y el índice de diecinueve fragmentos seguía
absteniéndose. Lo que la hizo responder fue bajar el tope.

Y eso es el mecanismo del ruido por fragmento, cumpliéndose. Entre B y
C la plantilla es la misma, así que la entrada se puede comparar
directo. Bajó de **1161 a 1047 tokens**, de modo que el contexto de
esa consulta se achicó en 114 tokens.

```
  el mecanismo se escribio   antes de medir esto
  la medicion                es consistente con el
  el alcance                 una pregunta, una corrida por estado
```

Es una confirmación y no una prueba. Una pregunta no es muestra, y eso
mismo lo advierte la lección 13 sobre el costo.

Lo que sí queda establecido es que el costo de la partición grande,
que esta sección documentaba como pérdida, era reversible bajando el
tope, y que bajarlo no costó ninguna de las cosas que la partición
grande había ganado. La sección 13 las lista y están todas.

---

## 15. La reindexación no borraba

Al reindexar con la configuración nueva, la verificación del Bloque 24
avisó.

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
antigua. Veintiséis fragmentos viejos mezclados con diecinueve nuevos.

Era la primera vez que el número de fragmentos bajaba en lugar de
subir, y por eso nunca había aparecido.

**No se habría notado sin `--verificar`.** La búsqueda no lanza ningún
error ante un fragmento viejo, lo devuelve como cualquier otro.

La indexación ahora borra, al terminar, los ids que están en la
colección y no están en la tanda que acaba de escribir. Borra después
y no antes para que un fallo a mitad de camino no deje el índice vacío.

### La reindexación al tope de 1300

Esta vez el conteo subió, de diecinueve a veintidós, que es el caso
que nunca había fallado. Se corrió el `--verificar` igual, en un
proceso nuevo y sin calcular ningún embedding.

```
  fragmentos guardados   22
  el corpus de hoy da    22
```

---

## 16. Errores de medición corregidos

Van escritos porque son la razón de que los scripts de este bloque
tengan guardas.

**Una evaluación medida contra el índice viejo.** Al adoptar el tope de
1300 se corrieron la evaluación y el registro antes de reindexar. Los
dos scripts leen el tope del módulo y la colección del disco, así que
imprimieron *"fragmentos 19"* y *"tope 1300, solape 234"* en renglones
seguidos, y nadie los comparó. La evaluación quedó guardada con la
etiqueta del tope nuevo y los números del viejo, y se habría usado para
las tablas de este documento.

Lo que la delató fueron dos cosas. Las dieciséis preguntas y las ocho
filas de la curva de k salieron idénticas a las del tope 1500 hasta el
último dígito, que con una partición distinta no pasa. Y los tokens de
entrada de las cuatro corridas crecieron exactamente treinta y un
tokens cada una, que es el largo de la plantilla nueva y no el efecto
de fragmentos distintos.

Las cuatro líneas de esa corrida se sacaron del registro, porque el
archivo existe para que cada línea diga con qué configuración se midió
y esas cuatro decían una que no era. Antes de sacarlas se usaron para
separar el efecto de la plantilla del efecto del tope, que es la tabla
de la sección 5 y la de la sección 14.

Al sacarlas, el primer filtro tomó tres de las cuatro, porque la cuarta
tiene su marca de tiempo un segundo después del cambio de minuto. Lo
atrapó contar las líneas que quedaron.

El script podría detenerse solo, comparando los fragmentos de la
colección contra los que da la partición de hoy. Eso no se agregó y
queda como pendiente, porque la lección no lo pide y el episodio ya
está escrito aquí.

**Una afirmación falsa sobre el solape en la cabecera entregada.** La
cabecera de `indexar_corpus.py` decía que por encima del piso el solape
repite entre el uno y el tres por ciento del corpus. Eso es cierto en
otros topes y falso en el entregado, donde repite cero. La medición está
en la sección 11 y la cabecera quedó corregida.

**Un mensaje que culpaba a la causa equivocada.** Cuando la generación
no es la etapa más lenta en todas las corridas, `registro_rag.py`
imprimía que la reconexión al índice de la primera corrida podía
explicarlo. La corrida donde pasó fue la tercera, y la causa son los
tokens de salida. Ahora el mensaje nombra cuál corrida fue y con
cuántos tokens de salida, en vez de suponer.

**El piso escrito con un carácter de más.** La cabecera decía que el
tope tiene que superar a la unidad más larga y que el piso queda en
1058. Medido con una grilla fina, en 1057 ya caben las cuarenta y nueve
unidades. No cambia ninguna decisión, porque el valor adoptado está
muy por encima, pero era un número que la medición contradice. El 1056
y el 1057 entraron a la grilla de `medir_incisos.py` para que el piso
se vea medido.

**Un chequeo que confunde ausente con correcto.** El script que verifica
si una regla llega con su condición solo informa cuando la regla está
nombrada. Si el modelo no la nombra, se queda callado, y callado no es
lo mismo que correcto. En la verificación de la partición nueva eso hizo
que el error del aporte figurara como resuelto cuando en realidad estaba
evitado, porque ese fragmento ya no se recupera para esa consulta. El
límite quedó escrito en la cabecera del script, pero el chequeo en sí no
cambió, así que queda anotado como pendiente.

**Una prueba de fallo que no probaba nada.** Para comprobar que una
corrida interrumpida no escribe líneas sueltas, el primer intento
parcheaba la función desde afuera y el script se volvía a cargar
pisando el parche. Corrió las cinco consultas y escribió cinco líneas
más. Se rehizo haciendo fallar al modelo falso en la tercera llamada, y
ahí sí.

**Un experimento que dejó de reproducir lo suyo.**
`probar_linea_contexto.py` importaba el tope y el solape del indexador,
así que al cambiarlos en este bloque daba cuarenta y seis fragmentos en
vez de los cuarenta y cinco que documentó el Bloque 27. Quedó fijado en
su propia configuración, incluido el texto sin separar, y vuelve a dar
45, 34 y 379%.

**El k escrito en dos lugares.** `RECUPERADOS` en `recuperacion.py` y
`K_ELEGIDO` en `evaluacion_recuperacion.py` eran el mismo número en dos
archivos. Si uno cambiaba sin el otro, la evaluación mediría un k que la
aplicación no usa. Ahora el segundo importa al primero.

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

Una tercera referencia no funda ninguna decisión de este bloque y sí
respalda dos pendientes, así que va aparte, al final de esta sección.

### NitiBench, que describe el fallo en los mismos términos

Es sobre legislación tailandesa, y nombra el problema de la sección 9
tal como apareció aquí.

> *Como la estrategia ingenua de partición no sabe dónde terminan las
> secciones, el texto partido puede contener varias secciones, si la
> sección es más corta que el tope, o quedar incompleto, si la sección
> es más larga que el tope.*

Incompleto cuando la unidad es más larga que el tope. El artículo 168
mide 1057 caracteres y el tope anterior era 700, así que caía justo en
ese caso.

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
enteras. Afinar los números mejora el resultado sin arreglarlo, que es
exactamente lo que pasó en los Bloques 24 y 27 de este proyecto.

Los mismos autores advierten que la ventaja de punta a punta es leve,
y la explican porque el modelo alcanza a filtrar el ruido. El caso de
este proyecto es distinto. Lo que faltaba no era ruido, era ausencia, y
un modelo puede descartar ruido pero no puede recuperar lo que nunca
recibió. Aun así, ellos miden sobre un banco de pruebas grande y este
proyecto mide sobre dieciséis preguntas, que alcanzan para una
dirección y no para una magnitud.

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

Sus 250 tokens **no se comparan con el tope de este proyecto**, y
conviene decirlo porque la tentación es grande. Son otro tokenizador,
y sobre todo cumplen otro papel. Esa ventana gobierna la sub-partición
de adentro de una unidad legal que ya quedó aislada por el corte
estructural. El tope de este proyecto es lo que decide si la unidad
queda aislada o no, porque este proyecto no tiene corte estructural
explícito. Que los dos números queden cerca es una coincidencia y no
una confirmación.

Esa diferencia es justamente lo que justifica el pendiente de cortar
por estructura. La implementación de este proyecto se aproxima a lo que
hacen ellos por otro mecanismo, el tope más la línea en blanco, y por
eso el tope carga con una responsabilidad que en su diseño no tiene.

Subir el tope tiene un riesgo, y ese trabajo lo nombra en su
introducción.

> *Los fragmentos demasiado gruesos diluyen el foco temático. Los
> demasiado finos pierden contexto legal esencial y los anclajes de
> cita.*

Demasiado fino pierde el contexto legal, que es lo que hacía el tope de
700 con el alcance del artículo 40 bis D. Demasiado grueso diluye el
foco, y de esa mitad hay dos mediciones en este documento. La precisión
de la sección 12 subió de 0.203 a 0.271 en vez de bajar, y la sección 14
muestra el otro lado, una consulta que con el tope de 1500 dejaba de
contestar por ruido y con el de 1300 volvió a contestar.

De su sección III.A sale la confirmación de algo que este proyecto ya
hacía desde el Bloque 24.

> *Cada fragmento retiene una copia completa del metadato de su
> documento padre, lo que asegura que el contexto estructural se
> preserve. Esto permite al sistema mantener referencias precisas a la
> fuente de cada fragmento, algo crítico tanto para la exactitud como
> para la trazabilidad en las tareas posteriores.*

Eso es el metadato `articulo`, puesto al partir y heredado por cada
fragmento. En la literatura se llama **metadata inheritance**.

Ese trabajo hay que leerlo sabiendo la diferencia de tamaño. Su corpus
pasa de 3000 páginas y deja más de 6000 sub-fragmentos, con seis campos
de metadato en cada uno. Este tiene once artículos partidos en
veintidós fragmentos, y un solo campo. Respalda el diseño y no la
escala.

### Contextual retrieval, que respalda pendientes y no decisiones

Agregar contexto al fragmento antes de indexarlo tiene nombre propio, y
Anthropic lo publicó con tres cifras que miden cosas distintas.

```
  Anthropic, "Introducing Contextual Retrieval", septiembre de 2024
  anthropic.com/news/contextual-retrieval

  contextual embeddings solos                 -35%   5.7% a 3.7%
  mas contextual BM25, busqueda hibrida       -49%   5.7% a 2.9%
  las dos mas un reordenador                  -67%   5.7% a 1.9%
```

Son reducciones del fallo de recuperación sobre los veinte primeros
fragmentos. Esta referencia no aporta nada a la decisión del tope, que
es de lo que trata este bloque, y se conserva por dos cosas que sí
están en el documento.

Las trece notas que este corpus tiene desde el Bloque 21 son una
versión a mano de la primera cifra, la del 35%, y esta es la única
referencia que le pone nombre a esa técnica. Y la tercera cifra, la del
reordenador, es la que respalda el primero de los pendientes de la
sección 18.

Esas cifras se midieron recuperando veinte fragmentos y este proyecto
recupera tres, así que dan la dirección y no la magnitud.

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

   La primera es la que tiene respaldo publicado más directo. El
   parámetro del trabajo peruano no se puede copiar, porque recuperan
   veinte candidatos y este índice tiene veintidós fragmentos, de modo
   que recuperar veinte sería recuperar casi todo.

2. **La regla del artículo 40 bis D llega sin su condición en la
   pregunta compuesta.** Una corrida de tres, y pasa con esta plantilla
   y con la anterior, así que es preexistente. No es de recuperación.
   La condición está en el mismo fragmento que la regla, porque ese
   artículo mide 933 caracteres y cabe entero con cualquiera de los
   topes probados. Y en la consulta del cálculo, en la misma corrida y
   con el mismo artículo citado, la respuesta sí la nombra.
   Hay una hipótesis concreta y no está medida. La condición es una
   nota al final del artículo, y en la respuesta correcta el modelo la
   puso al principio de la frase. Mover esa nota al comienzo del
   artículo es una decisión de indexación del mismo tipo que separar
   incisos, porque esa nota es un agregado propio y no texto legal.
   Habría que medirlo antes de hacerlo, con más de tres corridas.
3. **El hueco de cobertura de `probar_generacion.py`.** La consulta
   compuesta se agregó a `CASOS` al elegir el tope de 1300, y hasta
   entonces el chequeo de alcance nunca la había tocado, porque probaba
   la consulta del cálculo, que está escrita de otra manera. Lo que no
   está en `CASOS` no se revisa, y durante dos bloques esta consulta no
   estuvo. Conviene revisar qué otras consultas del conjunto de
   evaluación tocan una regla con alcance y no están en la lista.
4. Las preguntas 10 y 15 quedan en recall 0.50, con su fragmento en el
   borde del corte.
5. El registro de latencia no guarda la versión del prompt. En este
   bloque cambiaron la partición y el prompt, y el archivo solo
   distingue la primera. La separación de la sección 5 se pudo hacer
   porque quedó una corrida intermedia por accidente, no porque el
   registro lo permitiera. Si el prompt vuelve a cambiar, convendría
   que también quede en el registro.
6. **La evaluación y el registro no comprueban que el índice
   corresponda al tope del módulo.** El episodio está en la sección 16.
   Los dos scripts tienen los dos números a mano y no los comparan.
   Arreglarlo son unas pocas líneas.
7. El chequeo de alcance de `probar_generacion.py` confunde ausente con
   correcto. Solo informa de una regla cuando el modelo la nombra, así
   que una regla que el modelo nunca menciona deja el chequeo callado, y
   callado no es correcto. El límite está escrito en la cabecera del
   script, pero el chequeo en sí sigue igual. Arreglarlo pide distinguir
   las tres salidas, regla presente y correcta, regla presente y
   equivocada, y regla ausente.
8. **Cortar por estructura de forma explícita**, en vez de dejar que el
   tope decida la integridad de la unidad. Es lo que hacen los dos
   trabajos de la sección 17 y es la diferencia de diseño que obliga a
   este proyecto a volver a medir el tope cuando el corpus cambie.
**Que vienen de bloques anteriores y siguen abiertos.**

9. Apretar o afinar la abstención, planteado en el Bloque 27. La
   plantilla de tres salidas cubrió la parte de la pregunta compuesta y
   el caso del acoso quedó resuelto en la sección 14, así que de este
   pendiente queda la parte general, no un caso concreto abierto.
10. Migrar el corpus de `src/soporte_corpus_legal.py` a archivos `.md`.
   Esto dejó de ser una idea propia. El trabajo peruano de la sección
   17 convierte los documentos a Markdown como formato intermedio antes
   de segmentarlos, y limpia encabezados y pies en ese paso.
   > *En una etapa inicial, estos archivos se convierten a un formato
   > intermedio, como Markdown (.md).*
11. El empate de cuatro milésimas de la sección 6 del
   `limites_bloque27.md` no tiene tratamiento. El corte en k es duro y
   parte empates que no significan nada.
12. Volver a medir la línea de contexto del Bloque 27 cuando el corpus
   crezca.
13. Cerrar el hueco de `--verificar`, planteado en el Bloque 26 y
   todavía abierto. Compara cuántos fragmentos hay guardados contra
   cuántos daría el corpus de hoy, así que atrapa que se agregue o se
   saque un artículo, y no atrapa un cambio de texto que no cambie la
   cuenta. Cerrarlo pide comparar el contenido y no la cuenta.
**Cerrado en este bloque.**

El pendiente que pedía una respuesta parcial correcta para la consulta
del acoso, en vez de una abstención, quedó resuelto y está en la
sección 14.
