"""La agenda dentro del motor: el chat y las notas de voz pasan por aquí antes del cerebro.

`AgendaMixin` es parte de `MekaEngine` (core/engine.py), como `MediaMixin`. Usa del motor:
config, memory, bus, persona, focus, system, lock y ai.
"""

import time

from ai.text_utils import ParsedMessage, parse_message
from core.config import default_user
from core.tasks import TaskService, TaskStore
from core.tasks.proactive import Proactive


class AgendaMixin:
    def _setup_agenda(self, config: dict):
        self.tasks = TaskService(config, TaskStore(self.memory.db_path), self.bus, self.persona)
        self.last_activity = 0.0  # Última vez que el usuario habló (la proactiva no interrumpe)
        self.proactive = Proactive(
            config,
            self.tasks,
            self.bus,
            user=default_user(config),
            focus=self.focus,
            system=self.system,
            busy=lambda: self.lock.locked(),
            last_activity=lambda: self.last_activity,
        )

    async def _answer_with_agenda(
        self, session: str, user: str, text: str, *, private: bool, use_memory: bool = True
    ):
        """Primero la agenda (determinista), luego el cerebro con la agenda real de contexto.
        Devuelve (mensajes listos, respuesta del cerebro)."""
        self.last_activity = time.time()
        private = self.ai.decide_privacy(session, text, private)
        agenda = self.tasks.handle(
            user, text, private=private, local=self.ai.stays_local("chat", private)
        )
        answer = await self.ai.answer(
            session, user, text, use_memory=use_memory, private=private,
            extra_context=agenda.context,
        )  # fmt: skip
        # Las frases de la agenda no pasan por el filtro de acotaciones: «(antes del 15)» es dato
        parsed = [ParsedMessage(text=reply) for reply in agenda.replies]
        parsed += [parse_message(message) for message in answer.messages]
        return parsed, answer

    def _close_agenda(self):
        self.tasks.store.close()
