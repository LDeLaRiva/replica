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


