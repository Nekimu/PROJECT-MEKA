"""Confirmación de acciones (filosofía híbrida §8: separar "preparar" de "ejecutar").

Antes de algo delicado (borrar, mover, enviar...) el núcleo o un agente externo pide
permiso: la mascota y las apps reciben `agent.confirm`, el usuario responde con
`user.confirm` (WebSocket) o `POST /v1/confirmations/{id}`, y todos reciben
`agent.confirmed` para cerrar el diálogo. Si nadie responde a tiempo, la respuesta es **no**.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from core.events import EventBus, in_loop
from core.logger import setup_logger

logger = setup_logger("Confirm")

MAX_TIMEOUT = 600  # Ninguna espera puede bloquear más de 10 minutos


@dataclass
class Confirmation:
    id: str
    action: str
    expires_at: float
    details: dict = field(default_factory=dict)
    future: asyncio.Future = field(repr=False, default=None)

    def public(self) -> dict:
        data = {
            "id": self.id,
            "action": self.action,
            "expires_at": self.expires_at,
            "timeout": max(0, round(self.expires_at - time.time())),  # Segundos que quedan
        }
        if self.details:
            data["details"] = self.details  # Anidado: nunca pisa id ni action
        return data


class ConfirmationRegistry:
    def __init__(self, bus: EventBus, default_timeout: float = 120):
        self.bus = bus
        self.default_timeout = default_timeout
        self._pending: dict[str, Confirmation] = {}

    def pending(self) -> list[dict]:
        """Las que esperan respuesta (para un cliente que se conecta tarde)."""
        return [c.public() for c in self._pending.values()]

    async def ask(
        self, action: str, *, timeout: float | None = None, details: dict | None = None
    ) -> bool:
        """Pide permiso y espera la respuesta. False si se rechaza o caduca."""
        timeout = min(float(timeout or self.default_timeout), MAX_TIMEOUT)
        confirmation = Confirmation(
            id=uuid.uuid4().hex[:12],
            action=action[:300],
            expires_at=time.time() + timeout,
            details=dict(details or {}),
            future=asyncio.get_running_loop().create_future(),
        )
        self._pending[confirmation.id] = confirmation
        self.bus.publish("agent.confirm", **confirmation.public())
        logger.info(f"Pidiendo permiso ({confirmation.id}): {confirmation.action}")
        try:
            approved = await asyncio.wait_for(asyncio.shield(confirmation.future), timeout)
        except TimeoutError:
            approved = False
            self._finish(confirmation.id, False, "timeout")
        finally:
            self._pending.pop(confirmation.id, None)
        return approved

    def resolve(self, confirmation_id: str, approved: bool, by: str = "usuario") -> bool:
        """Respuesta del usuario. False si el id no existe o ya se resolvió/caducó."""
        confirmation = self._pending.get(str(confirmation_id))
        if confirmation is None or confirmation.future.done():
            return False
        loop = confirmation.future.get_loop()
        if in_loop(loop):
            confirmation.future.set_result(bool(approved))
        else:  # Desde una ruta `def` (otro hilo): el futuro se resuelve en su bucle
            loop.call_soon_threadsafe(_settle, confirmation.future, bool(approved))
        self._finish(confirmation.id, bool(approved), by)
        return True

    def _finish(self, confirmation_id: str, approved: bool, by: str):
        self.bus.publish("agent.confirmed", id=confirmation_id, approved=approved, by=by)
        logger.info(f"Permiso {confirmation_id}: {'concedido' if approved else 'denegado'} ({by})")

    def cancel_all(self):
        """Al apagar: todo lo pendiente se rechaza."""
        for confirmation_id in list(self._pending):
            self.resolve(confirmation_id, False, "apagado")


def _settle(future: asyncio.Future, approved: bool):
    if not future.done():  # Pudo caducar mientras tanto
        future.set_result(approved)
