# Salida con color para la terminal, sin dependencias.
# Color exacto en RGB, así que no depende del tema de VS Code.
# Tonos elegidos para fondo claro y fotosensibilidad, sin blancos ni saturados.
#
# Terminaciones de los atajos
#   sin nada   solo texto en color
#   n          texto en color con negrita
#   b          barra de color al inicio
#   bn         barra de color al inicio, con negrita
#   f          fondo suave
#   fn         fondo suave, con negrita

RESET = "\033[0m"

# nombre -> (color de texto oscuro, color de fondo suave)
TONOS = {
    "verde":  ((13, 70, 36),   (198, 230, 205)),
    "fucsia": ((155, 15, 125), (250, 212, 240)),
    "vino":   ((145, 25, 45),  (250, 212, 220)),
    "ambar":  ((120, 60, 8),   (250, 226, 180)),
    "azul":   ((23, 52, 128),  (205, 222, 250)),
    "lila": ((88, 28, 135),  (231, 216, 250)),
    "teal":   ((14, 94, 92),   (198, 234, 232)),
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


# ---------- las tres formas, para elegir el color a mano ----------

def color(texto, tono="verde", negrita=True):
    """Solo el texto en color, lo más suave."""
    oscuro, _ = TONOS[tono]
    estilo = _texto(oscuro, negrita)
    for linea in str(texto).split("\n"):
        print(f"{estilo}{linea}{RESET}" if linea.strip() else "")


def barra(texto, tono="verde", negrita=True):
    """Barra de color al inicio de cada línea, área mínima."""
    oscuro, _ = TONOS[tono]
    marca = f"{_fondo(oscuro)}   {RESET}"
    estilo = _texto(oscuro, negrita)
    for linea in str(texto).split("\n"):
        print(f"{marca} {estilo}{linea}{RESET}" if linea.strip() else "")


def caja(texto, tono="verde", negrita=True):
    """Fondo suave con texto oscuro del mismo tono, parejo de los dos lados."""
    oscuro, claro = TONOS[tono]
    lineas = str(texto).split("\n")
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