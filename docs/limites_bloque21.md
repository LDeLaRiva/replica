# Límites y métricas, Bloque 21

Agente con dos herramientas propias, `src/agente_con_herramientas.py`.
Siete corridas del 6 de noviembre de 2026 sobre los mismos cuatro
casos de verificación. Modelo `gemini-3.5-flash-lite`, sin cambios en
el `.env` durante toda la serie.

Seis corridas completaron los cuatro casos. Una murió en el tercero
por una caída del proveedor.

---

## 1. El comportamiento del agente no es reproducible

Es el hallazgo metodológico de la serie, y condiciona todo lo demás.

Dos corridas consecutivas, **con el archivo idéntico y el mismo
modelo**, separadas por minutos, dieron resultados distintos. Una
eligió bien en 3 de 4 casos y la siguiente en 4 de 4.

Se verificó antes de concluirlo. Se comparó la superficie que el
modelo lee para decidir, es decir los nombres de las dos funciones,
sus docstrings, los nombres y tipos de sus parámetros y el prompt del
sistema. El hash de esa superficie fue idéntico en las dos corridas.

**Consecuencia práctica.** Una sola corrida no prueba que un agente
elija bien. El nombre de la herramienta que emite es texto generado
token por token, igual que cualquier respuesta, y el módulo no fija
`temperature`. Verificar un agente exige varias corridas y reportar
una proporción, no un resultado.

Eso distingue esta verificación de la del Bloque 19. Allá, con la
clasificación reemplazada por un mock, la prueba da el mismo
resultado siempre. En esta verificación no.

---

## 2. El fuero del artículo 66, texto literal contra resumen

Es el dato más fuerte del registro, porque es el mismo hecho medido
en tres condiciones distintas.

**El dato.** El artículo 66 concede fuero laboral de un mes al
trabajador del inciso primero. El inciso primero cubre dos casos, la
muerte de un hijo y la del cónyuge o conviviente civil. Los otros dos
casos del artículo, hijo en gestación y hermano, padre o madre, no dan
fuero.

**Condición 1, el modelo reconstruyendo de memoria.** Seis o más
corridas por la ruta de consulta del Bloque 19. Nunca entregó el
artículo y el inciso correctos en la misma respuesta.

**Condición 2, un resumen del artículo redactado para el proyecto,
dentro de la herramienta.** Una corrida. El resumen decía, fiel al
artículo, "el trabajador del inciso primero goza de fuero". El
modelo atribuyó el fuero solo a la muerte del hijo y dejó al
cónyuge afuera.

La causa no fue el modelo. Un resumen entrega los cuatro casos como
lista plana y destruye la estructura de incisos a la que el artículo
se remite. La remisión quedó sin referente y el modelo la resolvió
suponiendo.

**Condición 3, texto literal con la remisión resuelta entre
corchetes.** Cinco corridas consecutivas, las cinco correctas. El
modelo nombró hijo y cónyuge, y además lo escribió en lenguaje llano,
sin usar la expresión "el trabajador del inciso primero", que no
significa nada para quien no tiene el artículo delante.

**Lo que además apareció** en esas cinco corridas y que el resumen
redactado no había entregado nunca.

- que el permiso corre desde el día del fallecimiento
- que en defunción fetal corre desde que se acredita la muerte
- que el fuero, en contrato a plazo fijo u obra, se corta cuando
  termina el contrato
El resumen omitía cuatro datos de un solo artículo.
El del fuero fue el único que se descubrió, porque fue el único que
produjo una afirmación verificable.

---

## 3. La frase más inestable del corpus

Cinco corridas mencionaron la cláusula del fuero en contratos a plazo
fijo. Salieron cinco redacciones distintas y dos correctas.

El Código dice "se mantendrá vigente por el mismo periodo o hasta el
término de dicho contrato".

| corrida | lo que escribió | veredicto |
|---|---|---|
| 3 | el fuero dura ese mes o hasta el término del contrato | correcto |
| 4 | hasta el término del contrato si este es menor a un mes | condición inventada |
| 5 | no la mencionó | omitida |
| 6 | se mantiene hasta el término del contrato si este es a plazo fijo o por obra o servicio | omite el tope del mes |
| 7 | el fuero dura un mes o hasta el término del contrato | correcto |

La de la corrida 4 describía el efecto correcto de la norma, pero
agregaba una condición que el texto no establece. La de la corrida 6
deja entender que el fuero dura todo el contrato, cuando el tope es un
mes.

**Lo que esto identifica.** No es que el modelo reformule plazos en
general. Es esta frase, y la razón es concreta. Es la única del corpus
que ofrece dos plazos alternativos unidos por un "o". Las frases con
un plazo único salieron exactas en las siete corridas.

---

## 4. Un nombre de herramienta inventado

Una corrida de siete. El agente invocó
`buscar_articulo_del_consulta`, que no existe.

El nombre es la mezcla de la herramienta real,
`buscar_articulo_del_codigo`, con el nombre de su único parámetro,
`consulta`. Las dos palabras están en el mismo campo de significado y
las dos viven en el esquema que el modelo recibe.

LangChain devolvió como observación "is not a valid tool, try one of
[...]" con la lista de las dos herramientas reales. El agente leyó esa
observación, **se corrigió en la vuelta siguiente**, invocó la
herramienta correcta y la respuesta final salió completa y sin
errores.

La corrida siguiente, con el archivo idéntico, no repitió el error.

**Esto no se corrigió.** Es la conducta que el Bloque 21 anuncia en su
primera lección cuando dice que "el modelo puede elegir mal una
herramienta, o interpretar mal un resultado". El ciclo razonar, actuar
y observar hizo exactamente lo que tiene que hacer, que es recuperarse
de un error suyo usando la observación.

Si reapareciera, el primer ajuste a probar sería renombrar el
parámetro de `consulta` a algo que no se pueda confundir con el nombre
de la herramienta. Son dos líneas. No se hizo porque es una ocurrencia
en siete corridas y reaccionar a un solo evento introduce regresiones.

---

## 5. Los cambios al prompt del sistema

Dos en un día. El primero produjo el efecto contrario al buscado
y queda registrado.

**Primer intento.** "No transcribas el artículo completo, responde lo
que la persona preguntó."

A la entrada "¿en qué artículo está el permiso por fallecimiento?" el
modelo respondió una sola frase, el número del artículo y nada más,
teniendo los cuatro plazos y el fuero a la vista. Obedeció al pie de
la letra. Una pregunta de una sola parte invita a una respuesta de una
línea.

En la misma corrida, el caso cuya pregunta tenía dos partes sí
respondió con sustancia. La diferencia confirma la causa.

**Segundo intento.** "Cuando respondas sobre un artículo, di cuál es y
qué establece en lo que viene al caso, con los plazos y las cifras que
trae. No transcribas el artículo completo."

Pide las dos cosas y acota el alcance en vez de prohibir el contenido.
Las cinco corridas siguientes entregaron los cuatro plazos completos.

**Lo que no se pidió.** Que explique el artículo en palabras simples.
Esa instrucción equivale a reescribirlo, que es el mismo paso que
produjo el error del fuero cuando el resumen estaba en el corpus.

La distinción está en la permanencia. Una paráfrasis por respuesta
queda visible en la traza y no se acumula. Un resumen fijado en el
corpus es invisible y se reutiliza en todas las consultas.

---

## 6. Qué partes de la observación suelta el modelo

El modelo no reproduce la observación completa. Suelta partes, y de
forma despareja entre casos.

**El ancla del artículo.** La herramienta de cálculo devuelve como
primera frase que la indemnización la regula el artículo 163. En la
consulta de jornada parcial, una corrida la omitió y encuadró la
respuesta en el artículo 40 bis D, que solo modifica qué se entiende
por última remuneración. La corrida siguiente la conservó. Son
dos corridas con un resultado cada una.

Antes de ese orden, con el 40 bis D nombrado primero, el modelo había
escrito que la indemnización "se rige por el artículo 40 bis D", que
es falso. Poner el 163 adelante eliminó la afirmación falsa pero no
impidió la omisión.

**Los supuestos del cálculo.** Conserva siempre el del artículo 161,
que es el que decide si la indemnización procede. Suelta los más
estrechos, obra o faena, casa particular, liquidación concursal y
pacto superior, y lo hace de forma despareja. En la consulta de
jornada parcial los conservó completos. En la que encadena las dos
herramientas los soltó.

**Lo que sí se corrigió desde la herramienta.** La cláusula del pacto
superior pasó de decir solo que no se aplicaba a decir qué ocurre en
ese caso, "porque en ese caso se paga lo pactado". Con esa redacción
llegó completa a la respuesta.

---

## 7. Caída del proveedor

Una corrida de siete murió completa en el tercer caso.

```
503 UNAVAILABLE
This model is currently experiencing high demand.
Spikes in demand are usually temporary.
```

No fue agotamiento de cuota, que se reporta como 429
`RESOURCE_EXHAUSTED`, ni la credencial, ni el código. Fue saturación
momentánea del servicio.

El cuarto caso no llegó a ejecutarse, y las llamadas ya consumidas en
los dos primeros quedaron sin verificación completa.

A partir de eso se incorporó, alrededor del bucle de casos, el patrón
de manejo de error del Bloque 20. Un reintento único a los veinte
segundos y un `try/except` que registra el traceback completo con
`logger.exception` y continúa con el caso siguiente. El cierre cuenta
sobre los casos que de verdad se ejecutaron e informa aparte los que
no.

Esto no lo exige la actividad del Bloque 21, que pide manejo de error
dentro de la herramienta. Se incorporó porque un fallo transitorio del
proveedor interrumpía la verificación entera.

---

## 8. Elección de herramienta

Un solo nombre inválido en siete corridas. En todos los demás casos
de todas las corridas, el agente invocó exactamente las herramientas
esperadas.

Los cuatro casos cubren una herramienta sola, la otra sola, ninguna, y
las dos encadenadas.

**Un dato aparte sobre el docstring.** En la consulta de jornada
parcial el agente extrajo la jornada del texto corrido y pasó
`horas_semanales=20`. En la que no menciona jornada omitió el
parámetro en lugar de inventar un valor. El docstring indica dejarlo
en cero si la persona no la menciona, y el modelo lo cumplió en las
dos direcciones, en todas las corridas.

---

## 9. Lo que la verificación automática no comprueba

La comparación del módulo contrasta **nombres de herramientas**, no
argumentos. La consulta de jornada parcial pasaría igual si el agente
llamara al cálculo olvidando `horas_semanales`, y la respuesta sería
distinta y peor.

Lo que confirma que el argumento llegó es la traza, donde sale tal
cual lo armó el modelo. Esa parte de la verificación es manual y no se
puede automatizar comparando nombres.
