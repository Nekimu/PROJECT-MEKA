"""Bus de eventos de MEKA Core: lo que pasa en el núcleo llega a la mascota y a otros clientes.

Contrato completo en docs/VISION.md («Contrato de eventos»). Cada evento es un JSON
`{"type": ..., "data": {...}}`.
"""

import asyncio
import contextlib

from core.logger import setup_logger

logger = setup_logger("Events")

# Eventos que MEKA Core (o un agente externo, vía POST /v1/events) envía a los clientes
OUTBOUND_EVENTS = frozenset({
    "agent.working", "agent.done", "agent.error", "agent.confirm",
    "message", "emotion", "budget.low",
})  # fmt: skip
EMOTIONS = frozenset({
    "idle", "happy", "working", "thinking", "sleeping", "eating", "error", "celebrate", "sad",
})  # fmt: skip


def event(type_: str, **data) -> dict:
    return {"type": type_, "data": data}


class EventBus:
    """Reparte cada evento a todos los suscriptores (una cola por cliente WebSocket)."""

    def __init__(self, queue_size: int = 100):
        self.queue_size = queue_size
        self._subscribers: set[asyncio.Queue] = set()

    @property
    def subscribers(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(self.queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)

    def publish(self, type_: str, **data):
        message = event(type_, **data)
        for queue in list(self._subscribers):
            if queue.full():
                # Un cliente lento no frena a los demás: se descarta su evento más antiguo
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            queue.put_nowait(message)
        logger.debug(f"Evento {type_} enviado a {len(self._subscribers)} cliente(s)")
