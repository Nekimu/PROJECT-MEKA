"""Las "manos" de MEKA (fase 3): leer y, con permiso, cambiar carpetas que el usuario autoriza.

La política (qué se puede tocar) está en policy.py; la lectura en reader.py; los cambios
(con permiso, punto de restauración y deshacer) en changes.py, writer.py y restore.py. Cada acción
queda en el registro de ejecución (sin rutas ni contenido) y las búsquedas avisan a la
mascota con agent.working → agent.done.
"""

import asyncio
import time

from core.confirmations import ConfirmationRegistry
from core.events import EventBus
from core.hands import reader
from core.hands.changes import ChangesMixin
from core.hands.policy import Folder, HandsError, parse_folders
from core.hands.restore import RestorePoints
from core.logger import setup_logger
from core.runs import Run, RunLog

__all__ = ["Hands", "HandsError"]

logger = setup_logger("Hands")


class Hands(ChangesMixin):
    def __init__(
        self,
        config: dict,
        bus: EventBus | None = None,
        runs: RunLog | None = None,
        *,
        confirmations: ConfirmationRegistry | None = None,
        restore_points: RestorePoints | None = None,
    ):
        hands = config.get("hands") or {}
        self.enabled = bool(hands.get("enabled", True))
        self.folders = parse_folders(config) if self.enabled else {}
        self.denied = tuple(hands.get("deny") or ())
        self.max_chars = int(hands.get("max_read_chars", 20_000))
        self.max_results = int(hands.get("max_results", 200))
        self.max_files = int(hands.get("max_scanned_files", 5_000))
        self.max_write_chars = int(hands.get("max_write_chars", 200_000))
        self.bus = bus
        self.runs = runs
        self.confirmations = confirmations
        self.restore_points = restore_points
        for folder in self.folders.values():
            if not folder.root.is_dir():
                logger.warning(f"Carpeta autorizada '{folder.name}' no existe: {folder.root}")

    def list_folders(self, *, include_private: bool = True) -> list[dict]:
        return [f.public() for f in self.folders.values() if include_private or not f.private]

    def _folder(self, name: str, include_private: bool) -> Folder:
        folder = self.folders.get(name)
        if folder is None or (folder.private and not include_private):
            raise HandsError(f"No hay ninguna carpeta autorizada llamada {name!r}", 404)
        if not folder.root.is_dir():
            raise HandsError(f"La carpeta autorizada {name!r} no existe en este equipo", 404)
        return folder

    async def _run(self, action: str, name: str, include_private: bool, func, **kwargs) -> dict:
        start, error = time.perf_counter(), None
        try:
            folder = self._folder(name, include_private)
            return await asyncio.to_thread(func, folder, denied=self.denied, **kwargs)
        except HandsError as e:
            error = e
            raise
        finally:
            self._record(action, name, int((time.perf_counter() - start) * 1000), error)

    def _record(self, action: str, folder: str, latency_ms: int, error):
        """Registro de lo que hacen las manos: acción, carpeta y resultado. Sin rutas ni texto."""
        logger.info(f"Manos: {action} en '{folder}' -> {'ok' if error is None else error}")
        if self.runs is not None:
            self.runs.record(
                Run(
                    task=f"hands.{action}",
                    provider="hands",
                    model=folder,
                    ok=error is None,
                    latency_ms=latency_ms,
                    error=type(error).__name__ if error else None,
                )
            )

    async def list(self, folder: str, path: str = ".", *, pattern=None, include_private=True):
        return await self._run(
            "list", folder, include_private, reader.list_dir, path=path, pattern=pattern,
            limit=self.max_results,
        )  # fmt: skip

    async def read(self, folder: str, path: str, *, include_private: bool = True) -> dict:
        return await self._run(
            "read", folder, include_private, reader.read_file, path=path, max_chars=self.max_chars
        )

    async def search(self, folder: str, query: str, *, content=True, include_private=True):
        if self.bus is not None:
            self.bus.publish("agent.working", task=f"Buscando en {folder}")
        try:
            result = await self._run(
                "search", folder, include_private, reader.search, query=query, content=content,
                limit=self.max_results, max_files=self.max_files,
            )  # fmt: skip
        except HandsError as e:
            if self.bus is not None:
                self.bus.publish("agent.error", message=str(e))
            raise
        if self.bus is not None:
            found = len(result["matches"])
            self.bus.publish("agent.done", summary=f"{found} resultado(s) en {folder}")
        return result
