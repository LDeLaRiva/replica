# Ajustes al banco de prompts

> Registro de las mediciones de consistencia del banco y de las
> correcciones aplicadas a los prompts. Cada iteración deja lo que
> se observó, el cambio hecho y el resultado de volver a medir.
>
> **Proyecto** · Miniaplicación de consultas laborales
> **Modelo** · gemini-3.5-flash-lite
> **Última medición** · 22 de octubre de 2026

---

## Mediciones

Todas las mediciones se hicieron el 22 de octubre de 2026.

| # | Qué se midió | responder_consulta | extraer_datos_contrato | revisar_clausula | listar_materias_contrato |
|---|---|---|---|---|---|
| 1 | línea base, 3 repeticiones | 3/3 | 3/3 | 3/3 | — |
| 2 | línea base, 5 repeticiones | 5/5 | 5/5 | 5/5 | — |
| 3 | después de las iteraciones 1 y 2 | 5/5 | 5/5 | 5/5 | — |
| 4 | confirmación de la anterior | 5/5 | 5/5 | 5/5 | — |
| 5 | después de la iteración 3 | 5/5 | 5/5 | 5/5 | 5/5 |
| 6 | después de la iteración 4 | 5/5 | 5/5 | 5/5 | 5/5 |
| 7 | después de la iteración 5 | 5/5 | 5/5 | 5/5 | 5/5 |

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

Por la misma razón, los prompts `revisar_clausula` y
`listar_materias_contrato` se diseñaron para que el modelo describa
lo que el texto establece y no opine sobre su legalidad. Esa
comparación la hace el programa contra el texto legal, donde no
puede inventarse.