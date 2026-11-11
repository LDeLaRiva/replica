# Límites de autonomía, agente de consultas laborales

El agente vive en `src/agente_con_memoria.py` y tiene tres
herramientas. Dos leen y calculan. La tercera notifica a una persona
que su contrato termina, y esa no se puede deshacer.

Este documento dice qué puede hacer el agente sin que nadie
intervenga, qué no, qué se revisa después, y qué hacer cuando algo
sale distinto de lo esperado.

Todo lo que dice está medido sobre corridas reales. Las mediciones
están al final, con la fecha y el archivo donde quedaron.

## Herramientas y nivel de riesgo

- `buscar_articulo_del_codigo_del_trabajo`: bajo (solo lee el texto
  de los artículos desde un archivo del proyecto, no modifica nada;
  el peor resultado es entregar un artículo que no viene al caso)
- `calcular_indemnizacion_por_anos_de_servicio`: bajo (solo calcula
  en memoria, no ejecuta ninguna acción externa; el peor resultado
  es un monto equivocado dentro de una respuesta)
- `enviar_aviso_de_termino_de_contrato`: alto (notifica a una
  persona el término de su contrato y no se puede retirar; cuando la
  causal es la del inciso primero del artículo 161, el artículo 169
  considera ese aviso una oferta irrevocable de pago de la
  indemnización; requiere aprobación humana)
### Por qué ninguna quedó en riesgo medio

El riesgo medio es la escritura reversible, algo que se puede
corregir después aunque cueste tiempo. Ninguna de las tres escribe
nada reversible. Las dos primeras no escriben, y la tercera escribe
algo que no se corrige.

No se forzó una herramienta intermedia para llenar la categoría.
Clasificar de más tiene el mismo problema que pedir aprobación de
más, que la clasificación deja de servir para priorizar.

## Herramientas que requieren aprobación humana

- `enviar_aviso_de_termino_de_contrato`: es la única. Una vez
  enviado el aviso, el trabajador queda notificado y la empresa
  queda obligada al pago que el aviso indica. No hay forma de
  retirarlo. Sin un humano que lo autorice, la decisión de notificar
  un despido quedaría en el razonamiento del modelo.
Las otras dos se ejecutan directamente, y la razón es el riesgo de
cada una en particular y no una regla pareja.

`buscar_articulo_del_codigo_del_trabajo` lee un archivo del
repositorio. Si el modelo la invoca cuando no corresponde, entrega
un artículo que no venía al caso y la respuesta queda larga o
confusa. No cambia nada fuera del programa.

`calcular_indemnizacion_por_anos_de_servicio` multiplica en memoria
y devuelve un texto. Si el modelo le pasa datos equivocados, el
monto sale equivocado dentro de una respuesta que la persona
todavía puede cuestionar. Tampoco cambia nada fuera del programa.

Pedir aprobación también en esas dos tendría un costo concreto. En
una corrida de seis turnos se habrían pedido ocho aprobaciones.
Quien aprueba ocho veces por corrida deja de leer lo que aprueba, y
cuando llegue la novena, que es la del despido, la va a contestar
por costumbre. La fricción se reserva para donde hace falta.

### Cómo está implementada

`esperar_aprobacion` vive en `src/soporte_supervision.py`. Muestra
qué se va a hacer y por qué no se puede deshacer, espera la
respuesta por consola, y devuelve verdadero solo si la respuesta es
la letra `s`.

Tiene un límite de tiempo de trescientos segundos. Si nadie
responde, devuelve falso y la acción no se ejecuta. Para una acción
irreversible, no aprobado es la opción segura, y un vencimiento que
ejecutara la acción anularía el sentido de pedir supervisión.

La decisión se registra siempre, apruebe o rechace. Sin el registro
del rechazo no habría forma de responder después por qué un aviso no
se envió.

Al revisar el código con `findstr /N "esperar_aprobacion("
src\agente_con_memoria.py` aparece **una** línea, la llamada dentro
de la herramienta de riesgo alto. La definición no aparece porque
vive en el módulo de soporte, siguiendo la retroalimentación del
Gate 1 que pidió desacoplar las funciones auxiliares.

## Revisión de trazas

Cada interacción se escribe como una línea en
`src/trazas_agente.jsonl`. Cada línea guarda qué se preguntó, qué
herramientas se usaron y con qué argumentos, si un humano autorizó
las acciones de riesgo alto, y qué se respondió.

- Frecuencia: una muestra de cinco interacciones por semana, más
  **todas** las líneas donde aparezca
  `enviar_aviso_de_termino_de_contrato`. Esas no se revisan por
  muestra, se revisan todas, porque cada una corresponde a una
  persona notificada.
- Qué se busca: los tres patrones de abajo, en este orden.
### 1. La misma herramienta invocada varias veces seguidas

En este agente sería `buscar_articulo_del_codigo_del_trabajo`
llamada dos veces consecutivas con consultas parecidas. Significa
que el corpus no resolvió la pregunta y el modelo volvió a intentar
con otras palabras.

Qué indica. O falta un artículo en el corpus, o las claves de
búsqueda de ese artículo no cubren cómo la gente pregunta por él.

No se ha observado hasta ahora. En las doce interacciones medidas,
ninguna herramienta se repitió de forma consecutiva.

### 2. Una herramienta de riesgo alto sin registro de aprobación

En este archivo de trazas sería una línea cuyo campo `acciones`
contenga `enviar_aviso_de_termino_de_contrato` y cuyo campo
`aprobaciones` esté vacío.

Qué indica. Que el flujo de supervisión dejó de funcionar. Es el
patrón más grave de los tres, porque significaría que se notificó a
alguien sin que nadie lo autorizara.

No se ha observado. En las dos corridas medidas, las dos veces que
se invocó la herramienta quedó su decisión registrada, una aprobada
y una rechazada.

### Los comandos de revisión

Son tres. A la izquierda la forma de terminal Unix, y a la derecha
la de PowerShell, que es donde se desarrolla este proyecto.

Que la aprobación esté en el código.

```
grep -n "esperar_aprobacion(" src/agente_con_memoria.py
findstr /N "esperar_aprobacion(" src\agente_con_memoria.py
```

Devuelve una línea y no dos, porque la definición de
`esperar_aprobacion` vive en el módulo de soporte.

Que el archivo de trazas no esté vacío.

```
wc -l src/trazas_agente.jsonl
(Get-Content src\trazas_agente.jsonl).Count
```

Que la herramienta de riesgo alto haya quedado registrada con su
decisión.

```
grep -c '"aprobado"' src/trazas_agente.jsonl
(Select-String -Path src\trazas_agente.jsonl -Pattern '"aprobado"').Count
```

### 3. Una respuesta final que no coincide con ninguna observación

**Este patrón sí se observó, y es el hallazgo principal de esta
revisión.**

En la corrida del 10 de noviembre, sesión `consulta_002`, el agente
cerró su respuesta así.

> Total general: Sumando ambos conceptos, el total a pagar asciende
> a $7.680.000.

Ninguna herramienta devolvió ese número. Se revisaron las dos
observaciones de esa interacción. El cálculo devolvió 7.040.000 por
años de servicio, y de paso repitió el sueldo de 640.000. La
búsqueda devolvió el texto del artículo 162, que dice que la
sustitutiva del aviso previo equivale a la última remuneración
mensual, sin dar ninguna cifra. El total de 7.680.000 no aparece en
ninguna de las dos. El modelo tomó las dos cifras que tenía a la
vista, las sumó, y presentó el resultado como un total.

Por qué importa. El proyecto tiene como regla que los cálculos se
hagan en Python y no en el modelo, justamente porque un número que
el modelo produjo no se puede contrastar contra nada. En una consulta
laboral, ese total es la cifra que la persona se va a llevar.

Frecuencia medida. Una vez en doce interacciones. En la segunda
corrida, con la misma pregunta, no volvió a ocurrir.

Qué corregir. El prompt del sistema. Hoy dice que las cifras que
entregue una herramienta se repitan exactamente como llegaron, pero
no dice nada sobre no operar con ellas. La corrección es agregar que
no sume, reste ni combine cifras de distintas herramientas, y que si
hace falta un total lo pida a una herramienta.

Esa corrección no se aplicó todavía. Queda registrada aquí y se
aplica en el bloque siguiente, para no cambiar el prompt en la misma
entrega en que se midió su efecto.

## Qué hacer ante un comportamiento inesperado

Pasos concretos y en este orden.

**1. Encontrar la interacción en la traza.**

```
Select-String -Path src\trazas_agente.jsonl -Pattern "<texto de la pregunta>"
```

Sin la línea de la traza no se sabe qué pasó, y una corrección
basada en lo que se recuerda de la consola corrige lo que no estaba
roto.

**2. Clasificar la falla en uno de tres casos**, comparando el campo
`acciones` con el campo `respuesta_final`.

- Eligió mal la herramienta. Invocó una que no correspondía, o no
  invocó ninguna cuando hacía falta.
- El dato que recibió estaba mal. La herramienta se invocó bien y
  devolvió algo equivocado o incompleto.
- La redacción agregó algo. Las herramientas respondieron bien y la
  respuesta final afirma cosas que ninguna devolvió.

**3. Corregir según el caso, y solo eso.**

- Si eligió mal la herramienta, ajustar el docstring de esa
  herramienta en `src/agente_con_memoria.py`, que es lo que el
  modelo lee para decidir. Decir con más precisión cuándo usarla y
  cuándo no.
- Si el dato estaba mal y es legal, revisar el artículo en
  `src/soporte_corpus_legal.py` contra el texto de BCN. Si el
  artículo no está en el corpus, agregarlo desde BCN, nunca
  escribirlo de memoria.
- Si el dato estaba mal y es un cálculo, revisar
  `calcular_indemnizacion_por_anos_de_servicio` y agregar el caso a
  las pruebas antes de corregirlo.
- Si la redacción agregó algo, revisar el prompt del sistema. Es el
  caso del patrón 3 de arriba.

**4. Si la falla fue en la herramienta de riesgo alto, sacarla de
circulación mientras se corrige.** No se deja andando una
herramienta irreversible que se comportó de forma inesperada. Se
comenta su línea en la lista de herramientas.

```python
herramientas = [
    buscar_articulo,
    calcular_indemnizacion,
    # enviar_aviso_de_termino,   desactivada, ver este documento
]
```

El agente sigue respondiendo consultas y deja de poder notificar.

**5. Volver a correr las pruebas.**

```
python src\agente_con_memoria.py
```

El bloque de pruebas cubre los dos turnos en una sesión, las dos
sesiones que no se mezclan, y los dos niveles de riesgo. Si la
corrección rompió otra cosa, aparece ahí.

**6. Registrar el hallazgo en este documento**, con la fecha, la
sesión, qué se observó y qué se cambió. Un hallazgo que no queda
escrito se vuelve a encontrar desde cero.

## Lo que este agente no tiene

Esta sección existe porque un documento de límites que describe el
agente que uno quiso construir, en vez del que construyó, no sirve
para confiar en él.

**La separación de acceso no está implementada.** El agente atiende
a dos partes, el área de recursos humanos de una empresa y los
trabajadores que consulten por su cuenta. El envío del aviso
corresponde solo a la primera. No hay inicio de sesión ni ninguna
comprobación de quién pregunta, y hoy lo único que cumple esa
función es que una persona tenga que aprobar el envío. Un trabajador
podría escribir que es de recursos humanos y el agente intentaría el
envío igual.

**El envío está simulado.** La herramienta devuelve el texto de un
aviso enviado, pero el proyecto no se conecta a ningún servicio de
correo ni a la Inspección del Trabajo. Lo que se probó es el
circuito de supervisión completo, no la entrega.

**El registro de aprobaciones se pierde al terminar.** Vive en una
lista en memoria. Lo que sí queda en disco es el campo
`aprobaciones` de cada línea de la traza, que es donde hay que
buscarlo después.

**El tope del artículo 172 no se aplica.** El inciso tercero limita
a noventa unidades de fomento la remuneración con que se calcula la
indemnización. El cálculo no tiene el valor de la UF, así que no
puede aplicarlo. Lo advierte en su respuesta, pero para un sueldo
que supere ese tope el monto que entrega es mayor que el legal.

**Una espera vencida deja un hilo bloqueado.** `esperar_aprobacion`
espera la respuesta en un hilo aparte. Si la espera vence, ese hilo
queda detenido leyendo el teclado. Con dos aprobaciones en la misma
ejecución habría dos hilos leyendo la misma entrada y cuál recibe el
texto no está definido. En este proyecto no ocurre, porque cada
aprobación se contesta antes de seguir, pero un servicio que atienda
varias a la vez necesitaría otra cosa.

## Las mediciones

Corridas del 10 de noviembre de 2026, con el agente completo y el
modelo real. Dos corridas de seis interacciones cada una, una
aprobando el envío y otra rechazándolo.

```
interacciones registradas            12
líneas con JSON inválido              0
líneas con claves faltantes           0

decisiones de aprobación              2
    aprobada                          1    00:52:38
    rechazada                         1    00:53:18

veces que se pidió la aprobación      1 por corrida
```

Después del rechazo el modelo no volvió a intentar el envío, de modo
que no se observó aprobación pedida dos veces para la misma acción.

**Artículos citados en las respuestas finales.** Se revisaron las
doce respuestas buscando números de artículo que no vinieran ni del
corpus ni de lo que devolvió una herramienta.

```
citados      163, 172, 162, 161, 168
fuera del corpus o de las herramientas      ninguno
```

En una corrida anterior del mismo día, el agente había nombrado los
artículos 159 y 73, que ese día no estaban en el corpus, y había
descrito mal el número 6 del artículo 159. Después de agregar al
párrafo del cálculo el tope del artículo 172 y el recargo del
artículo 168, las doce respuestas medidas se mantuvieron dentro del
corpus.

Eso no prueba que no vuelva a ocurrir. Lo que muestra es dónde
ocurre, que es en los artículos que el corpus no incluye, y es la
razón por la que el corpus existe.

Esa observación fue la que llevó a cargar el artículo 159, y con él
el 172, al día siguiente. El corpus pasó de nueve artículos a once
en un commit aparte, porque las mediciones de esta página se
hicieron sobre el de nueve.

**Patrones sospechosos encontrados.**

```
patrón 1, herramienta repetida seguida          0 de 12
patrón 2, riesgo alto sin aprobación            0 de 2
patrón 3, respuesta sin respaldo                1 de 12
```

El archivo con los datos es `src/trazas_agente.jsonl`.
