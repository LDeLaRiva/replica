"""Salida con color para la terminal, sin dependencias externas.

Los colores van en RGB exacto, así que no dependen del tema de VS
Code y se ven igual en cualquier terminal.

Los tonos están pensados para una terminal de fondo claro. Usan
texto oscuro sobre fondos suaves, en vez de texto blanco o colores
saturados, porque esos contrastes me generan incomodidad visual
dificultando la lectura a causa de la fotosensibilidad.

Terminaciones de los atajos:
    sin nada   solo texto en color
    n          texto en color con negrita
    b          barra de color al inicio
    bn         barra de color al inicio, con negrita
    f          fondo suave
    fn         fondo suave, con negrita
    t          tabla de clave y valor en columna, con barra
"""

import shutil
import textwrap

RESET = "\033[0m"

# nombre -> (color de texto oscuro, color de fondo suave)
TONOS = {
    "verde":  ((13, 70, 36),   (198, 230, 205)),
    "fucsia": ((155, 15, 125), (250, 212, 240)),
    "vino":   ((145, 25, 45),  (250, 212, 220)),
    "ambar":   ((120, 60, 8),   (247, 232, 206)),
    "azul":   ((23, 52, 128),  (205, 222, 250)),
    "lila": ((88, 28, 135),  (231, 216, 250)),
    "teal":   ((58, 70, 82),   (226, 231, 237)),
}




def _texto(rgb, negrita):
    """Código de color de texto. El guion bajo avisa que es de uso interno."""
    r, g, b = rgb
    peso = "1;" if negrita else ""
    return f"\033[{peso}38;2;{r};{g};{b}m"


def _fondo(rgb):
    """Código de color de fondo."""
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m"


# ---------- las cuatro formas, para elegir el color a mano ----------

def color(texto, tono="verde", negrita=True):
    """Solo el texto en color, lo más suave."""
    oscuro, _ = TONOS[tono]
    estilo = _texto(oscuro, negrita)
    for linea in str(texto).split("\n"):
        print(f"{estilo}{linea}{RESET}" if linea.strip() else "")

def barra(texto, tono="verde", negrita=True):
    """Barra de color al inicio de cada línea, también en las que se parten.

    El fondo suave va detrás del texto, no solo el color de la letra.
    Sin fondo, el texto oscuro queda ilegible en una terminal de tema
    oscuro, porque el contraste cae de 10 a 1,5, y el mínimo legible
    es 4,5. Con el fondo puesto se lee igual en cualquier tema, porque
    el color del editor deja de participar.
    """
    oscuro, claro = TONOS[tono]
    marca = f"{_fondo(oscuro)}   {RESET}"
    estilo = f"{_fondo(claro)}{_texto(oscuro, negrita)}"
    ancho = max(shutil.get_terminal_size((80, 20)).columns - 5, 20)
    for parrafo in str(texto).split("\n"):
        if not parrafo.strip():
            print()
            continue
        for linea in textwrap.wrap(parrafo, ancho):
            print(f"{marca}{estilo} {linea} {RESET}")

def tabla(pares, tono="verde", negrita=True):
    """Pares de clave y valor en columna, con el valor alineado.

    El ancho de la primera columna sale de la clave más larga, así
    que sirve para cualquier diccionario sin saber sus claves. El
    valor se parte antes de imprimirlo, si no la continuación se
    descuelga hasta el margen izquierdo y deja de leerse como
    columna.
    """
    if not pares:
        return
    ancho = max(len(str(clave)) for clave in pares)
    sangria = 2 + ancho + 2
    libre = max(
        shutil.get_terminal_size((80, 20)).columns - 5 - sangria, 1)
    for clave, valor in pares.items():
        trozos = textwrap.wrap(str(valor), libre) or [""]
        barra(f"  {str(clave):<{ancho}}  {trozos[0]}", tono, negrita)
        for trozo in trozos[1:]:
            barra(f"{' ' * sangria}{trozo}", tono, negrita)

def caja(texto, tono="verde", negrita=True):
    """Fondo suave con texto oscuro del mismo tono, parejo de los dos lados."""
    oscuro, claro = TONOS[tono]
    disponible = max(shutil.get_terminal_size((80, 20)).columns - 4, 20)
    lineas = []
    for parrafo in str(texto).split("\n"):
        if parrafo.strip():
            lineas.extend(textwrap.wrap(parrafo, disponible))
        else:
            lineas.append("")
    ancho = max([len(l) for l in lineas], default=0)
    estilo = f"{_fondo(claro)}{_texto(oscuro, negrita)}"
    for linea in lineas:
        print(f"{estilo} {linea:<{ancho}} {RESET}" if linea.strip() else "")


# ---------- titulo, azul. Encabezados ----------

def titulo(texto):
    color(texto, "azul", negrita=False)

def titulon(texto):
    color(texto, "azul", negrita=True)

def titulob(texto):
    barra(texto, "azul", negrita=False)

def titulobn(texto):
    barra(texto, "azul", negrita=True)

def titulof(texto):
    caja(texto, "azul", negrita=False)

def titulofn(texto):
    caja(texto, "azul", negrita=True)

def titulot(pares):
    tabla(pares, "azul", negrita=True)


# ---------- exito, verde. Algo salió bien ----------

def exito(texto):
    color(texto, "verde", negrita=False)

def exiton(texto):
    color(texto, "verde", negrita=True)

def exitob(texto):
    barra(texto, "verde", negrita=False)

def exitobn(texto):
    barra(texto, "verde", negrita=True)

def exitof(texto):
    caja(texto, "verde", negrita=False)

def exitofn(texto):
    caja(texto, "verde", negrita=True)

def exitot(pares):
    tabla(pares, "verde", negrita=True)


# ---------- aviso, ambar. Advertencias ----------

def aviso(texto):
    color(texto, "ambar", negrita=False)

def avison(texto):
    color(texto, "ambar", negrita=True)

def avisob(texto):
    barra(texto, "ambar", negrita=False)

def avisobn(texto):
    barra(texto, "ambar", negrita=True)

def avisof(texto):
    caja(texto, "ambar", negrita=False)

def avisofn(texto):
    caja(texto, "ambar", negrita=True)

def avisot(pares):
    tabla(pares, "ambar", negrita=True)


# ---------- error, vino. Algo falló ----------

def error(texto):
    color(texto, "vino", negrita=False)

def erroron(texto):
    color(texto, "vino", negrita=True)

def errorb(texto):
    barra(texto, "vino", negrita=False)

def errorbn(texto):
    barra(texto, "vino", negrita=True)

def errorf(texto):
    caja(texto, "vino", negrita=False)

def errorfn(texto):
    caja(texto, "vino", negrita=True)

def errort(pares):
    tabla(pares, "vino", negrita=True)


# ---------- sal, fucsia. El resultado principal ----------

def sal(texto):
    color(texto, "fucsia", negrita=False)

def saln(texto):
    color(texto, "fucsia", negrita=True)

def salb(texto):
    barra(texto, "fucsia", negrita=False)

def salbn(texto):
    barra(texto, "fucsia", negrita=True)

def salf(texto):
    caja(texto, "fucsia", negrita=False)

def salfn(texto):
    caja(texto, "fucsia", negrita=True)

def salt(pares):
    tabla(pares, "fucsia", negrita=True)


# ---------- nota, teal. Comentarios al margen ----------

def nota(texto):
    color(texto, "teal", negrita=False)

def notan(texto):
    color(texto, "teal", negrita=True)

def notab(texto):
    barra(texto, "teal", negrita=False)

def notabn(texto):
    barra(texto, "teal", negrita=True)

def notaf(texto):
    caja(texto, "teal", negrita=False)

def notafn(texto):
    caja(texto, "teal", negrita=True)

def notat(pares):
    tabla(pares, "teal", negrita=True)


# ---------- lila. Para destacar algo sin alarmar ----------

def lila(texto):
    color(texto, "lila", negrita=False)

def lilan(texto):
    color(texto, "lila", negrita=True)

def lilab(texto):
    barra(texto, "lila", negrita=False)

def lilabn(texto):
    barra(texto, "lila", negrita=True)

def lilaf(texto):
    caja(texto, "lila", negrita=False)

def lilafn(texto):
    caja(texto, "lila", negrita=True)

def lilat(pares):
    tabla(pares, "lila", negrita=True)