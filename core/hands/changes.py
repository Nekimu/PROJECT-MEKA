"""Cambios de las manos con permiso, punto de restauración y deshacer (T-005).

Flujo de cada cambio (VISION.md, «Seguridad de las manos»):
1. Validar (carpeta `writable`, ruta segura, sin protegidos).
2. Pedir permiso al usuario (agent.confirm). Sin respuesta, no se hace nada.
3. Punto de restauración de los archivos afectados (git "sombra" en data/hands/).
4. Ejecutar, avisar a la mascota y anotarlo en el registro (sin rutas ni contenido).

`ChangesMixin` es parte de `Hands`; usa su bus, confirmations, restore_points, runs...
"""

import asyncio
import time

from core.hands import writer
from core.hands.policy import HandsError

MAX_BACKUP_BYTES = 50 * 1024 * 1024  # Un punto de restauración no guarda más de 50 MB


class ChangesMixin:
    async def _change(self, name: str, include_private: bool, plan, **kwargs) -> dict:
        start, error = time.perf_counter(), None
        op = plan.__name__.removeprefix("plan_")
        try:
            if self.confirmations is None or self.restore_points is None:
                raise HandsError("Los cambios no están disponibles en este núcleo", 503)
            folder = self._folder(name, include_private)
            change = plan(folder, denied=self.denied, **kwargs)
            self._check_backup_size(folder, change)
            approved = await self.confirmations.ask(
                change.summary,
                details={"folder": folder.name, "op": change.op, "paths": change.paths},
            )
            if not approved:
                raise HandsError("No hubo permiso: no se ha cambiado nada", 403)
            self._publish("agent.working", task=change.summary)
            operation = await asyncio.to_thread(
                self.restore_points.snapshot, folder, change.op, change.paths
            )
            await asyncio.to_thread(writer.apply, change)
            self._publish("agent.done", summary=f"Hecho: {change.summary}")
            return {"op_id": operation.id, "op": change.op, "paths": change.paths}
        except HandsError as e:
            error = e
            self._publish("agent.error", message=str(e))
            raise
        finally:
            self._record(op, name, int((time.perf_counter() - start) * 1000), error)

    def _check_backup_size(self, folder, change):
        size = sum(
            (folder.root / p).stat().st_size for p in change.paths if (folder.root / p).is_file()
        )
        if size > MAX_BACKUP_BYTES:
            raise HandsError("Archivo demasiado grande para un punto de restauración (50 MB)", 413)

    def _publish(self, type_: str, **data):
        if self.bus is not None:
            self.bus.publish(type_, **data)

    # ------------------------------------------------------------------ operaciones

    async def write(
        self, folder: str, path: str, content: str, *, overwrite=False, include_private=True
    ):
        return await self._change(
            folder, include_private, writer.plan_write, path=path, content=content,
            overwrite=overwrite, max_chars=self.max_write_chars,
        )  # fmt: skip

    async def move(self, folder: str, src: str, dest: str, *, include_private=True):
        return await self._change(folder, include_private, writer.plan_move, src=src, dest=dest)

    async def delete(self, folder: str, path: str, *, include_private=True):
        return await self._change(folder, include_private, writer.plan_delete, path=path)

    async def mkdir(self, folder: str, path: str, *, include_private=True):
        return await self._change(folder, include_private, writer.plan_mkdir, path=path)

    def history(self, folder: str, *, include_private=True, limit=20) -> list[dict]:
        self._folder(folder, include_private)
        if self.restore_points is None:
            return []
        return [op.public() for op in self.restore_points.history(folder, limit)]

    async def undo(self, name: str, *, include_private=True) -> dict:
        """Deshace la última operación que siga en pie (también pide permiso)."""
        start, error = time.perf_counter(), None
        try:
            folder = self._folder(name, include_private)
            operation = self.restore_points and self.restore_points.last_undoable(folder.name)
            if not operation:
                raise HandsError("No hay nada que deshacer en esta carpeta", 404)
            summary = f"Deshacer: {operation.op} de {', '.join(operation.paths)} en {folder.name}"
            approved = await self.confirmations.ask(
                summary, details={"folder": folder.name, "op": "undo", "undo": operation.id}
            )
            if not approved:
                raise HandsError("No hubo permiso: no se ha deshecho nada", 403)
            await asyncio.to_thread(self.restore_points.restore, folder, operation)
            self._publish("agent.done", summary=summary)
            return {"undone": operation.id, "op": operation.op, "paths": operation.paths}
        except HandsError as e:
            error = e
            raise
        finally:
            self._record("undo", name, int((time.perf_counter() - start) * 1000), error)
