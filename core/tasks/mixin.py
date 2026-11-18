"""La agenda dentro del motor: el chat y las notas de voz pasan por aquí antes del cerebro.

`AgendaMixin` es parte de `MekaEngine` (core/engine.py), como `MediaMixin`. Usa del motor:
config, memory, bus, persona, focus, system, lock y ai.
"""

import collections
import time

from ai.text_utils import ParsedMessage, parse_message
from core.config import default_user
from core.system.presence import idle_seconds
from core.tasks import TaskService, TaskStore
from core.tasks.proactive import Proactive


class AgendaMixin:
    def _setup_agenda(self, config: dict):
        self.tasks = TaskService(config, TaskStore(self.memory.db_path), self.bus, self.persona)
        self.last_activity = 0.0  # Última vez que el usuario habló (la proactiva no interrumpe)
        self.clients: collections.Counter = collections.Counter()  # Conectados por WebSocket
        desk = set((config.get("proactive") or {}).get("desk_clients") or ["pet"])
        self.proactive = Proactive(
            config,
            self.tasks,
            self.bus,
            user=default_user(config),
            focus=self.focus,
            system=self.system,
            busy=lambda: self.lock.locked(),
            last_activity=lambda: self.last_activity,
            at_desk=lambda: any(self.clients[name] > 0 for name in desk),
            idle=idle_seconds,
        )

    async def _answer_with_agenda(
        self,
        session: str,
        user: str,
        text: str,
        *,
        private: bool,
        use_memory: bool = True,
        remote: bool = False,
    ):
        """Primero la agenda (determinista), luego el cerebro con la agenda real de contexto.
        Devuelve (mensajes listos, respuesta del cerebro)."""
        self.last_activity = time.time()
        private = self.ai.decide_privacy(session, text, private)
        # Lo privado solo entra en el prompt si lo lee un cerebro local Y la respuesta no sale
        # del equipo (Telegram o MCP la llevarían fuera)
        local = self.ai.stays_local("chat", private) and not remote
        agenda = self.tasks.handle(user, text, private=private, local=local, remote=remote)
        answer = await self.ai.answer(
            session, user, text, use_memory=use_memory, private=private,
            extra_context=agenda.context, remote=remote,
        )  # fmt: skip
        # Las frases de la agenda no pasan por el filtro de acotaciones: «(antes del 15)» es dato
        parsed = [ParsedMessage(text=reply) for reply in agenda.replies]
        parsed += [parse_message(message) for message in answer.messages]
        return parsed, answer

    def _close_agenda(self):
        self.tasks.store.close()
