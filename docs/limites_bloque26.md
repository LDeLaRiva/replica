# Límites y hallazgos de la recuperación semántica (Bloque 26)

Qué se midió, qué salió y qué quedó sin resolver al conectar la
búsqueda por significado al corpus legal.

Las decisiones de diseño están en el encabezado de
`src/recuperacion.py`. Este documento recoge las corridas que las
respaldan.

---

## 1. Qué se corrió

`src/recuperacion.py` sobre el índice del Bloque 24, once artículos
partidos en cuarenta y cinco fragmentos, en la colección
`corpus_legal_chile`.

Cuatro consultas por corrida.

```
  del corpus                         aviso por necesidades de la empresa
  del corpus                         cálculo de la indemnización
  fuera del corpus, del mismo tema   vacaciones
  fuera del corpus, de otro tema     la receta del pastel de choclo
```

Ocho llamadas por corrida, cuatro embeddings de pregunta y cuatro
respuestas.

---

## 2. Las comprobaciones de la actividad

Las cuatro pasaron.

```
  citas con k entradas, claves 1 a k                   cumple
  ningún valor dice desconocida                        cumple
  el prompt lleva la pregunta exacta sin recortar      cumple
  el contexto numera desde 1 sin saltos                cumple

  el contexto cambia entre las dos del corpus          cumple
  la pregunta fuera del corpus no se inventa           cumple, las dos
  verificar una cita a mano                            cumple
```

Las dos primeras comprobaciones están automatizadas dentro del
script. La tercera está en la sección 11 de este documento.

---

## 3. Por qué el k pasó de 3 a 4

Con k=3 la segunda consulta devolvió una respuesta legalmente
equivocada. Antes de mover el valor se midió dónde había quedado el
fragmento que sí respondía.

Las diez posiciones más cercanas a la consulta por el cálculo de la
indemnización, con su distancia de Chroma. Menor es más parecido.

```
  pos  distancia  artículo    empieza con
    1     0.4598  163         [1] Art. 163. Si el contrato hubiere
    2     0.4923  40 bis D    Art. 40 bis D. Para los efectos del
    3     0.5020  163         b) La obligación de efectuar el aporte
    4     0.5340  163         [2] A falta de esta estipulación
    5     0.5759  168         a) En un treinta por ciento
    6     0.5798  172         [2] Si se tratare de remuneraciones
    7     0.6047  163         a) Tendrán derecho, cualquiera que sea
    8     0.6077  172         [1] Art. 172. Para los efectos del pago
    9     0.6188  168         [1] Art. 168. El trabajador cuyo
   10     0.6234  163         [3] Si el contrato celebrado para una
```

El fragmento que responde la pregunta es el inciso 2 del artículo
163, el de los treinta días por año con tope de trescientos treinta.
Quedó en la posición 4.

Los saltos entre posiciones consecutivas.

```
   1 -> 2    0.0325
   2 -> 3    0.0097
   3 -> 4    0.0320     el corte con k=3 pasaba por aquí
   4 -> 5    0.0419     el salto más grande de los diez
   5 -> 6    0.0039
   6 -> 7    0.0249
   7 -> 8    0.0030
   8 -> 9    0.0111
   9 -> 10   0.0046
```

Dos cosas salen de esa tabla.

El salto que separaba al tercero del cuarto, 0.0320, es del mismo
tamaño que el que separa al primero del segundo, 0.0325. El
fragmento correcto no estaba lejos, estaba justo debajo del corte.

Y el salto más grande de los diez cae entre la posición 4 y la 5.
Ahí es donde la propia distribución indica que conviene cortar.

El valor subió a 4 y no más. La actividad ofrece empezar en 3 o en
4, así que 4 es uno de los dos valores propuestos, y es hasta donde
llega lo medido.

Estas distancias no son porcentajes ni probabilidades. Solo valen
comparadas entre sí dentro de esta misma corrida, con este modelo y
este corpus.

---

## 4. Las tres primeras eran excepciones y la regla general quedó cuarta

Mirando qué es cada una de las cuatro primeras de esa tabla.

```
  1   163 inciso 1     la indemnización pactada, si hay pacto
  2   40 bis D         el caso de jornada parcial
  3   163 letra b)     el caso de trabajadores de casa particular
  4   163 inciso 2     la regla general
```

Las tres que entraban con k=3 son excepciones o reglas
condicionadas. La regla general quedaba afuera.

La causa está en cómo abre cada texto. El artículo 40 bis D empieza
con "Para los efectos del cálculo de la indemnización", que es casi
la pregunta escrita de otra forma. El inciso 2 del 163 empieza con
"A falta de esta estipulación", que es una remisión hacia atrás y no
nombra su materia.

La búsqueda por significado premia al texto que se anuncia. En un
corpus legal, el que se anuncia suele ser la excepción, porque la
regla general se enuncia una vez y después se la referencia.

---

## 5. Los dos errores legales de la segunda respuesta

Con k=4 la respuesta empieza correcta y sigue con dos afirmaciones
que son falsas para un trabajador de jornada completa.

**El artículo 40 bis D presentado como regla general.** El modelo
respondió que la última remuneración es el promedio de las
remuneraciones de los últimos once años reajustadas por IPC. Eso es
el 40 bis D, que se aplica solo a jornada parcial, treinta horas
semanales o menos. La herramienta de cálculo del Bloque 22 ya lo
trataba así, aplicándolo únicamente cuando la jornada informada es
de treinta horas o menos.

**El aporte de casa particular presentado como regla general.** El
modelo respondió que el monto puede quedar determinado por los
aportes del período más su rentabilidad. Eso es la letra b) del
inciso 5 del artículo 163, que rige solo para trabajadores de casa
particular.

Los dos errores tienen una sola causa. **El fragmento recuperado
trae la regla y no trae la condición que limita su alcance**, porque
esa condición quedó en otro fragmento o en otro artículo.

El prompt no puede corregir esto. No le falta instrucción al modelo,
le falta información. Con el contexto que recibió, no tenía cómo
saber que esas dos normas eran excepciones.

---

## 6. Diecinueve caracteres

El artículo 40 bis D del corpus ya trae una nota de alcance escrita
al final.

> [nota: este artículo integra el párrafo que abre el artículo 40
> bis, cuyo texto declara afectos a esa normativa los contratos de
> jornada no superior a treinta horas semanales. Fuera de la jornada
> parcial no se aplica]

Dice exactamente lo que hacía falta y no llegó al prompt.

```
  largo del artículo 40 bis D      933 caracteres
  tope del chunking                700
  el corte real cae en el          697
  la nota empieza en el            716
```

Diecinueve caracteres. El primer fragmento termina en "fuere
superior, se" y la nota empieza diecinueve caracteres después.

El segundo fragmento sí la trae, porque el solape de 126 caracteres
la alcanza. Pero la búsqueda recuperó el primero.

El caso del aporte de casa particular es el mismo en otra escala. La
frase que dice que esa regla no se aplica a los demás trabajadores
está en el encabezado del inciso 5 del artículo 163, y la letra b)
quedó en un fragmento aparte.

No es que al corpus le falte la salvaguarda. **La tiene y el
chunking la separó de la regla que protege.**

---

## 7. La abstención a dos distancias

La actividad pide una pregunta que el corpus no pueda responder. El
profesor, en clase, propuso como ejemplo algo de otro tema por
completo. Se probaron las dos.

```
  vacaciones            el feriado anual son los artículos 67 al 76
                        y no están indexados. Pero el 66 sí, y
                        menciona el feriado anual al pasar, así que
                        la búsqueda trae algo del mismo tema

  pastel de choclo      no hay nada cerca en el corpus
```

Las dos se abstuvieron con la frase exacta, en todas las corridas.

La de vacaciones es la más exigente de las dos, porque el contexto
traía el artículo 66 hablando de días de permiso y del feriado
anual. El modelo tuvo material tentador delante y no lo usó.

---

## 8. La búsqueda nunca dice que no tiene nada

Para la pregunta por la receta del pastel de choclo, la recuperación
devolvió esto.

```
  [1]  art. 172       remuneración, con aguinaldos de navidad
  [2]  art. 40 bis D
  [3]  art. 168       acoso sexual
  [4]  art. 172       el pedazo de los aguinaldos otra vez
```

Cuatro artículos del Código del Trabajo para una pregunta de cocina,
con total seguridad y sin ninguna señal de que no venían al caso.

Esto es lo contrario de la búsqueda por palabra clave del Bloque 21,
que para esa misma consulta habría respondido que no encontró
ningún artículo sobre ese tema.

```
  por palabra clave     dice que no lo tiene, y se pierde los
                        sinónimos

  por significado       encuentra los sinónimos, y nunca dice
                        que no lo tiene
```

Fallan al revés. Lo único que evita que una de ellas conteste
cualquier cosa es la instrucción de abstención del prompt. Esa frase
no es decorativa, es la pieza que cierra el hueco que la búsqueda
por significado deja abierto por diseño.

### Y pierden cosas distintas

Hay una segunda diferencia entre las dos, y es la que explica los
errores de la sección 5.

La búsqueda por palabra devuelve el artículo entero. La búsqueda por
significado devuelve fragmentos.

Para la consulta por el cálculo de la indemnización, la búsqueda por
palabra calza con las claves `indemniz` y `anos de servicio` y
devuelve el artículo 163 completo, con su inciso 5 incluido, que es
el que dice que lo anterior no se aplica a los trabajadores de casa
particular.

```
  la frase "trabajadores de casa particular"

  en el artículo 163 completo            sí
  en los cuatro fragmentos del prompt    en ninguno
```

El modelo recibió la letra b) sin el encabezado que la condiciona.
Partir el texto es lo que hace posible recuperar con precisión, y es
también lo que separa una regla de su alcance.

Ninguna de las dos basta sola. Para esa misma consulta, la búsqueda
por palabra no habría traído el artículo 40 bis D, porque ninguna de
sus claves calza, y para un trabajador de jornada parcial ese
artículo sí viene al caso. Una conserva la estructura y se pierde el
artículo, la otra encuentra el artículo y se pierde la estructura.

---

## 9. El mismo contexto dio dos órdenes distintos

Se corrió tres veces la misma consulta por el cálculo de la
indemnización, con k=4.

**La recuperación fue idéntica las tres veces**, los mismos cuatro
fragmentos en el mismo orden.

La respuesta no.

```
  corrida 1   arranca con los treinta días del 163
  corrida 2   arranca con el promedio del 40 bis D
  corrida 3   arranca con los treinta días del 163
```

Las tres dicen las mismas tres cosas. Lo que cambia es cuál va
primero.

Para una aplicación de consulta laboral eso pesa, porque lo primero
que lee un trabajador es con lo que se queda, y hoy esa parte no es
estable.

No se puede fijar con el parámetro de temperatura. Está documentado
en `src/cadena_tres_pasos.py` que Google lo marcó como obsoleto en
los modelos flash de esta generación, que lo ignoran. Y aunque se
pudiera, la temperatura en cero reduce la variación pero no la
elimina.

Esta observación explica por qué el Bloque 27 mide la recuperación y
no la respuesta. La recuperación es reproducible y se puede medir.
La respuesta cambia entre corridas, de modo que juzgarla por una
sola no demuestra nada.

---

## 10. Los corchetes, que marcan dos cosas a la vez

Los incisos de este corpus van numerados entre corchetes, y el
prompt le pide al modelo que cite entre corchetes. En el contexto
que llega al modelo, las dos numeraciones quedan pegadas.

```
  [1] [1] Art. 161. Sin perjuicio de lo señalado...
       ↑   ↑
       |   el número de inciso, que es del texto legal
       el número de cita, que pone formatear_contexto
```

De esa coincidencia salieron dos problemas distintos.

### El primero, las citas de varios números

En una de las corridas el modelo respaldó una afirmación con dos
fragmentos a la vez, escribiendo `[1, 4]`.

La expresión regular de la lección es `\[(\d+)\]`, que exige
corchete, dígitos y corchete. No reconoce esa forma, así que las dos
citas se perdieron, y eran justamente las que sostenían la parte
correcta de la respuesta.

El fallo no avisa. El listado de fuentes sale más corto y nada
indica que falte ninguna.

Se corrigió buscando primero los grupos entre corchetes que
contengan solo dígitos y separadores, y después los números de cada
grupo. Esa primera condición es la que deja afuera a las notas del
corpus, que también van entre corchetes y traen números adentro.

Se probó contra nueve formas distintas antes de aplicarlo, incluidas
`[1,4]` sin espacio, `[1; 4]`, `[1][4]`, un `[9]` que no existía en
el contexto y una nota del corpus pegada en la respuesta.

En la corrida final el modelo citó `[4]` solo, de modo que el caso
que motivó la corrección no se ve en la evidencia de esa corrida. El
caso fue real y está en la corrida anterior.

### El segundo, que no se puede cerrar

Si el modelo copiara textualmente una línea del contexto que empiece
con un marcador de inciso, ese marcador quedaría indistinguible de
una cita. Se probó y ocurre.

```
  la respuesta dice    dice "[2] A falta de esta..." y cito [1]
  se leen como citas   el 2 y el 1
```

El 2 no era una cita, era texto copiado del artículo.

No pasó en ninguna de las corridas, porque el modelo parafraseó en
todas. Y no se puede cerrar. Cambiar el formato de la cita rompe el
criterio de la actividad, que pide números entre corchetes, y
sacarle los corchetes al texto legal lo volvería no literal, que es
lo único que este proyecto no se puede permitir.

Lo que sí hay es una red parcial. Un número que no esté en el
diccionario se nombra como cita inválida en vez de resolverse a
cualquier artículo. Eso atrapa el caso en que el número copiado sea
mayor que el k, y no el caso en que coincida con un bloque real.

---

## 11. La verificación manual de una cita

Es la tercera comprobación que pide la actividad. Se hizo comparando
textos y no a ojo.

De la primera consulta, el modelo citó `[2]`.

```
  citas[2] dice        soporte_corpus_legal.py · art. 162

  el bloque que llegó al prompt es un trozo literal del
  inciso 4 del artículo 162                               sí
  largo del bloque 694, del inciso 824

  las dos afirmaciones de la respuesta, contra el texto
    a lo menos con treinta días de anticipación           literal
    indemnización en dinero efectivo sustitutiva del
    aviso previo                                          literal
```

El fragmento que viajó al prompt es un trozo exacto del artículo, sin
una palabra cambiada, y las dos cosas que el modelo afirmó están
escritas ahí.

---

## 12. Un hueco en --verificar

Salió al revisar qué pasa cuando el corpus crece.

`python src/indexar_corpus.py --verificar` compara cuántos
fragmentos hay guardados contra cuántos daría el corpus de hoy. Eso
atrapa que se agregue o se saque un artículo, que es lo que pasó al
entrar el 159 y el 172.

Lo que no atrapa es un cambio de texto que no cambie la cuenta. Si se
corrige una palabra del artículo 162 y los fragmentos siguen siendo
cuarenta y cinco, verificar informa que el índice está al día y la
búsqueda sigue respondiendo con el texto viejo.

El chequeo no miente, cuenta y compara, que es lo que su docstring
dice. El que promete de más es el mensaje, que dice que el índice
está al día con el corpus.

La costumbre ya cubre el caso, porque después de tocar el corpus se
corre `--reindexar`. Cerrarlo en código sería comparar el contenido
y no la cuenta.

---

## 13. Por qué el corpus vive en un .py y no en archivos .md

Los ejemplos del curso etiquetan los fragmentos con nombres de
archivo `.md`, y en clase se recomendó convertir a ese formato los
documentos que se vayan a indexar.

Ninguno de esos archivos existe. Tanto el ejemplo de la lección como
el del ayudante escriben el texto a mano dentro de un `.py` y le
pegan un nombre de archivo inventado como metadato. Y la entrega del
Bloque 24 son tres archivos, el script, el requirements y el
gitignore, sin ningún archivo de corpus.

La razón de fondo para mantenerlo así es otra. En este proyecto cada
artículo es un par, el texto y las claves de búsqueda por palabra
que usa `buscar_articulos`. Separando el texto a un `.md`, las
claves quedarían en el `.py` y un mismo artículo pasaría a vivir en
dos archivos que se pueden desincronizar.

Además el texto está verificado contra la fuente artículo por
artículo, y moverlo obligaría a rehacer esa verificación.

Esta decisión dejaría de servir si el corpus creciera mucho, si
tuviera que mantenerlo alguien que no programa, o si entrara
material que venga de PDF. En cualquiera de esos casos lo correcto
sería pasar a archivos y escribir un cargador.

La migración está planificada de todas formas, por una razón
distinta de esas tres. Está en la sección 14.

---

## 14. Lo que queda pendiente

**Mover la nota de alcance del artículo 40 bis D al principio del
artículo**, para que el primer fragmento la lleve siempre. Es el
arreglo de la sección 6 y no requiere escribir nada nuevo, solo
cambiar de lugar lo que ya está. Obliga a reverificar el texto,
reindexar y volver a correr.

**Medir si el mismo problema afecta a otros artículos.** El del
aporte de casa particular es el segundo caso conocido. No se ha
revisado si hay más incisos cuya condición de alcance quedó en otro
fragmento.

**Fijar un umbral de cercanía para detectar empates.** Cuando dos
fragmentos de artículos distintos quedan casi a la misma distancia,
la respuesta podría presentar los dos con su condición en vez de
elegir uno en silencio. El metadato del artículo es lo que permite
saber que son de artículos distintos. El umbral no se puede sacar de
la teoría, porque estas distancias no son probabilidades, así que se
fija en el Bloque 27 con consultas reales a la vista.

**Cerrar el hueco de `--verificar`** comparando contenido y no
cuenta, si alguna vez deja de alcanzar con la costumbre.

**Pasar el corpus a archivos `.md`.** La sección 13 explica por qué
hoy vive en un `.py` y bajo qué condiciones esa decisión dejaría de
servir. Ninguna de esas condiciones se cumple todavía, y aun así
conviene migrar, porque once artículos cuestan menos que cuarenta y
el corpus va a crecer.

Lo que hay que resolver es dónde quedan las claves de búsqueda por
palabra. Una forma es que el número del artículo salga del nombre
del archivo, `art_162.md`, y que las claves vivan en un diccionario
con ese mismo número como llave, con una comprobación al cargar de
que todo archivo tenga sus claves y toda entrada de claves tenga su
archivo. El texto no hay que volver a verificarlo contra la fuente,
basta comparar los archivos nuevos contra el texto ya verificado y
confirmar que son idénticos carácter por carácter.
