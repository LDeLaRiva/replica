# Límites y métricas, Bloque 22

Agente con memoria entre interacciones, `src/agente_con_memoria.py`.
Tres corridas del 7 de noviembre de 2026 sobre las mismas dos
pruebas, de cuatro turnos cada una. Modelo `gemini-3.5-flash-lite`,
sin cambios en el `.env` durante la serie.

Las tres corridas completaron los cuatro turnos. No hubo caídas del
proveedor, ni errores de validación de Pydantic, ni nombres de
herramienta inválidos.

El archivo no fue idéntico en las tres. Las dos primeras corrieron
con el prompt del Bloque 21 y la tercera con una frase modificada,
registrada en la sección 6. Donde eso importa para leer un número,
está dicho.

---

## 1. La memoria propaga los errores hacia adelante

Es el hallazgo propio de este bloque, porque es una conducta que
ninguna de las siete corridas del Bloque 21 podía producir.

En la corrida 2, en el primer turno de `consulta_001`, el modelo
escribió que la fracción superior a seis meses se cuenta según el
**artículo 173**. Esa regla está en el 163, y la herramienta se lo
había dicho en la misma vuelta. Su salida nombra el 163 siete veces
y no nombra el 173 en ninguna parte. El 173 tampoco está en el
corpus.

En el segundo turno de la misma sesión lo repitió, "según el
artículo 173 del Código del Trabajo".

Lo que viaja en el historial entre un turno y otro es la respuesta
anterior del propio modelo, con el 173 adentro. La leyó y la volvió
a usar.

**El dato que lo confirma.** `consulta_002` es sesión nueva y sin
historial, y citó el 163 correctamente en las tres corridas.

**Consecuencia práctica.** En el Bloque 21 cada caso era
independiente y un error moría en su caso. Con memoria, una
respuesta equivocada queda guardada como contexto y el turno
siguiente la toma como dato. La memoria no distingue lo que el
modelo acertó de lo que alteró.

---

## 2. El modelo solo altera números que ya tenía

El 173 no es una invención desde cero, y eso se puede mostrar con el
reparto de las nueve respuestas de cálculo.

| dónde aparece un número de artículo | resultado |
|---|---|
| para la indemnización, donde la herramienta dijo 163 | 163 en 7, 173 en 2 |
| para el aviso previo, donde ninguna herramienta dijo nada | ningún número en las 9 |

El modelo afirmó el aviso previo de treinta días en las nueve
respuestas, y en las nueve lo hizo sin citar artículo. Donde no
recibió un número, no produjo uno.

**Lo que esto identifica.** El problema no es que el modelo invente
citas. Es que corrompe la que se le entrega. Un número que llega en
la observación puede salir cambiado, y un tema sin número sale sin
número.

Eso es lo que decidió qué cambio al prompt probar, en la sección 6.

---

## 3. Lo que el modelo agrega y lo que suelta

Es la medición más limpia de la serie, porque son nueve turnos con
el mismo resultado en las dos direcciones.

| sobre nueve turnos de cálculo | |
|---|---|
| mencionó el aviso previo de treinta días | 9 |
| mencionó el feriado proporcional | 9 |
| conservó los supuestos que entrega la herramienta | 0 |

**Lo que agrega.** Ninguna herramienta le entregó el aviso previo ni
el feriado proporcional. La herramienta de cálculo no los nombra, y
la de búsqueda no se llamó en ninguna de las tres corridas. Los
nueve casos salieron de la memoria del modelo.

**Lo que suelta.** La herramienta de cálculo devuelve, en todas sus
respuestas, los supuestos que acotan el monto, que no se aplica a
contratos por obra o faena, a trabajadores de casa particular, a la
liquidación concursal, ni cuando lo pactado supera la indemnización
legal. En los nueve turnos ninguna respuesta final los conservó.

Eso precisa lo que decía la sección 6 del Bloque 21, donde los
supuestos estrechos se soltaban de forma despareja. En esta serie no
hay dispersión, es cero de nueve.

**Sobre el contenido agregado.** El aviso previo es correcto y está
en el inciso cuarto del artículo 162. Ese artículo se incorporó al
corpus después de la corrida 1, porque el 163 ya remitía a él y el
destino faltaba. Ahora existe el texto contra el cual contrastar,
aunque la búsqueda siga sin llamarse.

El feriado proporcional es el artículo 73 y no está en el corpus. Es
una afirmación sin fuente en el proyecto, repetida en nueve de nueve
respuestas.

---

## 4. La herramienta de búsqueda recibió cero llamadas

En los doce turnos de las tres corridas, la herramienta
`buscar_articulo_del_codigo_del_trabajo` no se invocó ni una vez.

Las cuatro entradas de la verificación apuntan al cálculo o no
apuntan a ninguna herramienta, de modo que el número no mide mala
elección sino cobertura. La verificación del Bloque 21 cubría una
herramienta sola, la otra sola, ninguna y las dos encadenadas. Esta
no.

**Lo que eso deja sin medir.** Estas tres corridas no dicen nada
sobre el corpus, ni sobre si el agente elige bien entre dos
herramientas. Las afirmaciones legales de la sección 3 convivieron
con un corpus que el agente no abrió.

---

## 5. Un cálculo que el modelo hizo sin la herramienta

Una vez en nueve turnos. En la corrida 2, en el segundo turno de
`consulta_001`, la línea de la verificación dice `herramientas
ninguna` y la respuesta entrega 7.200.000 pesos.

El monto es correcto, seis años por 1.200.000, y eso es lo
preocupante. Un resultado equivocado se ve en la respuesta, uno
correcto por coincidencia no se ve en ninguna parte.

La memoria funcionó en ese turno, porque el modelo conservó los
cinco años y ocho meses que la segunda pregunta no repetía. Lo que
no hizo fue entregárselos a la función.

**Lo que lo dejó a la vista.** La línea que imprime las herramientas
usadas en cada turno. La respuesta se lee igual de bien que las
otras ocho.

**Esto no se corrigió.** Es una ocurrencia en nueve turnos, y el
criterio es el mismo que se aplicó al nombre de herramienta
inventado en la sección 4 del Bloque 21.

---

## 6. El cambio al prompt del sistema, y lo que todavía no prueba

El prompt del Bloque 21 ya pedía repetir exacto lo que entrega una
herramienta, y en esa parte funcionó. Las cifras llegaron exactas en
las nueve respuestas, los 5.100.000, los 7.200.000, los 7.040.000,
los seis años y los once del tope.

Lo que esa frase no mencionaba eran los números de artículo, que es
justo lo que la sección 2 identifica como el dato que se altera.

**Antes.** "Cuando una herramienta te entregue cifras o plazos,
repítelos exactamente como llegaron."

**Después.** "Cuando una herramienta te entregue cifras, plazos o
números de artículo, repítelos exactamente como llegaron."

El cambio extiende una instrucción que ya se cumplía, aplicada al
mismo tipo de dato, y no prohíbe nada. Esa fue la razón de
preferirlo. El primer cambio del Bloque 21 era una prohibición y
produjo el efecto contrario al buscado.

**Lo que no se puede afirmar.** La corrida 3 es la primera con la
frase nueva y salió limpia, con el 163 en las tres respuestas y sin
el 173. Eso no prueba que el cambio sirvió. El 173 apareció en una
de las dos corridas anteriores, de modo que una corrida limpia
después sale por azar con frecuencia parecida. Con una tasa de un
medio harían falta cuatro o cinco corridas limpias seguidas para que
el número diga algo, porque cuatro seguidas es una entre dieciséis.

Lo que sí se puede afirmar es que el cambio se hizo por una
observación concreta y que la conducta no reapareció en la corrida
siguiente.

**Por qué se cambió con una sola observación.** Es la diferencia con
el nombre de herramienta inventado del Bloque 21. Ese lo corrigió el
propio ciclo, usando la observación que devolvió LangChain, y la
persona nunca lo vio. Un número de artículo equivocado llega a
destino y nada lo atrapa.

---

## 7. Una etiqueta HTML en la respuesta

Una vez en doce turnos. En la corrida 1, en el segundo turno de
`consulta_001`, el modelo abrió su respuesta con un `<span></span>`
literal, y `texto_de_la_respuesta` lo pasó tal cual a la salida.

No reapareció en las dos corridas siguientes. El prompt ya pide
escribir en texto plano sin markdown, y esto no es markdown sino
marcado generado de más.

Queda anotado y no se corrigió, por el mismo criterio de la
sección 5.

---

## 8. Los contadores del historial son estables, la elección no

Los dos comportamientos se midieron en la misma serie y salieron
distintos.

| | corrida 1 | corrida 2 | corrida 3 |
|---|---|---|---|
| `consulta_001` tras el primer turno | 2 | 2 | 2 |
| `consulta_001` tras el segundo | 4 | 4 | 4 |
| `consulta_002` | 2 | 2 | 2 |
| `consulta_003` | 2 | 2 | 2 |
| turnos de cálculo que llamaron al cálculo | 3 de 3 | 2 de 3 | 3 de 3 |

El historial guarda dos mensajes por turno, la pregunta y la
respuesta, y lo hizo igual en las tres corridas. Es código, no
generación.

La elección de herramienta es texto generado token por token y no es
estable, igual que en la sección 1 del Bloque 21.

**Por qué el contador importa.** La lección 2 advierte que la falla
de la memoria es silenciosa, el agente responde normal y el
historial queda vacío. `len(obtener_historial(sid).messages)` es lo
único que distingue las dos situaciones desde la salida.

---

## 9. El aislamiento entre sesiones

Limpio en las tres corridas. `consulta_003` pregunta por una
antigüedad y un sueldo que nunca recibió, y en las tres respondió
que no tiene el dato. No llamó ninguna herramienta en ninguna.

**Una corrección a la prueba.** La primera versión usaba la misma
antigüedad en `consulta_001` y en `consulta_002`, cinco años y ocho
meses. Con los mismos datos en las dos sesiones una filtración no se
puede atribuir a ninguna, y si las cifras coinciden tampoco se nota.
`consulta_002` pasó a doce años y tres meses con un sueldo de
640.000.

Ese cambio trajo un efecto que no se buscaba. Los doce años disparan
el tope de once del artículo 163, que ninguna de las siete corridas
del Bloque 21 había ejecutado, porque todas usaban cinco años y ocho
meses.

**El chequeo automático.** Busca las cifras de las otras dos
sesiones en la respuesta de `consulta_003`, en las tres formas en
que el modelo las escribe, con punto, con coma y sin separador. Se
verificó antes que ninguna de esas marcas aparece en el texto de los
ocho artículos del corpus, de modo que una cita no las gatilla.

---

## 10. El parámetro con valor por defecto

`horas_semanales` tiene `default=0` en el `args_schema`, y el
docstring indica dejarlo en cero si la persona no menciona la
jornada. Ninguna de las cuatro entradas la menciona.

De las ocho llamadas al cálculo, cuatro pasaron `horas_semanales=0`
explícito y cuatro omitieron el parámetro. El resultado es el mismo
en los dos casos, porque el valor por defecto es el que el modelo
escribe cuando lo escribe.

Las dos conductas cumplen el docstring. Lo que muestra el reparto
mitad y mitad es que el modelo no resuelve igual una decisión que da
lo mismo, y que un parámetro con valor por defecto razonable absorbe
esa variación sin que llegue al resultado.

Pydantic no rechazó ninguna de las ocho llamadas. No hubo
`ValidationError` en la serie.

---

## 11. El aviso de deprecación

Aparece una vez por corrida y es esperado.

```
LangChainDeprecationWarning: The class `InMemoryChatMessageHistory`
was deprecated in LangChain 1.6.4 and will be removed in 2.0.0
```

Es una advertencia, no un error, y la lección 2 lo anticipa. Las
tres corridas completaron los cuatro turnos con el aviso presente.

Sale una vez y no tres, aunque se creen tres sesiones, porque el
sistema de advertencias de Python no repite el mismo aviso desde la
misma línea.

**El límite real que anuncia.** La clase se elimina en LangChain
2.0.0 y la documentación recomienda otra alternativa. El código
queda atado a una versión con fecha de término.

---

## 12. Lo que la verificación automática no comprueba

**El chequeo de filtración solo atrapa cifras escritas.** Si el
modelo parafraseara, por ejemplo "me dijiste que trabajaste algo más
de una década", la marca no calza y el chequeo cierra limpio. Que no
aparezcan marcas no prueba que no hubo filtración.

**El contador del historial prueba que guardó, no que guardó bien.**
Cuenta mensajes. Los cuatro de `consulta_001` habrían sido cuatro
igual con el contenido equivocado, que es exactamente lo que ocurrió
en la corrida 2 con el 173 adentro.

**Nada de la verificación mira el número de artículo.** El 173 se
descubrió leyendo la respuesta. Las dos pruebas pasaron igual en esa
corrida.

Igual que en el Bloque 21, esa parte de la verificación es manual y
no se puede automatizar contando mensajes ni comparando nombres de
herramientas.
