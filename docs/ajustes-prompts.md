# Ajustes al banco de prompts

> Registro de las mediciones de consistencia del banco y de las
> correcciones aplicadas a los prompts. Cada iteración deja lo que
> se observó, el cambio hecho y el resultado de volver a medir.
>
> **Proyecto** · Miniaplicación de consultas laborales
> **Modelo** · gemini-3.5-flash-lite
> **Última medición** · 23 de octubre de 2026

---

## Mediciones

Las mediciones 1 a 9 se hicieron el 22 de octubre de 2026 y la
10 el 23 de octubre.

| # | Qué se midió | responder_consulta | extraer_datos_contrato | revisar_clausula | listar_materias_contrato |
|---|---|---|---|---|---|
| 1 | línea base, 3 repeticiones | 3/3 | 3/3 | 3/3 | — |
| 2 | línea base, 5 repeticiones | 5/5 | 5/5 | 5/5 | — |
| 3 | después de las iteraciones 1 y 2 | 5/5 | 5/5 | 5/5 | — |
| 4 | confirmación de la anterior | 5/5 | 5/5 | 5/5 | — |
| 5 | después de la iteración 3 | 5/5 | 5/5 | 5/5 | 5/5 |
| 6 | después de la iteración 4 | 5/5 | 5/5 | 5/5 | 5/5 |
| 7 | después de la iteración 5 | 5/5 | 5/5 | 5/5 | 5/5 |
| 8 | después de la iteración 6 | 5/5 | 5/5 | 5/5 | 5/5 |
| 9 | después de la iteración 7 | 5/5 | 5/5 | 5/5 | 5/5 |
| 10 | después de la iteración 8 | 5/5 | 5/5 | 5/5 | 5/5 |

> [!NOTE]
> El conteo dio 5/5 en casi todas las tandas, y aun así los prompts
> cambiaron mucho entre una y otra. El conteo mide si la respuesta
> trae las claves esperadas. No mide si el valor es consistente ni
> si el contenido es cierto. Las iteraciones de abajo se apoyan en
> revisar las respuestas una por una, no en el número.

---

## Iteración 1 — formato de la fuente citada

`responder_consulta` · 22 de octubre de 2026

### Qué se observó

Las cinco repeticiones pasaron la validación de estructura, pero el
campo que indicaba el respaldo volvió en tres formatos distintos.

```text
Artículo 67 del Código del Trabajo    3 veces
Artículo 67 y Artículo 68             1 vez
Artículo 67                           1 vez
```

El conteo marcaba 5/5 porque la clave estaba presente. La prueba
verifica la estructura, no el valor.

### Qué se cambió

La instrucción pedía "el artículo del Código del Trabajo en que te
basas", sin indicar formato. Se hicieron dos cambios.

1. El campo pasó a llamarse `fuente`, y ahora se pide el documento
   y la parte exacta, no solo un número. El nombre anterior solo
   servía mientras el corpus fuera el Código del Trabajo, y el
   proyecto contempla sumar dictámenes de la Dirección del Trabajo.
2. Se permitió responder `no identificado` cuando no se pueda
   determinar la fuente. El esquema la exigía siempre, sin dejarle
   al modelo ninguna forma de indicar que no estaba seguro.
### Resultado

El conteo se mantuvo en 5/5, porque el problema no era estructural.
Lo que cambió fue el valor del campo.

```text
antes     Artículo 67 del Código del Trabajo    3 veces
          Artículo 67 y Artículo 68             1 vez
          Artículo 67                           1 vez

después   Código del Trabajo artículo 67        5 veces
```

El formato se mantuvo estable en todas las tandas posteriores.

---

## Iteración 2 — contenido no solicitado

`responder_consulta` · 22 de octubre de 2026

### Qué se observó

Al revisar el contenido aparecieron errores que el conteo no
detecta. De las cinco respuestas, dos eran correctas.

- Una afirmó que el día sábado se considera siempre hábil para
  efectos del feriado. El artículo 69 del Código del Trabajo
  establece lo contrario, que se considera siempre inhábil.
- Una devolvió texto cortado, con una región inexistente y la zona
  geográfica equivocada.
- Una citó el artículo 68, que regula otra materia.
Las cinco contaron como válidas, porque traían las claves pedidas.

### Qué se cambió

Las tres fallas tenían algo en común. Ninguna estaba en la
respuesta a la pregunta, sino en información que el modelo agregó
por su cuenta sin que se le pidiera.

1. Se agregó la instrucción de responder solo lo que se pregunta,
   sin agregar información que no se haya pedido.
2. El largo máximo de la respuesta bajó de tres oraciones a dos.
3. Las instrucciones de los tres prompts se reordenaron según la
   estructura RTCF, es decir rol, tarea, contexto y formato. Antes
   cada una usaba un subconjunto distinto de esas partes. Las
   restricciones nuevas quedaron en el apartado de contexto, que
   era justamente el que faltaba en dos de los tres.
### Resultado

Las tres tandas siguientes salieron limpias, sin una sola adición
ni error, lo que en su momento se interpretó como que el problema
estaba resuelto.

Una cuarta tanda, varias horas después, mostró que no.

```text
intento 2    volvió a afirmar que el sábado es hábil
intento 3    agregó las reglas regionales
intento 5    agregó las reglas regionales
```

Sumando todas las respuestas producidas con esta versión del
prompt, el resultado real es este.

```text
                        antes del cambio    después del cambio
                        5 respuestas        20 respuestas

agregó contenido        5    (100 %)        3    (15 %)
error de fondo          1    (20 %)         1    (5 %)
```

La mejora es grande, pero no es eliminación. Tres tandas seguidas
sin fallas no bastaban para concluir que el problema estaba
resuelto, y conviene dejarlo anotado como aprendizaje del
ejercicio.

---

## Iteración 3 — cuarto prompt, salida de tipo lista

`listar_materias_contrato` · 22 de octubre de 2026

### Qué se observó

El banco cumplía el mínimo de tres prompts, pero los tres devolvían
campos sueltos. Ninguno devolvía una cantidad variable de
elementos, que es un caso distinto de manejar tanto para el modelo
como para el código que después lo consume.

Revisados contra los tipos que acepta la API, faltaba `ARRAY`.

### Qué se cambió

Se agregó un cuarto prompt, `listar_materias_contrato`, que recibe
un contrato y devuelve la lista de materias que el texto aborda.

Sigue el mismo criterio que `revisar_clausula`. El modelo solo
identifica lo que el texto trata, y la comparación contra lo que la
ley exige la hace el programa.

### Resultado

Las cinco repeticiones devolvieron la misma lista, en el mismo
orden.

```text
['cargo', 'lugar_trabajo', 'plazo', 'jornada', 'remuneracion']
```

La consistencia fue mayor de la esperada para una salida de tipo
lista, que tiene más libertad que un campo suelto.

Pero la lista omitía la fecha de inicio, pese a que el contrato de
ejemplo la menciona. Eso abrió la iteración siguiente.

---

## Iteración 4 — vocabulario cerrado para las materias

`listar_materias_contrato` · 22 de octubre de 2026

### Qué se observó

La instrucción daba ejemplos de etiquetas pero dejaba la lista
abierta, de modo que el modelo elegía cómo nombrar cada materia.
Los ejemplos no incluían ninguna fecha, y el modelo se ciñó a
ellos.

El problema de fondo no era el ejemplo que faltaba, sino que una
lista abierta no sirve para comparar. El programa tiene que
contrastar lo que el contrato trata contra lo que exige el artículo
10 del Código del Trabajo, y eso requiere que ambas listas usen las
mismas palabras.

### Qué se cambió

Se reemplazaron los ejemplos por una lista cerrada de diez
etiquetas, derivada de las menciones que exige el artículo 10.

```text
lugar_fecha_contrato     identificacion_partes
fecha_ingreso            cargo
lugar_trabajo            remuneracion
jornada                  plazo
beneficios_especie       otros_pactos
```

La instrucción indica usar únicamente esas, sin inventar otras.

### Resultado

`fecha_ingreso` apareció desde la primera repetición.

```text
antes     ['cargo', 'lugar_trabajo', 'plazo', 'jornada',
           'remuneracion']

después   ['identificacion_partes', 'fecha_ingreso', 'cargo',
           'lugar_trabajo', 'remuneracion', 'jornada', 'plazo']
```

El modelo nunca devolvió las diez etiquetas, lo que confirma que
está leyendo el contrato y descartando, no repitiendo la lista
recibida.

Queda una variación menor. `identificacion_partes` aparece en
cuatro de cada cinco repeticiones. El artículo 10 Nº 2 exige
nacionalidad, domicilio, fecha de nacimiento y fecha de ingreso, y
el contrato de ejemplo solo nombra a las partes, de modo que el
caso es genuinamente ambiguo. La ambigüedad está en la instrucción,
no en el modelo.

---

## Iteración 5 — excepciones y casos regionales

`responder_consulta` · 22 de octubre de 2026

### Qué se observó

Las adiciones que seguían apareciendo en `responder_consulta` eran
todas del mismo tipo.

```text
"el día sábado se considera siempre hábil"       caso especial
reglas de Magallanes, Aysén y Palena             regla regional
reglas de la Duodécima Región                    regla regional
```

La instrucción decía "sin agregar información que no se haya
pedido", en términos generales. No nombraba el tipo de contenido
que efectivamente se colaba.

### Qué se cambió

Se agregó al contexto una restricción explícita.

> No menciones excepciones, reglas regionales ni casos especiales
> salvo que la pregunta los mencione.

En la misma edición, y sin relación con el comportamiento del
modelo, el contrato de ejemplo que comparten dos prompts se definió
una sola vez en una constante, porque estaba escrito dos veces y
con textos distintos.

### Resultado

```text
sin la restricción    3 de 5 agregaron, 1 con error de fondo
con la restricción    1 de 5 agregó, 0 con error
```

La única adición fue una regla regional correcta en su contenido,
aunque igualmente no solicitada.

> [!WARNING]
> Cinco repeticiones no bastan para afirmar que la restricción
> funciona. Un 20 % de adiciones no se distingue estadísticamente
> del 15 % anterior con una muestra de ese tamaño. La iteración 2
> ya había mostrado que tres tandas limpias seguidas pueden ser
> casualidad. Lo que sí está medido, sobre veinticinco respuestas,
> es la mejora frente a la versión original del prompt.

Sobre la constante del contrato, el prompt `extraer_datos_contrato`
devolvió los mismos cuatro valores, idénticos en las cinco
repeticiones, con el texto unificado. El cambio no alteró su
comportamiento.

---

## Iteración 6 — atribución de la fuente y cláusulas sin cantidad

`responder_consulta` y `revisar_clausula` · 22 de octubre de 2026

### Qué se observó

Dos defectos distintos, encontrados al usar el programa con
consultas que los ejemplos del banco no cubren.

**El primero.** A la pregunta por el máximo de horas
extraordinarias, el modelo respondió tres cosas ciertas y citó el
artículo que respalda solo una.

```text
respuesta  Se puede trabajar un máximo de dos horas
           extraordinarias por día. Estas deben pactarse por
           escrito y solo se admiten para atender necesidades o
           situaciones temporales de la empresa.
fuente     Código del Trabajo artículo 31
```

Verificado contra el texto oficial en BCN, el máximo de dos horas
está en el artículo 31, mientras que el pacto por escrito y las
necesidades temporales están en el 32.

La instrucción daba dos ejemplos de fuente, los dos en singular, y
no decía qué hacer cuando la respuesta se apoya en más de una
norma.

**El segundo.** El campo `valor` de `revisar_clausula` es un número
obligatorio, sin ninguna salida prevista. Una cláusula que no
establece cantidades, como la que solo define el cargo, obliga al
modelo a producir un número igual. Es el mismo defecto que tenía el
campo `fuente` antes de la iteración 1.

### Qué se cambió

1. En `responder_consulta` se agregó al contexto la instrucción de
   no afirmar nada que no se pueda atribuir a la norma citada, y de
   nombrar la otra norma si parte de la respuesta sale de ella.
   Una primera versión de este cambio pedía "nombra todas las
   normas en que se apoye tu respuesta" y quedó dentro de la
   descripción del campo, en el apartado de formato. No tuvo
   efecto. Se reubicó en el apartado de contexto, que es donde la
   estructura RTCF pone las reglas de comportamiento, y se
   reformuló para pedir no afirmar en vez de pedir citar más.
2. En `revisar_clausula` se indicó usar 0 en `valor` y la palabra
   ninguna en `unidad` cuando la cláusula no establece ninguna
   cantidad.
### Resultado

Los dos cambios se comprobaron ejecutando `main.py`, que toma la
instrucción del banco y la pregunta por separado, de modo que
permite probar un caso puntual sin alterar la medición.

**El segundo cambio funciona.** Con una cláusula sin cantidades.

```text
materia  funciones
valor    0
unidad   ninguna
```

Ningún número inventado.

**El primero funciona en parte.** Con la consulta de las horas
extraordinarias.

```text
antes     dos horas por día, más el pacto por escrito y las
          necesidades temporales, citando solo el artículo 31

después   No se pueden trabajar más de dos horas extraordinarias
          por día.
          Código del Trabajo artículo 31
```

Soltó las afirmaciones que venían del artículo 32 en lugar de
citarlo. Las dos salidas servían, y la cita quedó cubriendo
exactamente la respuesta.

Pero en la medición completa, tres de cinco repeticiones de la
pregunta por el feriado agregaron que el día sábado no se considera
hábil, citando el artículo 67. Esa regla está en el 69.

La instrucción solo se activa cuando el modelo reconoce que una
afirmación viene de otra norma. Si cree que está en la que ya citó,
no hay nada que atribuir y la regla no opera.

> [!NOTE]
> Un dato sobre la variabilidad. La misma afirmación sobre el día
> sábado apareció invertida en la segunda medición, diciendo que sí
> se considera hábil, que es lo contrario de lo que establece el
> artículo 69. En esta medición salió correcta. Ese cambio no
> responde a ningún ajuste, es variación entre corridas del mismo
> prompt.

---

## Iteración 7 — una frase que autorizaba lo que otra prohibía

`responder_consulta` · 22 de octubre de 2026

### Qué se observó

La tanda 8 mostró tres adiciones de cinco, contra una de cinco en
la tanda anterior. Al revisar el texto de la instrucción apareció
una contradicción interna.

```text
"responde solo lo que se pregunta"
"no menciones excepciones ni casos especiales"
"si parte de tu respuesta sale de otra norma, nómbrala también"
```

La tercera frase, agregada en la iteración 6, da por supuesto que
una respuesta puede apoyarse en otras normas, y pide nombrarlas.
Eso afloja lo que las dos anteriores prohíben.

### Qué se cambió

Se eliminó esa media frase. Quedó solo la parte que había
demostrado servir.

> No afirmes nada que no puedas atribuir a la norma que citas.

### Resultado

La medición empeoró en vez de mejorar.

```text
tanda 8, con la frase       3 de 5 agregaron
tanda 9, sin la frase       4 de 5 agregaron
```

Ninguna de las adiciones fue falsa. Dos repitieron las reglas
regionales, que están en el mismo artículo 67 que se citó, una
repitió la regla del sábado, y una fue relleno sin contenido.

La hipótesis de la contradicción interna no se sostuvo. Lo que el
cambio dejó a la vista es otra cosa, que se explica en la sección
siguiente.

---

## Iteración 8 — cita a nivel de artículo

`responder_consulta` · 23 de octubre de 2026

### Qué se observó

Al usar `main.py` con una consulta sobre el permiso por fallecimiento
de un hijo, el contenido salió correcto en cinco corridas, incluido
el número de días, que fue reformado y cuya versión antigua sigue
repetida en muchas fuentes. La fuente, en cambio, falló de tres
maneras distintas.

```text
artículo 66 ter            existe, pero regula permisos de vacunación
artículo 66 inciso primero la respuesta se apoyaba además en el tercero
artículo 66 inciso primero en una consulta cuya regla está en el quinto
```

La estructura del artículo 66 se verificó contra el texto oficial.

```text
inciso 1   hijo diez días corridos, cónyuge o conviviente civil siete
inciso 2   hijo en gestación, hermano, padre o madre
inciso 3   desde cuándo se hacen efectivos los permisos
inciso 4   el fuero de un mes
inciso 5   no se compensan en dinero
```

### Qué se probó antes

Cuatro redacciones distintas del campo `fuente`, todas pidiendo que
nombrara todas las partes en que se apoya la respuesta, separadas por
coma. Una de ellas se midió en tres corridas y no tuvo efecto, la
fuente siguió siendo `artículo 66 inciso 1` las tres veces.

### Por qué ninguna podía funcionar

El número de inciso no es contenido de la norma. Es una propiedad de
cómo está dispuesto el texto, y se obtiene contando los párrafos del
artículo. Los incisos no vienen numerados en la ley, se cuentan.

Se diseñó una prueba para verificarlo y se escribió la predicción
antes de ejecutarla. Si el modelo recita etiquetas en vez de contar
párrafos, una consulta cuya respuesta está en el inciso quinto no
sería citada como tal, porque ese inciso casi no aparece citado con
número en la literatura.

```text
consulta   ¿Los días de permiso por fallecimiento se pueden pagar
           en dinero?
regla      inciso quinto del artículo 66
respuesta  correcta, no se pueden compensar en dinero
fuente     Código del Trabajo artículo 66 inciso primero
```

La predicción se cumplió, y de forma más clara de lo previsto. No
eligió mal entre cinco incisos, repitió la misma etiqueta que había
usado en las cinco corridas anteriores sobre otra materia del mismo
artículo. La pregunta cambió por completo y la cita no se movió.

### Qué se cambió

La descripción del campo pasó de pedir "el documento y la parte
exacta" a pedir "el documento y el artículo". Dos palabras, ninguna
frase nueva.

Se descartó la formulación inversa, instruirle que no bajara al
inciso, porque una prohibición dirigida al formato puede leerse como
una instrucción de no considerar esa parte del texto al responder.
El riesgo de esa versión era una respuesta peor, no solo una cita más
pobre.

### Resultado

```text
antes     Código del Trabajo artículo 66 ter
          Código del Trabajo artículo 66 inciso primero
después   Código del Trabajo artículo 67        5 de 5 repeticiones
```

Las cinco citas salieron a nivel de artículo, sin inciso ni sufijo.

> [!NOTE]
> La frase del sábado tampoco apareció en esta tanda, y eso no se
> atribuye al cambio. Con la tasa de adiciones medida, cinco
> repeticiones limpias seguidas ocurren por azar cerca de la mitad
> de las veces. El cambio afectó el formato de la cita, no el
> contenido de la respuesta.

### Qué deja esto para el trabajo siguiente

Esta iteración es la demostración más concreta de por qué el proyecto
necesita entregarle el texto de la norma junto con la pregunta. La
cita a nivel de inciso depende del documento vigente, y el modelo no
lo tiene. Con el texto del artículo a la vista, contar los incisos es
trivial.

---

## Qué muestran las diez mediciones

El prompt `responder_consulta` pasó por cinco versiones y se midió
diez veces. Contando cuántas respuestas agregaron contenido que la
pregunta no pedía.

```text
tanda 2   versión original                5 de 5
tanda 3   tras las iteraciones 1 y 2      0 de 5
tanda 4   misma versión                   0 de 5
tanda 5   misma versión                   0 de 5
tanda 6   misma versión                   3 de 5
tanda 7   tras la iteración 5             1 de 5
tanda 8   tras la iteración 6             3 de 5
tanda 9   tras la iteración 7             4 de 5
tanda 10  tras la iteración 8             0 de 5
```

Las tandas 3 a 6 corresponden al **mismo prompt, sin un solo
cambio**, y van de 0 a 3 adiciones de cinco. Esa variación es tan
grande como cualquier diferencia entre versiones distintas.

Agrupando las 40 respuestas posteriores a la iteración 2.

```text
                        versión original    iteraciones 1 a 8
                        5 respuestas        40 respuestas

agregó contenido        5    (100 %)        11   (28 %)
error de contenido      2    (40 %)         1    (3 %)
```

> [!IMPORTANT]
> Las iteraciones 1 y 2 produjeron una mejora grande y sostenida.
> Las iteraciones 5, 6 y 7 no se distinguen entre sí con muestras
> de cinco repeticiones. Separar un 20 % de un 40 % con confianza
> exigiría decenas de repeticiones por versión, es decir cientos de
> llamadas a la API.
>
> Se deja de iterar aquí. No porque el resultado sea perfecto, sino
> porque la medición disponible ya no permite decidir si un cambio
> mejora o empeora.

### Qué queda sin resolver, con precisión

De las 40 respuestas, cinco agregaron algo que la fuente citada no
respalda. Y siempre es el mismo dato.

```text
reglas regionales        están en el artículo 67, la cita las
                         cubre
relleno sin contenido    no afirma nada que respaldar
regla del sábado         está en el artículo 69, la cita dice 67
```

No es inestabilidad general ni invención de datos falsos. Es un
hecho puntual que el modelo atribuye al artículo equivocado, y eso
rompe la verificabilidad de la cita, que es justamente la razón de
existir del campo `fuente`.

---

## Verificaciones

Comprobaciones sobre el banco ya ajustado. No modifican los
prompts, solo confirman que decisiones anteriores funcionan.

### Salida sin fuente identificable

La opción `no identificado`, incorporada en la iteración 1, nunca
se había activado, porque la pregunta de ejemplo siempre tiene
respaldo en la ley.

Para provocar el caso se cambió de forma temporal la pregunta de
ejemplo por una que el Código del Trabajo no regula, un permiso por
mudanza de casa.

```text
fuente = no identificado    5 de 5 repeticiones
```

Ninguna repetición inventó un artículo. Las respuestas además
señalaron correctamente que ese permiso, cuando existe, proviene de
un acuerdo entre las partes y no de la ley.

La pregunta original se restituyó al terminar la comprobación.

### Continuidad ante un error del servicio

Durante esa misma corrida la API respondió con un error 429 por
límite de cuota, en la tercera repetición de `revisar_clausula`.

```text
intento 3 falló. El servicio respondió 429
intento 4    materia = jornada_semanal, valor = 48
intento 5    materia = jornada_semanal, valor = 48
4/5 respuestas válidas
```

El script no se interrumpió. Contó esa repetición como fallida,
continuó con las siguientes, terminó los prompts restantes y guardó
el registro.

Esto responde a una decisión de diseño. El bloque `try` envuelve el
intento completo y no solo la interpretación del JSON, de modo que
una caída del servicio cuenta como intento fallido en vez de cortar
la medición y perder lo ya medido.

La pausa entre llamadas se subió de 3 a 5 segundos. Con cuatro
prompts y cinco repeticiones son veinte peticiones, y el plan
gratuito del modelo permite quince por minuto.

---

## Limitación conocida

Los ajustes anteriores redujeron los errores de forma medible, pero
no los eliminan por diseño. El modelo no consulta la ley, la
reconstruye desde su entrenamiento, de modo que puede equivocarse
también dentro de la respuesta a la pregunta.

> [!WARNING]
> La prueba de consistencia no detectaría ese caso. Verifica que
> estén las claves esperadas, no que lo que dicen sea cierto. Una
> respuesta equivocada con la estructura correcta cuenta como
> válida.

La corrección de fondo consiste en entregarle el texto del artículo
junto con la pregunta, de modo que responda solo desde esa fuente
en vez de desde su memoria. Queda anotado como trabajo siguiente.

Eso resolvería además el defecto identificado arriba. Si el modelo
recibe el texto del artículo 67 y se le pide responder solo desde
ahí, la regla del sábado no puede aparecer, porque no está en ese
texto.

Por la misma razón, los prompts `revisar_clausula` y
`listar_materias_contrato` se diseñaron para que el modelo describa
lo que el texto establece y no opine sobre su legalidad. Esa
comparación la hace el programa contra el texto legal, donde no
puede inventarse.

### Vocabulario abierto en revisar_clausula

Un segundo límite, encontrado al probar `revisar_clausula` con una
cláusula distinta a la del ejemplo. El campo `materia` admite
cualquier etiqueta, y el modelo devolvió `funciones`, que no estaba
prevista en ninguna parte.

La etiqueta describe bien la cláusula, pero el programa no puede
comparar contra una tabla de límites legales si los nombres los
elige el modelo en cada llamada. El prompt
`listar_materias_contrato` ya resolvió esto en la iteración 4, con
un vocabulario cerrado de diez etiquetas derivadas del artículo 10.

`revisar_clausula` necesita lo mismo, pero su vocabulario tiene que
derivarse de la tabla de límites legales que el programa vaya a
verificar, y esa tabla todavía no existe. Queda anotado como
dependencia de ese trabajo.