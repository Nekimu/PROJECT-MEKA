import os
import yaml
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def load_config(config_path="config.yml"):
    """
    Carga la configuración desde un archivo YAML y superpone variables de entorno.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Superponer secretos desde variables de entorno
    if os.getenv("TELEGRAM_TOKEN"):
        if "telegram" not in config:
            config["telegram"] = {}
        config["telegram"]["token"] = os.getenv("TELEGRAM_TOKEN")
        
    # Validar configuración crítica
    if not config.get("telegram", {}).get("token"):
        print("ADVERTENCIA: No se ha configurado el token de Telegram en .env")

    return config

# Instancia global de configuración
try:
    settings = load_config()
except Exception as e:
    print(f"Error cargando configuración: {e}")
    settings = {}
