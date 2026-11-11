"""Corpus legal del proyecto, artículos del Código del Trabajo.

Guarda qué dice la ley y cómo se busca. No sabe nada de agentes ni
de modelos, así que sirve igual para el agente con herramientas,
para la ruta ley del enrutamiento del Bloque 19, o para cualquier
otra cosa que necesite consultar el mismo texto.

Por qué el texto está en el proyecto

Porque el modelo no se sabe la ley. Preguntándole por el artículo 66
sin darle el texto, no entregó el artículo y el inciso correctos en
ninguna de las corridas registradas. Con el texto cargado los acertó
en todas. El registro está en docs/limites_bloque21.md.

Lo que falla no es el número del artículo sino el detalle, a quién
cubre el fuero o si los días son corridos o hábiles, y en una
consulta laboral esa diferencia decide si a alguien le pagan. Aparte
de eso, con el texto en el repositorio cualquiera puede contrastar
lo que respondió la aplicación contra lo que dice la ley, y una
respuesta construida de memoria no se puede contrastar con nada.

Este corpus tiene dos límites conocidos. Si la ley cambia, el
archivo queda viejo hasta que alguien lo actualice. Y son once
artículos, de modo que para cualquier otro tema la búsqueda contesta
que no lo encontró.

Ese segundo límite se puede medir. Los artículos cargados remiten a
otros once del Código que no están. El más citado es el 169, con dos
menciones, y los otros diez traen una cada uno. Una respuesta
todavía puede quedar apuntando a un texto que la búsqueda no
entrega.

Por qué están el 159 y el 172

Los dos entraron por esa misma medición. El 159 era el hueco más
grande, con seis menciones, dos en el 162, una en el 163 y tres en
el 168, que invocan sus causales por el número sin decir qué dicen.
Ningún otro artículo ausente pasaba de una mención.

Y el daño se alcanzó a medir. En una corrida, el agente describió el
número 6 del 159 como la salida intempestiva del trabajador, que es
el 160 número 4 letra a), cuando el 6 es el caso fortuito o fuerza
mayor. Tomó una frase de un artículo que tenía y la pegó a un número
de uno que no.

El 172 es el tope de noventa unidades de fomento sobre la
remuneración con que se calcula la indemnización. El cálculo del
proyecto no lo aplica, porque no tiene el valor de la UF, y hasta
entonces el tope no estaba ni en el texto cargado.

Una versión de producción consultaría la fuente en vivo o cargaría
el Código completo, para que la cobertura no dependa de haber
elegido bien once artículos.

La forma de buscar es otra cosa. Esta función busca por palabra
clave. El Bloque 24 indexa este mismo texto para buscarlo también
por significado, de modo que las dos búsquedas quedan sobre el
mismo corpus de once artículos.

Por qué vive aparte del agente

El texto está verificado contra la fuente artículo por artículo, y
tenerlo en un solo lugar evita que una corrección quede aplicada en
un archivo y olvidada en otro.

Además sigue la retroalimentación del Gate 1, que pidió continuar
desacoplando las funciones auxiliares hacia módulos de soporte para
mantener conciso el punto de entrada. Esa observación se hizo sobre
main.py, y el mismo criterio se aplica al archivo del agente, que
también se ejecuta directamente y que llevaba el corpus completo
adentro. Al moverlo salieron 284 líneas de ese punto de entrada. El
módulo creció después, cuando entraron el 159 y el 172.

La búsqueda se expone como función común, sin el decorador @tool.
Decorarla es decisión de quien la use como herramienta, y así el
nombre con que un agente la invoca no queda fijado en este módulo.

Fuente del texto

El Código del Trabajo publicado por la Biblioteca del Congreso
Nacional. Los artículos cargados son el 40 bis, el 40 bis D, el 66,
el 159, el 160, el 161, el 162, el 163, el 168, el 172 y el inciso
primero del 177.
"""

import unicodedata



def sin_tildes(texto):
    """Deja el texto en minúsculas y sin tildes, para poder comparar.

    Sin esto, buscar "indemnizacion" dentro de "indemnización" da falso,
    porque la i con tilde y la i sin tilde son caracteres distintos. Es
    la misma trampa de las categorías del Bloque 19, y aquí tiene
    más efecto, porque las personas escriben con tilde y a veces
    sin ella.
    """
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(
        c for c in descompuesto if not unicodedata.combining(c)
    )



# Cada entrada son las claves que la disparan y el texto que devuelve.
#
# Las claves van sin tilde y como raíces, no como palabras completas.
# "despid" calza con despido, despidieron y despedida. Si fuera
# "despido" a secas, no calzaría con "me despidieron".
#
# El 66 lleva "muer" y "muri" por separado, y las dos hacen falta.
# "muer" calza con muerte y muerto, y "muri" con murió y murieron.
# Ninguna de las dos cubre a la otra, porque la raíz cambia de vocal.
#
# El 172 no lleva "uf" como clave, aunque el artículo trate del tope
# en unidades de fomento. Son dos caracteres y calzan dentro de
# palabras como sufrió o insuficiente, que no vienen al caso. Va
# "unidades de fomento" escrito completo.
#
# El 159 no lleva clave de muerte, aunque su número 3 sea la muerte
# del trabajador. "muer" y "muri" ya disparan el 66, y agregarlas al
# 159 haría que toda consulta por el permiso por fallecimiento
# arrastre además las seis causales de término. El costo de no
# ponerlas es que una consulta por la muerte del propio trabajador
# llega al 66 y no al 159.
#
# El texto de cada artículo va literal, con los incisos separados por
# salto de línea y numerados entre corchetes. No va resumido porque
# un resumen aplana la estructura del artículo, y los artículos se
# remiten a sus propios incisos. El 66 dice "el trabajador al que se
# refiere el inciso primero gozará de fuero laboral", y sobre un
# texto plano esa remisión queda sin referente, de modo que quien lo
# lea tiene que suponer a qué apunta. Lo que esa suposición produjo
# está registrado en docs/limites_bloque21.md.
#
# El 159 y el 160 no llevan corchetes porque los dos se numeran
# solos, el 159 del 1.- al 6.- y el 160 del 1.- al 7.-, y esa
# numeración es la que hay que conservar.
#
# El 40 bis y el 40 bis D tampoco los llevan, porque son de un solo
# inciso y el número no distinguiría nada.
#
# En el 163 y en el 168 hay líneas con corchete y líneas sin él, y
# la diferencia no es un olvido. Las letras que van dentro de un
# inciso no llevan corchete, que son las a) y b) del inciso 5 del
# 163 y las a), b) y c) del inciso 1 del 168. El corchete marca
# incisos, y esas letras viven adentro de uno.
#
# Del 177 va solo el inciso primero, que es el que trae el plazo de
# diez días hábiles. El artículo sigue con doce incisos de
# procedimiento, anunciados en una línea para que el inciso primero
# no se lea como si fuera el artículo completo.
#
# Lo que va entre [nota: ...] es anotación de este proyecto y no
# texto legal. Son trece y hacen cuatro trabajos distintos.
#
# Siete resuelven las remisiones que un artículo hace a sus propios
# incisos, una en el 66, una en el 161, tres en el 163, una en el
# 168 y una en el 172. Se insertan dentro de la oración y no como
# nota al margen, para que al citar la oración la aclaración vaya
# incorporada y no pueda quedar atrás, y para que la expresión "el
# trabajador del inciso primero" no llegue a destino sin referente.
#
# Una resuelve una remisión a otro artículo que este corpus sí
# tiene. Es la del 162, que nombra los números 4, 5 y 6 del 159.
#
# Dos avisan de un texto al que su propio artículo remite y que este
# corpus no tiene. En el 168 es el artículo 153 con el Título IV del
# Libro II, y en el 172 son el 163 bis, el 169, el 170 y el 171.
#
# Las tres restantes fijan alcance o estructura. La del 40 bis D
# dice de qué trabajador habla el artículo, porque menciona la
# indemnización que pudiere corresponderle sin decir a cuál, y eso
# lo establece el párrafo que abre el 40 bis. La del 159 avisa que
# los tres párrafos que siguen al número 4 lo desarrollan y no son
# causales nuevas. La del 177 avisa de los doce incisos de
# procedimiento que no van.
#
# No se tocaron las referencias que no son ambiguas. "Este artículo"
# y "el presente artículo" se explican solos, y las que dicen "el
# inciso segundo del artículo 161" ya traen el número del artículo.
ARTICULOS = (
    (
        (
            "jornada parcial", "tiempo parcial", "part time", "part-time",
            "media jornada", "horas semanales",
        ),
        "Art. 40 bis. Se podrán pactar contratos de trabajo con jornada "
        "a tiempo parcial, considerándose afectos a la normativa del "
        "presente párrafo, aquéllos en que se ha convenido una jornada "
        "de trabajo no superior a treinta horas semanales."
    ),
    (
        (
            "jornada parcial", "tiempo parcial", "part time", "part-time",
            "media jornada", "horas semanales",
            "promedio de las remuneraciones",
        ),
        "Art. 40 bis D. Para los efectos del cálculo de la "
        "indemnización que pudiere corresponderle al trabajador al "
        "momento del término de sus servicios, se entenderá por última "
        "remuneración el promedio de las remuneraciones percibidas por "
        "el trabajador durante la vigencia de su contrato o de los "
        "últimos once años del mismo. Para este fin, cada una de las "
        "remuneraciones que abarque el período de cálculo deberá ser "
        "reajustada por la variación experimentada por el índice de "
        "precios al consumidor, entre el mes anterior al pago de la "
        "remuneración respectiva y el mes anterior al término del "
        "contrato. Con todo, si la indemnización que le correspondiere "
        "por aplicación del artículo 163 fuere superior, se le aplicará "
        "ésta. [nota: este artículo integra el párrafo que abre el "
        "artículo 40 bis, cuyo texto declara afectos a esa normativa "
        "los contratos de jornada no superior a treinta horas "
        "semanales. Fuera de la jornada parcial no se aplica]"
    ),
    (
        ("fallec", "muer", "muri", "luto", "duelo"),
        "[1] Artículo 66.- En caso de muerte de un hijo, todo "
        "trabajador tendrá derecho a diez días corridos de permiso "
        "pagado. En caso de la muerte del cónyuge o conviviente "
        "civil, todo trabajador tendrá derecho a un permiso "
        "similar, por siete días corridos. En ambos casos, este "
        "permiso será adicional al feriado anual, "
        "independientemente del tiempo de servicio.\n"
        "[2] Igual permiso se aplicará, por siete días hábiles, en "
        "el caso de muerte de un hijo en período de gestación. En "
        "el caso de muerte de un hermano, del padre o de la madre "
        "del trabajador, dicho permiso se extenderá por cuatro días "
        "hábiles.\n"
        "[3] Estos permisos deberán hacerse efectivos a partir del "
        "día del respectivo fallecimiento. No obstante, tratándose "
        "de una defunción fetal, el permiso se hará efectivo desde "
        "el momento de acreditarse la muerte, con el respectivo "
        "certificado de defunción fetal.\n"
        "[4] El trabajador al que se refiere el inciso primero "
        "[nota: es el inciso 1, es decir quien sufre la muerte de un "
        "hijo o la del cónyuge o conviviente civil] "
        "gozará de fuero laboral por el periodo de un mes a partir "
        "del día del respectivo fallecimiento. Si se trata de "
        "trabajadores cuyos contratos de trabajo sean a plazo fijo, "
        "o por obra o servicio determinado, el fuero establecido en "
        "el presente artículo se mantendrá vigente por el mismo "
        "periodo o hasta el término de dicho contrato.\n"
        "[5] Los días de permiso consagrados en este artículo no "
        "podrán ser compensados en dinero."
    ),
    (
        (
            "renunci", "mutuo acuerdo", "plazo fijo",
            "vencimiento del plazo", "caso fortuito", "fuerza mayor",
            "conclusion del trabajo",
        ),
        "Art. 159. El contrato de trabajo terminará en los siguientes "
        "casos:\n"
        "1.- Mutuo acuerdo de las partes.\n"
        "2.- Renuncia del trabajador, dando aviso a su empleador con "
        "treinta días de anticipación, a lo menos.\n"
        "3.- Muerte del trabajador.\n"
        "4.- Vencimiento del plazo convenido en el contrato. La "
        "duración del contrato de plazo fijo no podrá exceder de un "
        "año. [nota: los tres párrafos que siguen desarrollan este "
        "número 4 y no son causales nuevas]\n"
        "El trabajador que hubiere prestado servicios discontinuos en "
        "virtud de más de dos contratos a plazo, durante doce meses o "
        "más en un período de quince meses, contados desde la primera "
        "contratación, se presumirá legalmente que ha sido contratado "
        "por una duración indefinida.\n"
        "Tratándose de gerentes o personas que tengan un título "
        "profesional o técnico otorgado por una institución de "
        "educación superior del Estado o reconocida por éste, la "
        "duración del contrato no podrá exceder de dos años.\n"
        "El hecho de continuar el trabajador prestando servicios con "
        "conocimiento del empleador después de expirado el plazo, lo "
        "transforma en contrato de duración indefinida. Igual efecto "
        "producirá la segunda renovación de un contrato de plazo fijo.\n"
        "5.- Conclusión del trabajo o servicio que dio origen al "
        "contrato.\n"
        "6.- Caso fortuito o fuerza mayor."
    ),
    (
        ("probidad", "acoso", "abandon", "incumpl",
         "sin derecho a indemnizacion"),
        "Art. 160. El contrato de trabajo termina sin derecho a "
        "indemnización alguna cuando el empleador le ponga término "
        "invocando una o más de las siguientes causales:\n"
        "1.- Alguna de las conductas indebidas de carácter grave, "
        "debidamente comprobadas, que a continuación se señalan:\n"
        "a) Falta de probidad del trabajador en el desempeño de sus "
        "funciones;\n"
        "b) Conductas de acoso sexual;\n"
        "c) Vías de hecho ejercidas por el trabajador en contra del "
        "empleador o de cualquier trabajador que se desempeñe en la "
        "misma empresa;\n"
        "d) Injurias proferidas por el trabajador al empleador;\n"
        "e) Conducta inmoral del trabajador que afecte a la empresa "
        "donde se desempeña, y\n"
        "f) Conductas de acoso laboral.\n"
        "2.- Negociaciones que ejecute el trabajador dentro del "
        "giro del negocio y que hubieren sido prohibidas por "
        "escrito en el respectivo contrato por el empleador.\n"
        "3.- No concurrencia del trabajador a sus labores sin causa "
        "justificada durante dos días seguidos, dos lunes en el mes "
        "o un total de tres días durante igual período de tiempo; "
        "asimismo, la falta injustificada, o sin aviso previo de "
        "parte del trabajador que tuviere a su cargo una actividad, "
        "faena o máquina cuyo abandono o paralización signifique "
        "una perturbación grave en la marcha de la obra.\n"
        "4.- Abandono del trabajo por parte del trabajador, "
        "entendiéndose por tal:\n"
        "a) la salida intempestiva e injustificada del trabajador "
        "del sitio de la faena y durante las horas de trabajo, sin "
        "permiso del empleador o de quien lo represente, y\n"
        "b) la negativa a trabajar sin causa justificada en las "
        "faenas convenidas en el contrato.\n"
        "5.- Actos, omisiones o imprudencias temerarias que afecten "
        "a la seguridad o al funcionamiento del establecimiento, a "
        "la seguridad o a la actividad de los trabajadores, o a la "
        "salud de éstos.\n"
        "6.- El perjuicio material causado intencionalmente en las "
        "instalaciones, maquinarias, herramientas, útiles de "
        "trabajo, productos o mercaderías.\n"
        "7.- Incumplimiento grave de las obligaciones que impone el "
        "contrato."
    ),
    (
        ("necesidades de la empresa", "desahucio", "despid"),
        "[1] Art. 161. Sin perjuicio de lo señalado en los "
        "artículos precedentes, el empleador podrá poner término al "
        "contrato de trabajo invocando como causal las necesidades "
        "de la empresa, establecimiento o servicio, tales como las "
        "derivadas de la racionalización o modernización de los "
        "mismos, bajas en la productividad, cambios en las "
        "condiciones del mercado o de la economía, que hagan "
        "necesaria la separación de uno o más trabajadores. La "
        "eventual impugnación de las causales señaladas, se regirá "
        "por lo dispuesto en el artículo 168.\n"
        "[2] En el caso de los trabajadores que tengan poder para "
        "representar al empleador, tales como gerentes, "
        "subgerentes, agentes o apoderados, siempre que, en todos "
        "estos casos, estén dotados, a lo menos, de facultades "
        "generales de administración, y en el caso de los "
        "trabajadores de casa particular, el contrato de trabajo "
        "podrá, además, terminar por desahucio escrito del "
        "empleador, el que deberá darse con treinta días de "
        "anticipación, a lo menos, con copia a la Inspección del "
        "Trabajo respectiva. Sin embargo, no se requerirá esta "
        "anticipación cuando el empleador pagare al trabajador, al "
        "momento de la terminación, una indemnización en dinero "
        "efectivo equivalente a la última remuneración mensual "
        "devengada. Regirá también esta norma tratándose de cargos "
        "o empleos de la exclusiva confianza del empleador, cuyo "
        "carácter de tales emane de la naturaleza de los mismos.\n"
        "[3] Las causales señaladas en los incisos anteriores "
        "[nota: son el inciso 1, necesidades de la empresa, y el "
        "inciso 2, desahucio] no "
        "podrán ser invocadas con respecto a trabajadores que gocen "
        "de licencia por enfermedad común, accidente del trabajo o "
        "enfermedad profesional, otorgada en conformidad a las "
        "normas legales vigentes que regulan la materia."
    ),
    (
        (
            "aviso", "avisar", "carta de despido", "cotizacion",
            "imposicion", "ley bustos", "sustitutiva", "convalid",
        ),
        "[1] Art. 162. Si el contrato de trabajo termina de acuerdo con "
        "los números 4, 5 ó 6 del artículo 159, o si el empleador le "
        "pusiere término por aplicación de una o más de las causales "
        "señaladas en el artículo 160, deberá comunicarlo por escrito "
        "al trabajador, personalmente o por carta certificada enviada "
        "al domicilio señalado en el contrato, expresando la o las "
        "causales invocadas y los hechos en que se funda. [nota: el "
        "artículo 159 está en este corpus, y sus números 4, 5 y 6 son "
        "el vencimiento del plazo convenido, la conclusión del trabajo "
        "que dio origen al contrato y el caso fortuito o fuerza "
        "mayor]\n"
        "[2] Esta comunicación se entregará o deberá enviarse, dentro "
        "de los tres días hábiles siguientes al de la separación del "
        "trabajador. Si se tratare de la causal señalada en el número 6 "
        "del artículo 159, el plazo será de seis días hábiles.\n"
        "[3] Deberá enviarse copia del aviso mencionado en el inciso "
        "anterior a la respectiva Inspección del Trabajo, dentro del "
        "mismo plazo. Las Inspecciones del Trabajo, tendrán un registro "
        "de las comunicaciones de terminación de contrato que se les "
        "envíen, el que se mantendrá actualizado con los avisos "
        "recibidos en los últimos treinta días hábiles.\n"
        "[4] Cuando el empleador invoque la causal señalada en el "
        "inciso primero del artículo 161, el aviso deberá darse al "
        "trabajador, con copia a la Inspección del Trabajo respectiva, "
        "a lo menos con treinta días de anticipación. Sin embargo, no "
        "se requerirá esta anticipación cuando el empleador pagare al "
        "trabajador una indemnización en dinero efectivo sustitutiva "
        "del aviso previo, equivalente a la última remuneración mensual "
        "devengada. La comunicación al trabajador deberá, además, "
        "indicar, precisamente, el monto total a pagar de conformidad "
        "con lo dispuesto en el artículo siguiente. Igual indicación "
        "deberá contener la comunicación de la terminación del contrato "
        "celebrado para una obra o faena determinada, cuando "
        "corresponda el pago de indemnización por el tiempo servido, en "
        "conformidad a lo dispuesto en el artículo 163.\n"
        "[5] Para proceder al despido de un trabajador por alguna de "
        "las causales a que se refieren los incisos precedentes o el "
        "artículo anterior, el empleador le deberá informar por escrito "
        "el estado de pago de las cotizaciones previsionales devengadas "
        "hasta el último día del mes anterior al del despido, "
        "adjuntando los comprobantes que lo justifiquen. Si el "
        "empleador no hubiere efectuado el integro de dichas "
        "cotizaciones previsionales al momento del despido, éste no "
        "producirá el efecto de poner término al contrato de trabajo.\n"
        "[6] Con todo, el empleador podrá convalidar el despido "
        "mediante el pago de las imposiciones morosas del trabajador, "
        "lo que comunicará a éste mediante carta certificada acompañada "
        "de la documentación emitida por las instituciones "
        "previsionales correspondientes, en que conste la recepción de "
        "dicho pago.\n"
        "[7] Sin perjuicio de lo anterior, el empleador deberá pagar al "
        "trabajador las remuneraciones y demás prestaciones consignadas "
        "en el contrato de trabajo durante el período comprendido entre "
        "la fecha del despido y la fecha de envío o entrega de la "
        "referida comunicación al trabajador. No será exigible esta "
        "obligación del empleador cuando el monto adeudado por concepto "
        "de imposiciones morosas no exceda de la cantidad menor entre "
        "el 10% del total de la deuda previsional o 2 unidades "
        "tributarias mensuales, y siempre que dicho monto sea pagado "
        "por el empleador dentro del plazo de 15 días hábiles contado "
        "desde la notificación de la respectiva demanda.\n"
        "[8] El empleador deberá informar en el aviso de término del "
        "contrato si otorgará y pagará el finiquito laboral en forma "
        "presencial o electrónica, indicando expresamente que es "
        "voluntario para el trabajador aceptar, firmar y recibir el "
        "pago en forma electrónica y que siempre podrá optar por la "
        "actuación presencial ante un ministro de fe. En dicho aviso, "
        "el empleador deberá informar al trabajador que, al momento de "
        "suscribir el finiquito, si lo estima necesario podrá formular "
        "reserva de derechos.\n"
        "[9] Los errores u omisiones en que se incurra con ocasión de "
        "estas comunicaciones que no tengan relación con la obligación "
        "de pago íntegro de las imposiciones previsionales, no "
        "invalidarán la terminación del contrato, sin perjuicio de las "
        "sanciones administrativas que establece el artículo 506 de "
        "este Código.\n"
        "[10] La Inspección del Trabajo, de oficio o a petición de "
        "parte, estará especialmente facultada para exigir al empleador "
        "la acreditación del pago de cotizaciones previsionales al "
        "momento del despido, en los casos a que se refieren los "
        "incisos precedentes. Asimismo, estará facultada para exigir el "
        "pago de las cotizaciones devengadas durante el lapso a que se "
        "refiere el inciso séptimo. Las infracciones a este inciso se "
        "sancionarán con multa de 2 a 20 UTM."
    ),
    (
        ("indemniz", "anos de servicio"),
        "[1] Art. 163. Si el contrato hubiere estado vigente un año "
        "o más y el empleador le pusiere término en conformidad al "
        "artículo 161, deberá pagar al trabajador, la indemnización "
        "por años de servicio que las partes hayan convenido "
        "individual o colectivamente, siempre que ésta fuere de un "
        "monto superior a la establecida en el inciso siguiente "
        "[nota: es el inciso 2, la indemnización legal de treinta "
        "días de la última remuneración por año de servicio].\n"
        "[2] A falta de esta estipulación, entendiéndose además por "
        "tal la que no cumpla con el requisito señalado en el "
        "inciso precedente [nota: es el inciso 1, que exige que lo "
        "pactado sea de un monto superior], el empleador deberá "
        "pagar al trabajador "
        "una indemnización equivalente a treinta días de la última "
        "remuneración mensual devengada por cada año de servicio y "
        "fracción superior a seis meses, prestados continuamente a "
        "dicho empleador. Esta indemnización tendrá un límite "
        "máximo de trescientos treinta días de remuneración.\n"
        "[3] Si el contrato celebrado para una obra o faena "
        "determinada hubiere estado vigente por un mes o más, el "
        "empleador podrá ponerle término en forma justificada en "
        "tanto pague al trabajador, en el momento de su "
        "terminación, una indemnización equivalente a dos y medio "
        "días de remuneración por cada mes trabajado y fracción "
        "superior a quince días, en la forma y modalidad señalada "
        "en el artículo 23 transitorio de este Código. Esta "
        "indemnización será calculada en conformidad a lo "
        "establecido en el artículo 172, y le será aplicable lo "
        "dispuesto en el inciso segundo del artículo 13 de la ley "
        "N° 19.728. Sólo corresponderá el pago de la prestación "
        "antes señalada, si se pusiere término al contrato por la "
        "causal contemplada en el número 5 del artículo 159. El "
        "ejercicio del derecho establecido en este inciso por parte "
        "del trabajador es incompatible con las acciones derivadas "
        "de la aplicación del inciso primero del artículo 168, sin "
        "perjuicio de las acciones señaladas en el artículo 485 de "
        "este Código.\n"
        "[4] La indemnización a que se refiere este artículo será "
        "compatible con la sustitutiva del aviso previo que "
        "corresponda al trabajador, según lo establecido en el "
        "inciso segundo del artículo 161 y en el inciso cuarto del "
        "artículo 162 de este Código.\n"
        "[5] Lo dispuesto en los incisos anteriores "
        "[nota: son los incisos 1 a 4, la indemnización común] "
        "no se aplicará "
        "en el caso de terminación del contrato de los trabajadores "
        "de casa particular, respecto de los cuales regirán las "
        "siguientes normas:\n"
        "a) Tendrán derecho, cualquiera que sea la causa que "
        "origine la terminación del contrato, a una indemnización a "
        "todo evento que se financiará con un aporte del empleador, "
        "equivalente al 1,11% de la remuneración mensual imponible, "
        "la que se regirá, en cuanto corresponda, por las "
        "disposiciones de los artículos 165 y 166 de este Código, y\n"
        "b) La obligación de efectuar el aporte tendrá una duración "
        "de once años en relación con cada trabajador, plazo que se "
        "contará desde el 1º de enero de 1991, o desde la fecha de "
        "inicio de la relación laboral, si ésta fuere posterior. El "
        "monto de la indemnización quedará determinado por los "
        "aportes correspondientes al período respectivo, más la "
        "rentabilidad que se haya obtenido de ellos."
    ),
    (
        (
            "injustificad", "indebid", "improcedent", "reclam",
            "demand", "recargo",
        ),
        "[1] Art. 168. El trabajador cuyo contrato termine por "
        "aplicación de una o más de las causales establecidas en los "
        "artículos 159, 160 y 161, y que considere que dicha aplicación "
        "es injustificada, indebida o improcedente, o que no se haya "
        "invocado ninguna causal legal, podrá recurrir al juzgado "
        "competente, dentro del plazo de sesenta días hábiles, contado "
        "desde la separación, a fin de que éste así lo declare. En este "
        "caso, el juez ordenará el pago de la indemnización a que se "
        "refiere el inciso cuarto del artículo 162 y la de los incisos "
        "primero o segundo del artículo 163, según correspondiere, "
        "aumentada esta última de acuerdo a las siguientes reglas:\n"
        "a) En un treinta por ciento, si se hubiere dado término por "
        "aplicación improcedente del artículo 161;\n"
        "b) En un cincuenta por ciento, si se hubiere dado término por "
        "aplicación injustificada de las causales del artículo 159 o no "
        "se hubiere invocado ninguna causa legal para dicho término;\n"
        "c) En un ochenta por ciento, si se hubiere dado término por "
        "aplicación indebida de las causales del artículo 160.\n"
        "[2] Si el empleador hubiese invocado las causales señaladas en "
        "los números 1, 5 y 6 del artículo 160 y el despido fuere "
        "además declarado carente de motivo plausible por el tribunal, "
        "la indemnización establecida en los incisos primero o segundo "
        "del artículo 163, según correspondiere, se incrementará en un "
        "cien por ciento.\n"
        "[3] En el caso de las denuncias de acoso sexual, el empleador "
        "que haya cumplido con su obligación en los términos que "
        "señalan el artículo 153, inciso segundo, y el Título IV del "
        "Libro II, [nota: el artículo 153 y el Título IV del Libro II "
        "fijan esa obligación del empleador y este corpus no los "
        "incluye] no estará afecto al recargo de la indemnización a que "
        "hubiere lugar, en caso de que el despido sea declarado "
        "injusto, indebido o improcedente.\n"
        "[4] Si el juez estableciere que la aplicación de una o más de "
        "las causales de terminación del contrato establecidas en los "
        "artículos 159 y 160 no ha sido acreditada, de conformidad a lo "
        "dispuesto en este artículo, se entenderá que el término del "
        "contrato se ha producido por alguna de las causales señaladas "
        "en el artículo 161, en la fecha en que se invocó la causal, y "
        "habrá derecho a los incrementos legales que corresponda en "
        "conformidad a lo dispuesto en los incisos anteriores.\n"
        "[5] El plazo contemplado en el inciso primero [nota: es el "
        "inciso 1, el plazo de sesenta días hábiles contado desde la "
        "separación] se suspenderá cuando, dentro de éste, el "
        "trabajador interponga un reclamo por cualquiera de las "
        "causales indicadas, ante la Inspección del Trabajo respectiva. "
        "Dicho plazo seguirá corriendo una vez concluido este trámite "
        "ante dicha Inspección. No obstante lo anterior, en ningún caso "
        "podrá recurrirse al tribunal transcurridos noventa días "
        "hábiles desde la separación del trabajador."
    ),
    (
        (
            "tope", "unidades de fomento", "base de calculo",
            "ultima remuneracion mensual", "remuneraciones variables",
            "sobretiempo",
        ),
        "[1] Art. 172. Para los efectos del pago de las indemnizaciones "
        "a que se refieren los artículos 163, 163 bis, 168, 169, 170 y "
        "171, la última remuneración mensual comprenderá toda cantidad "
        "que estuviere percibiendo el trabajador por la prestación de "
        "sus servicios al momento de terminar el contrato, incluidas "
        "las imposiciones y cotizaciones de previsión o seguridad "
        "social de cargo del trabajador y las regalías o especies "
        "avaluadas en dinero, con exclusión de la asignación familiar "
        "legal, pagos por sobretiempo y beneficios o asignaciones que "
        "se otorguen en forma esporádica o por una sola vez al año, "
        "tales como gratificaciones y aguinaldos de navidad. [nota: de "
        "los artículos que enumera, este corpus incluye el 163 y el "
        "168, y no incluye el 163 bis, el 169, el 170 ni el 171]\n"
        "[2] Si se tratare de remuneraciones variables, la "
        "indemnización se calculará sobre la base del promedio "
        "percibido por el trabajador en los últimos tres meses "
        "calendario.\n"
        "[3] Con todo, para los efectos de las indemnizaciones "
        "establecidas en este título [nota: son las que el inciso "
        "primero enumera, los artículos 163, 163 bis, 168, 169, 170 y "
        "171], no se considerará una remuneración mensual superior a 90 "
        "unidades de fomento del último día del mes anterior al pago, "
        "limitándose a dicho monto la base de cálculo."
    ),
    (
        ("finiquit",),
        "[1] Art. 177. El finiquito, la renuncia y el mutuo acuerdo "
        "deberán constar por escrito. El instrumento respectivo que "
        "no fuere firmado por el interesado y por el presidente del "
        "sindicato o el delegado sindical respectivos, o que no "
        "fuere ratificado por el trabajador ante el inspector del "
        "trabajo, no podrá ser invocado por el empleador. El "
        "finiquito deberá ser otorgado por el empleador y puesto su "
        "pago a disposición del trabajador dentro de diez días "
        "hábiles, contados desde la separación del trabajador. Las "
        "partes podrán pactar el pago en cuotas de conformidad con "
        "los artículos 63 bis y 169.\n"
        "[nota: el artículo continúa con doce incisos más, que "
        "regulan quiénes pueden actuar como ministro de fe, el "
        "finiquito electrónico ante la Dirección del Trabajo, la "
        "reserva de derechos y la acreditación del pago de las "
        "cotizaciones]"
    ),
)


def buscar_articulos(consulta):
    """Devuelve el texto de los artículos que tratan el tema consultado.

    Recibe la consulta en lenguaje natural y la compara contra las
    claves de ARTICULOS, sin tildes y por subcadena, de modo que
    "indemnización por años de servicio" y "me despidieron" encuentran
    lo suyo sin tener que coincidir palabra por palabra.

    Para una consulta de texto devuelve siempre un texto, también
    cuando no encuentra nada, para que quien la llame tenga algo con
    lo que seguir.

    Si le llega algo que no es texto, lanza. No se atrapa porque el
    args_schema de la herramienta que la envuelve valida el tipo
    antes de invocarla, y un control de tipo repetido en los dos
    lados oculta dónde estaba el error cuando aparece.
    """

    pregunta = sin_tildes(consulta)

    # Devuelve todas las coincidencias y no solo la primera, porque un
    # mismo tema puede estar repartido en varios artículos. Preguntar
    # por el despido toca el 160 y el 161 a la vez.
    encontrados = [
        texto
        for claves, texto in ARTICULOS
        if any(sin_tildes(clave) in pregunta for clave in claves)
    ]

    if not encontrados:
        return (
            "No encontré un artículo sobre ese tema en los que tengo "
            "cargados."
        )

    # El encabezado va una vez por respuesta y no una vez por
    # artículo, para no repetirlo cuando calcen varios.
    return (
        "Texto del Código del Trabajo de Chile. Los números entre "
        "corchetes marcan los incisos del artículo.\n\n"
        + "\n\n".join(encontrados)
    )

