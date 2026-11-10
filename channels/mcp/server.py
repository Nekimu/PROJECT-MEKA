"""Canal MCP: MEKA como herramienta de Claude Desktop, Claude Code, Gemini CLI, Cursor...

Un agente externo puede hablar con el personaje, consultar su memoria y, sobre todo,
contarle a la mascota qué está haciendo (agent.working → agent.done), para que tu
compañera reaccione mientras el agente trabaja.

Se lanza con `python run.py mcp` (stdio). Ejemplo para Claude Desktop o Claude Code:

    {"mcpServers": {"meka": {"command": "python", "args": ["/ruta/a/PROJECT-MEKA/run.py", "mcp"]}}}

Requiere `pip install -r requirements-mcp.txt` y MEKA Core en marcha (`python run.py`).
"""

import functools
from typing import Literal

from channels.client import CoreClient, CoreUnavailableError
from core.config import default_user
from core.events import EMOTIONS

INSTRUCTIONS = (
    "MEKA es la compañera virtual del usuario: una mascota animada con personalidad. "
    "Usa pet_status al empezar ('working'), terminar ('done') o fallar ('error') una tarea "
    "larga para que la mascota reaccione. Usa chat solo si el usuario quiere hablar con MEKA."
)

STATES = {"working": "agent.working", "done": "agent.done", "error": "agent.error"}
DATA_KEYS = {"working": "task", "done": "summary", "error": "message"}


class MekaTools:
    """Las herramientas MCP. Separadas del servidor para poder probarlas sin el SDK."""

    def __init__(self, core: CoreClient, session: str, user: str):
        self.core = core
        self.session = session
        self.user = user

    async def chat(self, text: str) -> str:
        """Habla con MEKA, la compañera del usuario, y devuelve su respuesta."""
        replies = await self.core.chat(self.session, self.user, text, audio=False)
        return "\n\n".join(r["text"] for r in replies if r.get("text"))

    async def pet_status(self, state: Literal["working", "done", "error"], text: str = "") -> str:
        """Cuenta a la mascota qué haces: 'working' (con la tarea), 'done' (con un resumen)
        o 'error' (con el problema). La mascota se anima, celebra o se agobia."""
        if state not in STATES:
            raise ValueError(f"Estado no válido: {state!r}. Usa: {', '.join(STATES)}")
        data = {DATA_KEYS[state]: text} if text else {}
        delivered = await self.core.publish(STATES[state], **data)
        return f"Evento {STATES[state]} enviado a {delivered} cliente(s)."

    async def pet_emotion(self, emotion: str) -> str:
        """Cambia la expresión de la mascota (happy, thinking, celebrate, sad...)."""
        if emotion not in EMOTIONS:
            raise ValueError(f"Emoción no válida: {emotion!r}. Usa: {', '.join(sorted(EMOTIONS))}")
        delivered = await self.core.publish("emotion", emotion=emotion)
        return f"Emoción {emotion} enviada a {delivered} cliente(s)."

    async def remember(self, fact: str) -> str:
        """Guarda un dato del usuario en la memoria persistente de MEKA."""
        added = await self.core.remember(self.user, fact)
        return "Guardado." if added else "Ya lo sabía."

    async def memories(self) -> list[str]:
        """Lista lo que MEKA recuerda del usuario."""
        return await self.core.memories(self.user)

    def all(self):
        return [self.chat, self.pet_status, self.pet_emotion, self.remember, self.memories]


def _report_errors(tool, error_class):
    """Los errores esperados (argumento no válido, núcleo apagado) llegan al agente con su
    mensaje; el SDK oculta el texto de cualquier otra excepción."""

    @functools.wraps(tool)
    async def wrapper(*args, **kwargs):
        try:
            return await tool(*args, **kwargs)
        except (ValueError, CoreUnavailableError) as e:
            raise error_class(str(e)) from e

    return wrapper


def build_mcp(config: dict, core: CoreClient | None = None):
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.server.mcpserver.exceptions import ToolError
    except ImportError as e:
        raise SystemExit("Falta el SDK de MCP: pip install -r requirements-mcp.txt") from e

    mcp_config = config.get("mcp", {})
    tools = MekaTools(
        core or CoreClient.from_config(config),
        session=str(mcp_config.get("session") or "mcp"),
        user=str(mcp_config.get("user") or default_user(config)),
    )
    server = MCPServer(name="MEKA", instructions=INSTRUCTIONS)
    for tool in tools.all():
        server.add_tool(_report_errors(tool, ToolError))
    return server


def run_mcp(config: dict):
    build_mcp(config).run("stdio")
