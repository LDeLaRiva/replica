from dotenv import load_dotenv
import os

load_dotenv()  # Carga las variables de entorno desde el archivo .env

print(os.getenv("AI_API_KEY"))