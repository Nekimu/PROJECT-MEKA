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
    "larga para que la mascota reaccione. Antes de algo irreversible (borrar, enviar, publicar) "
    "usa ask_permission: el usuario decide desde la mascota. Para leer archivos del usuario usa "
    "list_folders, list_files, read_file y search_files (solo las carpetas que él autorizó). En "
    "las carpetas writable puedes write_file, move_file, delete_file y make_folder: cada cambio "
    "pide permiso al usuario en la mascota y se puede deshacer con undo_last_change. "
    "Usa chat solo si el usuario quiere hablar con MEKA."
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

    async def memories(self, query: str = "") -> list[str]:
        """Lo que MEKA recuerda del usuario. Con `query`, solo lo relacionado con ese tema
        (busca por significado: "mascotas" encuentra "mi perro se llama Toby").
        Nunca devuelve recuerdos privados: el agente los enviaría a su proveedor en la nube."""
        return await self.core.memories(self.user, query or None, include_private=False)

    async def tasks(self) -> list[dict]:
        """Tareas pendientes del usuario (las de fecha más cercana primero; fechas en epoch).
        Nunca devuelve las privadas: el agente las enviaría a su proveedor en la nube."""
        return await self.core.tasks(self.user, include_private=False)

    async def add_task(self, title: str, when: str = "") -> dict:
        """Apunta una tarea en la agenda de MEKA, que se la recordará al usuario. `when` en
        español natural y opcional: «mañana a las 5», «el viernes», «antes del 15 de noviembre»."""
        return await self.core.add_task(self.user, title, when or None, source="mcp")

    async def complete_task(self, task_id: int) -> str:
        """Marca una tarea como hecha (usa el `id` que devuelve `tasks`)."""
        await self.core.task_action(self.user, task_id, "done")
        return "Tarea marcada como hecha."

    async def ask_permission(self, action: str, timeout_seconds: int = 120) -> str:
        """Pide permiso al usuario antes de una acción delicada (borrar, enviar, publicar...).
        La mascota muestra el diálogo y esta herramienta espera la respuesta. Sin respuesta a
        tiempo (máximo 600 s) la respuesta es NO: no hagas la acción."""
        timeout = max(5, min(int(timeout_seconds), 600))
        approved = await self.core.ask_permission(action, timeout=timeout)
        return "APROBADO: puedes continuar." if approved else "DENEGADO: no hagas la acción."

    # ------------------------------------------------------------------ manos (solo lectura)
    # Nunca carpetas privadas: el agente envía lo que lee a su proveedor en la nube.

    async def list_folders(self) -> list[dict]:
        """Carpetas que el usuario autorizó a MEKA (solo lectura). Úsalas por su nombre."""
        return (await self.core.hands("folders", include_private=False))["folders"]

    async def list_files(self, folder: str, path: str = ".", pattern: str = "") -> dict:
        """Contenido de una carpeta autorizada. `path` es relativo a ella; `pattern` filtra
        (p. ej. "*.pdf")."""
        return await self.core.hands(
            "list", folder, path=path, pattern=pattern or None, include_private=False
        )

    async def read_file(self, folder: str, path: str) -> dict:
        """Texto de un archivo de una carpeta autorizada (también PDF, DOCX y XLSX)."""
        return await self.core.hands("read", folder, path=path, include_private=False)

    async def search_files(self, folder: str, query: str, content: bool = True) -> dict:
        """Busca archivos por nombre y, con `content`, también dentro de los de texto."""
        return await self.core.hands(
            "search", folder, q=query, content=content, include_private=False
        )

    async def write_file(self, folder: str, path: str, content: str, overwrite: bool = False):
        """Crea (o con `overwrite`, reemplaza) un archivo de texto en una carpeta writable.
        Pide permiso al usuario y espera su respuesta; si lo niega, no se hace nada."""
        body = {"path": path, "content": content, "overwrite": overwrite}
        return await self.core.hands_change("write", folder, body, include_private=False)

    async def move_file(self, folder: str, src: str, dest: str) -> dict:
        """Mueve o renombra un archivo dentro de una carpeta writable (nunca sobrescribe)."""
        body = {"src": src, "dest": dest}
        return await self.core.hands_change("move", folder, body, include_private=False)

    async def delete_file(self, folder: str, path: str) -> dict:
        """Borra UN archivo de una carpeta writable (nunca carpetas). Se puede deshacer."""
        return await self.core.hands_change("delete", folder, {"path": path}, include_private=False)

    async def make_folder(self, folder: str, path: str) -> dict:
        """Crea una subcarpeta dentro de una carpeta writable."""
        return await self.core.hands_change("mkdir", folder, {"path": path}, include_private=False)

    async def undo_last_change(self, folder: str) -> dict:
        """Deshace el último cambio de MEKA en esa carpeta (también pide permiso)."""
        return await self.core.hands_change("undo", folder, include_private=False)

    def all(self):
        return [
            self.chat,
            self.pet_status,
            self.pet_emotion,
            self.remember,
            self.memories,
            self.ask_permission,
            self.tasks,
            self.add_task,
            self.complete_task,
            self.list_folders,
            self.list_files,
            self.read_file,
            self.search_files,
            self.write_file,
            self.move_file,
            self.delete_file,
            self.make_folder,
            self.undo_last_change,
        ]


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
