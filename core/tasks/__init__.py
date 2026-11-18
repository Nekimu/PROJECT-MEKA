"""Agenda de MEKA: tareas y recordatorios que el usuario pide hablando (fase 4, productividad).

`TaskService` une el almacén (store.py), lo que el usuario pide (intents.py) y las frases del
personaje. El chat lo usa antes de preguntar al cerebro: crear, consultar o completar tareas es
**determinista** (no depende de que el modelo lo entienda) y el cerebro recibe la agenda real
como contexto, para que no invente tareas. Los avisos los da `core/tasks/proactive.py`.

Eventos: `task.changed {id, status, action}` y `reminder.due {id, title, text, due?}`.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime

from core.events import EventBus
from core.logger import setup_logger
from core.tasks.intents import best_match, understand
from core.tasks.store import Task, TaskStore
from core.tasks.when import numbers_as_digits, parse_when

__all__ = ["Agenda", "Task", "TaskService", "TaskStore", "describe_when"]

logger = setup_logger("Tasks")

# Frases por defecto: cada personaje puede dar las suyas en persona.yml (`lines`)
DEFAULT_LINES = {
    "task_added": "Anotado: {title}{when} ⏰",
    "task_list_header": "Esto es lo que tienes pendiente:",
    "task_list_empty": "No tienes nada pendiente. ¡Todo al día! ✅",
    "task_done": "¡Hecho! Taché «{title}» ✅",
    "task_done_unknown": "No encontré esa tarea entre tus pendientes. ¿Cuál era?",
    "reminder_due": "⏰ Te recuerdo: {title}{when}",
    "nudge_tasks": "Oye, {summary}",
    "nudge_notifications": "Tienes {count} notificación(es) nueva(s) de {apps}.",
    "nudge_welcome": "De vuelta 👋 Mientras no estabas: {summary}",
}
WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
ACTIONS = ("done", "reopen", "snooze", "delete")


def describe_when(ts: float | None, now: datetime | None = None, *, deadline=False) -> str:
    """«hoy a las 17:00», «mañana», «vie 20 nov a las 10:30»."""
    if ts is None:
        return ""
    now = now or datetime.now().astimezone()
    moment = datetime.fromtimestamp(ts).astimezone(now.tzinfo)
    days = (moment.date() - now.date()).days
    if (moment.hour, moment.minute) == (0, 0) and deadline:  # «Antes del 15»
        return "antes de mañana" if days == 1 else f"antes del {_day(moment, now, bare=True)}"
    day = _day(moment, now)
    if (moment.hour, moment.minute) == (23, 59):  # Todo el día
        return day
    return f"{day} a las {moment:%H:%M}" if days else f"hoy a las {moment:%H:%M}"


def _day(moment: datetime, now: datetime, *, bare=False) -> str:
    days = (moment.date() - now.date()).days
    if not bare and days == 0:
        return "hoy"
    if not bare and days == 1:
        return "mañana"
    return f"{WEEKDAYS[moment.weekday()]} {moment.day} {MONTHS[moment.month - 1]}"


@dataclass
class Agenda:
    """Lo que el chat hizo con la agenda: frases para el usuario y contexto para el cerebro."""

    replies: list[str] = field(default_factory=list)
    context: str = ""


class TaskService:
    def __init__(self, config: dict, store: TaskStore, bus: EventBus, persona):
        cfg = config.get("tasks") or {}
        self.enabled = bool(cfg.get("enabled", True))
        self.morning_hour = int(cfg.get("morning_hour", 9))
        self.store = store
        self.bus = bus
        self.persona = persona

    def line(self, key: str, **values) -> str:
        if key in self.persona.lines:
            return self.persona.line(key, **values)
        return DEFAULT_LINES[key].format(**values)

    def _changed(self, task: Task, action: str):
        self.bus.publish("task.changed", id=task.id, status=task.status, action=action)

    # ------------------------------------------------------------------ desde el chat

    def handle(
        self, user, text: str, *, private: bool, local: bool, remote: bool = False
    ) -> Agenda:
        """Crea, completa o lista tareas según lo que se dijo. `local`: el cerebro que leerá el
        contexto es local (solo entonces puede ver las tareas privadas)."""
        # Lo privado se muestra si lo lee un cerebro local o la charla es privada, pero nunca si
        # la respuesta sale del equipo (`remote`: Telegram, MCP). Crear sigue respetando `private`.
        show_private = (local or private) and not remote
        agenda = Agenda()
        if not self.enabled:
            return agenda
        now = datetime.now().astimezone()
        request = understand(text, now, morning_hour=self.morning_hour)
        if not request.any:
            return agenda
        notes = []
        for title, when in request.add:
            task = self.add(user, title, when=when, private=private)
            agenda.replies.append(self.line("task_added", title=task.title, when=self._when(task)))
            notes.append(f"Se acaba de apuntar «{task.title}»{self._when(task)}.")
        if request.done:
            pending = self.store.list(user, include_private=show_private)
            task_id = best_match(request.done, {t.id: t.title for t in pending})
            if task_id is None:
                agenda.replies.append(self.line("task_done_unknown"))
            else:
                task = self.complete(task_id)
                agenda.replies.append(self.line("task_done", title=task.title))
                notes.append(f"Se marcó como hecha «{task.title}».")
        if request.show:
            pending = self.store.list(user, include_private=show_private)
            agenda.replies.append(self.summary(pending, now))
            notes.append(
                "Agenda real del usuario (no inventes otras tareas): "
                + ("; ".join(f"{t.title}{self._when(t, now)}" for t in pending) or "vacía")
                + "."
            )
        agenda.context = (
            "\n\n[Agenda] " + " ".join(notes)
            + " Ya se lo mostraste al usuario: no repitas la lista, responde en una frase breve"
            " y sigue con el resto de su mensaje si hay algo más."
        )  # fmt: skip
        return agenda

    def summary(self, tasks: list[Task], now: datetime | None = None) -> str:
        if not tasks:
            return self.line("task_list_empty")
        lines = [self.line("task_list_header")]
        lines += [f"• {t.title}{self._when(t, now)}" for t in tasks[:10]]
        if len(tasks) > 10:
            lines.append(f"…y {len(tasks) - 10} más")
        return "\n".join(lines)

    def _when(self, task: Task, now: datetime | None = None) -> str:
        text = describe_when(task.due_at, now, deadline=True)
        return f" ({text})" if text else ""

    # ------------------------------------------------------------------ API, MCP y la isla

    def add(self, user, title: str, *, when=None, text_when: str | None = None, due_at=None,
            remind_at=None, private=False, source="chat") -> Task:  # fmt: skip
        """Con `text_when` («mañana a las 5») se interpreta la fecha como en el chat."""
        if text_when:
            when = parse_when(numbers_as_digits(text_when), datetime.now().astimezone(),
                              morning_hour=self.morning_hour)  # fmt: skip
            if not when.found:
                raise ValueError(f"No entendí la fecha: {text_when!r}")
        if when is not None and when.found:
            due_at = when.due.timestamp()
            remind_at = when.remind.timestamp() if when.remind else None
        if due_at is not None and remind_at is None and due_at > time.time():
            remind_at = due_at  # Con fecha y sin aviso propio: se avisa al vencer
        task = self.store.add(user, title, due_at=due_at, remind_at=remind_at, private=private,
                              source=source)  # fmt: skip
        logger.info(f"Tarea {task.id} apuntada ({source}){' · privada' if private else ''}")
        self._changed(task, "added")
        return task

    def complete(self, task_id: int) -> Task | None:
        task = self.store.set_status(task_id, "done")
        if task:
            self._changed(task, "done")
        return task

    def act(self, task_id: int, action: str, *, minutes: int | None = None) -> Task | None:
        """done | reopen | snooze (minutos, 10 por defecto) | delete."""
        if action not in ACTIONS:
            raise ValueError(f"Acción no válida: {action!r}. Usa: {', '.join(ACTIONS)}")
        task = self.store.get(task_id)
        if task is None:
            return None
        if action == "done":
            return self.complete(task_id)
        if action == "reopen":
            task = self.store.set_status(task_id, "pending")
        elif action == "snooze":
            minutes = max(1, min(int(minutes or 10), 7 * 24 * 60))
            if task.status == "done":  # Posponer una hecha = «recuérdamela otra vez»
                self.store.set_status(task_id, "pending")
            task = self.store.snooze(task_id, time.time() + minutes * 60)
        else:
            self.store.delete(task_id)
        self._changed(task, {"reopen": "reopened", "snooze": "snoozed"}.get(action, "deleted"))
        return task

    def remind(self, task: Task, *, remote: bool = False, now: float | None = None) -> str:
        """Avisa de una tarea (evento `reminder.due`) y la marca como avisada. `remote`: que
        llegue también al móvil (nunca si la tarea es privada)."""
        text = self.line("reminder_due", title=task.title, when=self._when(task))
        data = {"id": task.id, "title": task.title, "text": text, "due": task.due_at,
                "private": task.private, "remote": remote and not task.private}  # fmt: skip
        self.bus.publish("reminder.due", **{k: v for k, v in data.items() if v is not None})
        self.store.mark_reminded(task.id, now)
        logger.info(f"Aviso de la tarea {task.id}{' (también al móvil)' if data['remote'] else ''}")
        return text
