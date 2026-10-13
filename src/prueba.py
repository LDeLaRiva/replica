from rich import print as rprint
from rich.table import Table
from rich.panel import Panel
from termcolor import cprint

print("--- termcolor ---")
cprint("rojo", "red")
cprint("verde y negrita", "green", attrs=["bold"])
cprint("fondo amarillo", "black", "on_yellow")

print()
print("--- rich ---")
rprint("[bold red]rojo y negrita[/bold red]")
rprint("[green]verde[/green] y [blue]azul[/blue]")

tabla = Table(title="Mis dependencias")
tabla.add_column("Librería")
tabla.add_column("Para qué sirve")
tabla.add_row("requests", "hablar con una API")
tabla.add_row("google-genai", "hablar con Gemini")
rprint(tabla)

rprint(Panel("Esto es un recuadro con borde", title="rich"))