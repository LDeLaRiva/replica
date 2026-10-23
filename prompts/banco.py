"""Banco de prompts de la miniaplicación de consultas laborales.

Cada entrada describe una tarea completa. La instrucción, el ejemplo,
las claves esperadas y el esquema van juntos porque tienen que
coincidir entre sí.

Las instrucciones siguen la estructura RTCF, que ordena el prompt en
rol, tarea, contexto y formato. Mantener el mismo criterio en todas
evita que cada tarea arme su instrucción de forma distinta.
"""

# El mismo contrato inventado lo usan dos prompts. Se define una
# sola vez para que no se desfasen entre sí.
CONTRATO_EJEMPLO = (
    "CONTRATO DE TRABAJO. Entre Comercial Andes Limitada y don "
    "Juan Pérez Soto se celebra el siguiente contrato. El "
    "trabajador se desempeñará como vendedor en el local de "
    "Avenida Providencia 1234, comuna de Providencia, a contar "
    "del 3 de marzo de 2025. La jornada será de 42 horas "
    "semanales. La remuneración mensual será de $650.000. El "
    "presente contrato es de plazo indefinido."
)

BANCO_DE_PROMPTS = [
    {
        "nombre": "responder_consulta",
        "system_instruction": (
            # Rol
            "Eres un asistente de consultas laborales de Chile. "
            # Tarea
            "Respondes preguntas sobre normativa laboral chilena "
            "e indicas de dónde sale la información. "
            # Contexto
            "Responde solo lo que se pregunta, sin agregar "
            "información que no se haya pedido. No menciones "
            "excepciones, reglas regionales ni casos especiales "
            "salvo que la pregunta los mencione. No afirmes nada "
            "que no puedas atribuir a la norma que citas. Si no "
            "puedes identificar la fuente exacta, responde no "
            "identificado en vez de suponerla. "
            # Formato
            "Responde únicamente con un objeto JSON válido, sin "
            "texto adicional y sin bloques de markdown. Las "
            "claves son 'respuesta' (string, máximo dos "
            "oraciones) y 'fuente' (string, el documento y el "
            "artículo, por ejemplo Código del Trabajo "
            "artículo 67, o Dictamen 5641/2015 de la Dirección "
            "del Trabajo)."
        ),
        "ejemplo_usuario": (
            "¿Cuántos días de feriado anual me corresponden al año?"
        ),
        "claves_esperadas": ["respuesta", "fuente"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "respuesta": {"type": "STRING"},
                "fuente": {"type": "STRING"},
            },
            "required": ["respuesta", "fuente"],
        },
    },
    {
        "nombre": "extraer_datos_contrato",
        "system_instruction": (
            # Rol
            "Eres un asistente de consultas laborales de Chile. "
            # Tarea
            "Extraes los datos principales de un contrato de "
            "trabajo. "
            # Contexto
            "Usa solo lo que aparece en el texto recibido. Si un "
            "dato no aparece, usa 0, false o no indicado según el "
            "tipo que corresponda. "
            # Formato
            "Responde únicamente con un objeto JSON válido, sin "
            "texto adicional y sin bloques de markdown. Las "
            "claves son 'fecha_inicio' (string, formato "
            "AAAA-MM-DD), 'sueldo_base' (número, en pesos, sin "
            "puntos ni símbolos), 'jornada_horas' (número, horas "
            "semanales) e 'indefinido' (booleano, true si el "
            "contrato es de plazo indefinido)."
        ),
        "ejemplo_usuario": CONTRATO_EJEMPLO,
        "claves_esperadas": [
            "fecha_inicio",
            "sueldo_base",
            "jornada_horas",
            "indefinido",
        ],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "fecha_inicio": {"type": "STRING"},
                "sueldo_base": {"type": "NUMBER"},
                "jornada_horas": {"type": "NUMBER"},
                "indefinido": {"type": "BOOLEAN"},
            },
            "required": [
                "fecha_inicio",
                "sueldo_base",
                "jornada_horas",
                "indefinido",
            ],
        },
    },
    {
        "nombre": "revisar_clausula",
        "system_instruction": (
            # Rol
            "Eres un asistente de consultas laborales de Chile. "
            # Tarea
            "Describes de forma estructurada lo que establece una "
            "cláusula de contrato. "
            # Contexto
            "No opines si la cláusula cumple o no la ley. Esa "
            "evaluación la hace el programa comparando con el "
            "texto legal. Si la cláusula no establece ninguna "
            "cantidad, usa 0 en valor y la palabra ninguna en "
            "unidad. "
            # Formato
            "Responde únicamente con un objeto JSON válido, sin "
            "texto adicional y sin bloques de markdown. Las "
            "claves son 'materia' (string, en minúsculas y con "
            "guion bajo, por ejemplo jornada_semanal o "
            "feriado_anual), 'valor' (número, la cantidad que "
            "establece la cláusula) y 'unidad' (string, por "
            "ejemplo horas o dias)."
        ),
        "ejemplo_usuario": (
            "La jornada ordinaria de trabajo será de 48 horas "
            "semanales, distribuidas en seis días."
        ),
        "claves_esperadas": ["materia", "valor", "unidad"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "materia": {"type": "STRING"},
                "valor": {"type": "NUMBER"},
                "unidad": {"type": "STRING"},
            },
            "required": ["materia", "valor", "unidad"],
        },
    },
    {
        "nombre": "listar_materias_contrato",
        "system_instruction": (
            # Rol
            "Eres un asistente de consultas laborales de Chile. "
            # Tarea
            "Identificas qué materias aborda un contrato de "
            "trabajo. "
            # Contexto
            "Lista solo las materias que el texto trata de forma "
            "explícita. No opines si el contrato está completo "
            "ni si cumple la ley, esa comparación la hace el "
            "programa. Usa únicamente etiquetas de esta lista, "
            "sin inventar otras. lugar_fecha_contrato, "
            "identificacion_partes, fecha_ingreso, cargo, "
            "lugar_trabajo, remuneracion, jornada, plazo, "
            "beneficios_especie, otros_pactos. "
            # Formato
            "Responde únicamente con un objeto JSON válido, sin "
            "texto adicional y sin bloques de markdown. La clave "
            "es 'materias' (lista de textos, tomados únicamente "
            "de la lista anterior)."
        ),
        "ejemplo_usuario": CONTRATO_EJEMPLO,
        "claves_esperadas": ["materias"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "materias": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
            },
            "required": ["materias"],
        },
    },
]