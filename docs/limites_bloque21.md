bloque21 · MD
# Registro de corridas, Bloque 21

6 de noviembre de 2026. Agente con dos herramientas propias,
`src/agente_con_herramientas.py`. Cinco corridas del mismo conjunto
de cuatro casos.

---

## El hallazgo principal, el fuero del artículo 66

Es el dato más fuerte del registro, porque es el mismo hecho medido
antes y después de un solo cambio.

**El dato.** El artículo 66 concede fuero laboral de un mes al
trabajador del inciso primero. El inciso primero son dos casos, la
muerte de un hijo y la del cónyuge o conviviente civil. Los otros
dos casos del artículo, hijo en gestación y hermano, padre o madre,
no dan fuero.

**Con el modelo reconstruyendo de memoria.** Seis o más corridas en
el Bloque 19, por la ruta de consulta. Nunca entregó el artículo y
el inciso correctos en la misma respuesta. El fuero osciló entre
quedarse corto y pasarse.

**Con un resumen propio del artículo en la herramienta.** Una
corrida. El resumen decía, fiel al artículo, "el trabajador del
inciso primero goza de fuero". El modelo lo atribuyó solo a la
muerte del hijo y dejó al cónyuge afuera.

La causa no fue el modelo. Fue que un resumen entrega los cuatro
casos como lista plana y destruye la estructura de incisos a la que
el artículo se refiere. La referencia quedó apuntando a nada y el
modelo la resolvió suponiendo.

**Con el texto literal y la referencia resuelta entre corchetes.**
Tres corridas consecutivas, las tres correctas. El modelo nombró
hijo y cónyuge, y además lo escribió en lenguaje llano, sin usar la
frase "el trabajador del inciso primero", que no significa nada
para quien no tiene el artículo delante.

**Lo que además apareció** en esas tres corridas y que el resumen
propio nunca había entregado.

- que el permiso corre desde el día del fallecimiento
- que en defunción fetal corre desde que se acredita la muerte
- que el fuero, en contrato a plazo fijo u obra, se corta cuando
  termina el contrato
El resumen propio se había comido cuatro datos de un solo artículo.
El del fuero fue el único que se descubrió, porque fue el único que
produjo una afirmación verificable.

---

## Conductas del modelo observadas

Ninguna de las tres produjo una cifra ni un plazo equivocado.

### Reestructura plazos

Una corrida de cinco. Convirtió "un mes o hasta el término de dicho
contrato" en "hasta el término del contrato si este es menor a un
mes".

El efecto que describió coincide con el de la norma, pero esa
condición no está en el texto. El modelo dedujo y lo escribió como
si la ley lo dijera.

Apareció en una sola corrida. En la anterior enunció la alternativa
correctamente y en la siguiente la omitió entera. No es estable, y
por eso mismo puede reaparecer.

### Omite los supuestos estrechos del cálculo

De forma despareja. En la consulta de part time los conservó
completos. En la que encadena las dos herramientas los soltó.

Conserva siempre el del artículo 161, que es el que decide si la
indemnización procede. Los que suelta son obra o faena, casa
particular, liquidación concursal y pacto superior.

### Suelta frases enteras de la observación

La herramienta de cálculo devuelve como primera frase que la
indemnización la regula el artículo 163. En la consulta de part
time el modelo omitió esa frase y encuadró la respuesta en el
artículo 40 bis D, que solo cambia qué se entiende por última
remuneración.

Antes de ese cambio, con el 40 bis D nombrado primero, el modelo
había escrito que la indemnización "se rige por el artículo 40 bis
D". Poner el 163 adelante corrigió la afirmación falsa, pero no
impidió la omisión.

---

## Los cambios al prompt del sistema

Dos en un día, y conviene registrar el primero porque salió al
revés de lo buscado.

**Primer intento.** "No transcribas el artículo completo, responde
lo que la persona preguntó."

A la entrada "¿en qué artículo está el permiso por fallecimiento?"
el modelo respondió una sola frase, el número del artículo y nada
más, teniendo los cuatro plazos y el fuero a la vista. Obedeció al
pie de la letra. Una pregunta de una sola parte invita a una
respuesta de una línea.

En la misma corrida, el caso cuya pregunta tenía dos partes sí
respondió con sustancia. La diferencia confirma la causa.

**Segundo intento.** "Cuando respondas sobre un artículo, di cuál
es y qué establece en lo que viene al caso, con los plazos y las
cifras que trae. No transcribas el artículo completo."

Pide las dos cosas y acota el alcance en vez de prohibir el
contenido. Las tres corridas siguientes entregaron los cuatro
plazos completos.

**Lo que no se pidió.** Que explique el artículo en palabras
simples. Eso invita a reescribirlo completo con otras palabras, que
es el mismo paso que produjo el error del fuero cuando lo hicimos
nosotras en el corpus.

La distinción que importa. Una paráfrasis por respuesta es
revisable en la traza y no se acumula. Un resumen congelado en el
corpus es invisible y se reutiliza para siempre.

---

## Caída del proveedor

Una corrida de cinco murió completa en el tercer caso.

```
503 UNAVAILABLE
This model is currently experiencing high demand.
Spikes in demand are usually temporary.
```

No fue cuota, que llegaría como 429 `RESOURCE_EXHAUSTED`, ni la
clave, ni el código. Fue el servidor del proveedor ocupado.

El cuarto caso no llegó a correr, y las llamadas ya gastadas en los
dos primeros quedaron sin verificación completa.

A partir de eso se agregó, alrededor del bucle de casos, el patrón
de manejo de error del Bloque 20. Un reintento único a los veinte
segundos y un `try/except` que registra el traceback completo y
sigue con el caso siguiente. El cierre cuenta sobre los casos que
de verdad corrieron e informa aparte los que no.

Esto no lo pide la actividad del Bloque 21, que pide manejo de
error dentro de la herramienta. Se agregó porque un fallo
transitorio del proveedor botaba la verificación entera.

---

## Elección de herramienta

Las cinco corridas, 4 de 4 en las cuatro que completaron, y 2 de 2
en la que cayó por el 503. El agente no eligió mal ninguna vez.

Los cuatro casos cubren una herramienta sola, la otra sola, ninguna
y las dos encadenadas.

**Un dato aparte del docstring.** En la consulta de part time el
agente extrajo la jornada del texto corrido y pasó
`horas_semanales=20`. En la que no menciona jornada omitió el
parámetro en lugar de inventar un valor. El docstring dice que lo
deje en cero si la persona no la menciona, y lo cumplió en las dos
direcciones.
