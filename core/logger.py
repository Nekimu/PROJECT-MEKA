import logging
import sys
from colorama import init, Fore, Style

# Inicializar colorama para Windows
init(autoreset=True)

class ColorFormatter(logging.Formatter):
    """Formateador personalizado para logs con colores."""
    
    COLORS = {
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

def setup_logger(name="NoviaBot", level=logging.INFO):
    """Configura y devuelve un logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(handler)

    return logger

# Logger específico para la conversación
def log_conversation(role, message):
    """Imprime la conversación en la consola con colores específicos."""
    if role.lower() == "user":
        print(f"\n{Fore.BLUE}{Style.BRIGHT}Tú: {Style.RESET_ALL}{message}")
    elif role.lower() in ["ai", "assistant", "marin"]:
        print(f"{Fore.MAGENTA}{Style.BRIGHT}Marin: {Style.RESET_ALL}{message}\n")
    else:
        print(f"{Fore.WHITE}{role}: {message}")
