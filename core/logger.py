import logging
import sys
from typing import ClassVar

from colorama import Fore, Style, init

# Inicializar colorama para Windows
init(autoreset=True)

ROOT_LOGGER_NAME = "meka"


class ColorFormatter(logging.Formatter):
    """Formateador personalizado para logs con colores."""

    COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"


def configure_logging(level: str | int | None = None) -> logging.Logger:
    """Configura (una sola vez) el logger raíz del proyecto y, opcionalmente, su nivel."""
    root = logging.getLogger(ROOT_LOGGER_NAME)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            ColorFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
            )
        )
        root.addHandler(handler)
        root.propagate = False
    if level is not None:
        try:
            root.setLevel(level.upper() if isinstance(level, str) else level)
        except (ValueError, TypeError):
            root.setLevel(logging.INFO)
            root.warning(f"Nivel de log inválido en app.log_level: {level!r}. Se usa INFO.")
    elif root.level == logging.NOTSET:
        root.setLevel(logging.INFO)
    return root


def setup_logger(name: str = "NoviaBot") -> logging.Logger:
    """Devuelve un logger hijo de 'meka'; el nivel se controla con `app.log_level`."""
    configure_logging()
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def log_conversation(role, message):
    """Imprime la conversación en la consola con colores específicos."""
    if role.lower() == "user":
        print(f"\n{Fore.BLUE}{Style.BRIGHT}Tú: {Style.RESET_ALL}{message}")
    elif role.lower() in ["ai", "assistant", "marin"]:
        print(f"{Fore.MAGENTA}{Style.BRIGHT}Marin: {Style.RESET_ALL}{message}\n")
    else:
        print(f"{Fore.WHITE}{role}: {message}")
