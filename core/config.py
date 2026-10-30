"""Carga de configuración: `config.yml` + secretos desde variables de entorno (`.env`)."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from core.logger import setup_logger

logger = setup_logger("Config")

# Raíz del proyecto: las rutas relativas se resuelven contra ella y no contra el
# directorio desde el que se lance `python run.py`.
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.yml"
PLACEHOLDER_TOKENS = {"tu_token_aqui", "tu_token_aqui_sin_comillas"}

load_dotenv(BASE_DIR / ".env")


def resolve_path(path: str | os.PathLike) -> Path:
    """Convierte una ruta relativa de la configuración en absoluta respecto a la raíz."""
    path = Path(path).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


def parse_user_ids(raw) -> list[int]:
    """Convierte "123, 456" (o una lista) en [123, 456] sin duplicados, ignorando inválidos."""
    if raw is None:
        return []
    items = raw.split(",") if isinstance(raw, str) else raw
    ids: list[int] = []
    for item in items:
        item = str(item).strip()
        if not item:
            continue
        try:
            user_id = int(item)
        except ValueError:
            logger.warning(f"ID de usuario inválido en ALLOWED_USER_IDS: {item!r}")
            continue
        if user_id not in ids:
            ids.append(user_id)
    return ids


def is_valid_token(token: str | None) -> bool:
    return bool(token) and token not in PLACEHOLDER_TOKENS


def load_config(config_path: str | os.PathLike | None = None) -> dict:
    """
    Carga la configuración desde un archivo YAML y superpone variables de entorno.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {path}")

    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Superponer secretos desde variables de entorno
    telegram = config.setdefault("telegram", {})
    if os.getenv("TELEGRAM_TOKEN"):
        telegram["token"] = os.getenv("TELEGRAM_TOKEN").strip()

    env_ids = os.getenv("ALLOWED_USER_IDS")
    telegram["allowed_user_ids"] = parse_user_ids(
        env_ids if env_ids is not None else telegram.get("allowed_user_ids")
    )

    # Validar configuración crítica
    if not is_valid_token(telegram.get("token")):
        logger.warning("No se ha configurado el token de Telegram en .env")

    return config


# Instancia global de configuración
try:
    settings = load_config()
except Exception as e:
    logger.error(f"Error cargando configuración: {e}")
    settings = {}
