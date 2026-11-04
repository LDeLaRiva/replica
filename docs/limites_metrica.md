# Límites de la métrica de evaluación

Actualizado el 31-10-2026.

## Qué mide

Cuántas palabras de una referencia escrita a mano aparecen en la
respuesta del modelo, contando repeticiones. Devuelve precisión,
cobertura y F1. No mide si la respuesta es correcta.

## Modos de falla conocidos

- Una respuesta correcta y completa puntúa bajo, porque cada palabra
  de más divide la precisión. La consulta por el permiso de
  matrimonio no tiene un solo error.
```
precisión 0.184   cobertura 0.875   F1 0.304   el peor de 20
```

- Un dato equivocado casi no baja el puntaje. En la jornada semanal
  el modelo responde 44 horas, cuando desde abril de 2026 son 42.
```
el mismo error, redacción del modelo        F1 0.385
el mismo error, redacción de la referencia  F1 0.944
```

- La misma cifra escrita distinto no suma nada. Para la métrica 15 y
  quince no comparten ninguna palabra, y el símbolo % se borra al
  limpiar el texto. Pasó en dos de las veinte, las dos correctas, y
  una de ellas está entre las diez revisadas.
```
recargo     "50 por ciento" contra "50%"     cobertura 0.882
escriturar  "15 días" contra "quince días"   cobertura 0.769
```

- Un preámbulo correcto diluye la precisión. Cuatro de las veinte
  respuestas empiezan nombrando la legislación chilena, que viene de
  la instrucción del cliente.
```
con "Según la legislación chilena, se pueden..."   F1 0.750
la misma respuesta sin el preámbulo                F1 0.900
```

- El puntaje no se puede comparar entre consultas distintas, porque
  depende del largo de la referencia.
```
prenatal       referencia  9 palabras, respuesta +6   F1 0.667
feriado anual  referencia 18 palabras, respuesta +7   F1 0.698
```

- La negación ausente no apareció en esta muestra, así que no hay
  ejemplo que mostrar. Ninguna de las diez respuestas revisadas
  contradijo su referencia.
## Muestra revisada

10 casos revisados a mano, los 5 de menor F1 y los 5 de mayor, sobre
20 respuestas generadas el 31-10-2026. El registro está en
src/revision_manual.json.

## Recomendación de uso

- Usar el puntaje para ordenar y decidir qué revisar primero, no
  para aprobar ni rechazar. Aquí una respuesta sin errores saca
  entre 0.30 y 0.82.
- Comparar una consulta solo consigo misma, antes y después de
  cambiar algo del cliente. Entre dos consultas distintas no se
  puede comparar, porque depende del largo de cada referencia.
- Escribir las cifras de la referencia cortas, 50% en vez de 50 por
  ciento. Queda una palabra en vez de tres y hay menos que perder,
  0.933 en el peor caso contra 0.882.
- Antes de dar por mala una respuesta con puntaje bajo, revisar si
  la cifra está escrita de otra forma. 15 y quince son palabras
  distintas para la métrica.
- Revisar a mano cualquier respuesta que se vaya a usar. Todas las
  de este corpus son cifras de normativa laboral, y ahí la métrica
  no distingue un dato correcto de uno falso.


# 03 NOV 26

## Acierta el dato y cita mal la fuente, de forma distinta cada vez

Medido el 2026-11-03 sobre la ruta `consulta` de `enrutamiento.py`, en
tres corridas de la misma pregunta por el permiso por fallecimiento de
un hermano.

Las tres veces acertó los cuatro días hábiles. Las tres veces citó mal.

```text
corrida 1    Código del Trabajo artículo 66 ter
corrida 2    Código del Trabajo artículo 66 ter
corrida 3    artículo 66 inciso primero del Código del Trabajo
```

El 66 ter regula el permiso para vacunación. El artículo correcto es el
66, y dentro de él la regla del hermano está en el inciso segundo, no
en el primero. El inciso primero es el del hijo y el del cónyuge.

Lo que no cambia es que la cita está mal. Lo que cambia es en qué. Eso
es más difícil de manejar que un error fijo, porque no se puede
descartar mirando una sola corrida. El prompt ya restringe las fuentes
al Código del Trabajo y a los dictámenes de la Dirección del Trabajo, y
autoriza decir que no se sabe. Aun así cita con seguridad las tres
veces.

La métrica casi no lo registra. Contra una referencia correcta, la
respuesta de la corrida 1 da F1 0.780 y la misma respuesta con la cita
buena da 0.800. Una palabra de más, y esa palabra invalida el respaldo
entero de la respuesta.

## Omite una referencia cruzada del propio texto

Medido el 2026-11-03 sobre la ruta `ley` de `enrutamiento.py`, en las
mismas tres corridas.

Con el artículo 66 completo delante, la explicación acierta los cuatro
plazos y sus unidades, y se equivoca al resolver a quién alcanza el
fuero.

El artículo dice que goza de fuero "el trabajador al que se refiere el
inciso primero", y ese inciso cubre dos casos, la muerte de un hijo y
la del cónyuge o conviviente civil. La explicación lo deja solo en el
hijo.

```text
- El trabajador que sufre la muerte de un hijo tiene protección
  laboral, llamada fuero, por el período de un mes desde el día del
  fallecimiento.
```

Este sí salió igual en las tres corridas. Acá no inventa, omite. Por eso
es más difícil de ver que un dato falso, y una métrica de solapamiento
la puntúa alto, porque todo lo que dice sí está en el texto. Lo que
falta no se castiga.

## Lo que muestran los dos casos juntos

Las dos respuestas salieron del mismo modelo, el mismo día, sobre el
mismo artículo. Lo único distinto fue si el texto estaba delante.

La ruta que respondió de memoria citó mal la fuente las tres veces. La
ruta que recibió el texto acertó los cuatro plazos las tres veces y
solo falló en una referencia cruzada.

Eso acota para qué sirve medir con solapamiento. Sirve para comparar
respuestas de una misma ruta entre corridas. No sirve para decidir si
una respuesta está respaldada, porque los dos errores de arriba son de
respaldo y ninguno mueve el número lo suficiente como para aparecer en
los peores casos.
