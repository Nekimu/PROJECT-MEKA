"""Hanna proactiva: revisa de vez en cuando tus pendientes y notificaciones y te los recuerda.

Diseñada para **no estorbar ni gastar**:
- Cada `check_seconds` (60) solo hace una consulta a SQLite: ¿hay algún aviso que ya toca?
  No usa el cerebro ni la red; las frases salen del personaje.
- Los avisos que pediste («recuérdame…») llegan a su hora (`reminder.due`), también en modo
  concentración: los pediste tú.
- El resumen (`nudge`) es lo único que ella decide por su cuenta, y solo sale si:
  hay algo que contar (vencidas, de hoy o notificaciones nuevas); no es hora de silencio
  (`quiet_hours`); no estás concentrado; no le estás hablando ahora (`idle_minutes`); el
  núcleo no está ocupado; pasó `digest_minutes` desde el anterior; no lo ha repetido en
  `repeat_hours`, y no superó `max_per_day`.
- Las notificaciones solo cuentan (cuántas y de qué apps), nunca su texto.
"""

import asyncio
import contextlib
import time
from collections.abc import Callable
from datetime import datetime

from core.events import EventBus
from core.logger import setup_logger

logger = setup_logger("Proactive")


def _minutes(value: str) -> int:
    hours, minutes = str(value).split(":")
    return int(hours) * 60 + int(minutes)


class Proactive:
    def __init__(
        self,
        config: dict,
        tasks,
        bus: EventBus,
        *,
        user: str,
        focus=None,
        system=None,
        busy: Callable[[], bool] = lambda: False,
        last_activity: Callable[[], float] = lambda: 0.0,
    ):
        cfg = config.get("proactive") or {}
        # Desactivado si config.yml no lo pide (los tests no vigilan con el reloj real)
        self.enabled = bool(cfg.get("enabled", False))
        self.check_seconds = float(cfg.get("check_seconds", 60))
        self.digest_seconds = float(cfg.get("digest_minutes", 120)) * 60
        self.startup_seconds = float(cfg.get("startup_minutes", 2)) * 60
        self.idle_seconds = float(cfg.get("idle_minutes", 5)) * 60
        self.repeat_seconds = float(cfg.get("repeat_hours", 4)) * 3600
        self.max_per_day = int(cfg.get("max_per_day", 6))
        self.include_notifications = bool(cfg.get("notifications", True))
        quiet = cfg.get("quiet_hours") or ["22:00", "08:00"]
        self.quiet = (_minutes(quiet[0]), _minutes(quiet[1])) if quiet else None
        self.tasks, self.bus, self.user = tasks, bus, user
        self.focus, self.system = focus, system
        self.busy, self.last_activity = busy, last_activity
        self.started_at = time.time()
        self.last_nudge_at: float | None = None
        self.last_signature: tuple | None = None
        self.sent_today: dict[str, int] = {}
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------ ciclo

    async def start(self):
        if self.enabled and self._task is None:
            self.started_at = time.time()
            self._task = asyncio.create_task(self._loop())
            logger.info(
                f"Proactiva: avisos cada {self.check_seconds:.0f} s, resumen cada "
                f"{self.digest_seconds / 60:.0f} min como mucho"
            )

    async def stop(self):
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _loop(self):
        warned = False
        while True:
            try:
                self.tick()
                warned = False
            except Exception as e:  # Un fallo puntual no apaga la vigilancia
                if not warned:
                    logger.warning(f"Fallo en la revisión proactiva: {e}")
                    warned = True
            await asyncio.sleep(self.check_seconds)

    def tick(self, now: float | None = None) -> dict:
        """Una revisión: avisos que tocan y, si procede, el resumen. Devuelve lo que hizo."""
        now = now or time.time()
        reminded = [self.tasks.remind(task) for task in self.tasks.store.due_reminders(now)]
        reason = self.why_not(now)
        nudge = self.nudge(now) if reason is None else None
        return {"reminded": len(reminded), "nudge": nudge, "skipped": reason}

    # ------------------------------------------------------------------ el resumen

    def why_not(self, now: float) -> str | None:
        """Por qué no toca un resumen ahora (None: sí toca)."""
        if now - self.started_at < self.startup_seconds:
            return "acaba de arrancar"
        if self.last_nudge_at is not None and now - self.last_nudge_at < self.digest_seconds:
            return "resumen reciente"
        if self._quiet(now):
            return "horas de silencio"
        if self.focus is not None and self.focus.active:
            return "modo concentración"
        if self.busy():
            return "ocupada"
        if now - self.last_activity() < self.idle_seconds:
            return "conversación en curso"
        if self.sent_today.get(self._day(now), 0) >= self.max_per_day:
            return "límite diario"
        return None

    def nudge(self, now: float | None = None, *, force: bool = False) -> dict | None:
        """Publica el resumen si hay algo que contar. `force`: lo pidió el usuario (sin
        límites de frecuencia ni repetición)."""
        now = now or time.time()
        content = self.content(now)
        if content is None:
            return None
        signature = content.pop("signature")
        repeated = (
            signature == self.last_signature
            and self.last_nudge_at is not None
            and now - self.last_nudge_at < self.repeat_seconds
        )
        if repeated and not force:
            return None
        self.bus.publish("nudge", **content)
        self.last_nudge_at, self.last_signature = now, signature
        day = self._day(now)
        self.sent_today = {day: self.sent_today.get(day, 0) + 1}
        logger.info(f"Resumen proactivo: {content['tasks']} tarea(s), "
                    f"{content['notifications']} notificación(es)")  # fmt: skip
        return content

    def content(self, now: float) -> dict | None:
        today = datetime.fromtimestamp(now).astimezone()
        horizon = today.replace(hour=23, minute=59, second=59).timestamp()
        if today.hour >= 18:  # Por la tarde también cuenta lo de mañana
            horizon += 86400
        pending = self.tasks.store.list(self.user)
        overdue = [t for t in pending if t.due_at is not None and t.due_at < now]
        soon = [t for t in pending if t.due_at is not None and now <= t.due_at <= horizon]
        parts = []
        if overdue:
            parts.append(f"tienes {len(overdue)} vencida(s): " + _titles(overdue))
        if soon:
            parts.append(("y " if overdue else "") + "pronto vence: " + _titles(soon))
        notes = self._new_notifications() if self.include_notifications else []
        if not parts and not notes:
            return None
        text = []
        if parts:
            text.append(self.tasks.line("nudge_tasks", summary=" ".join(parts) + "."))
        if notes:
            apps = sorted({n["app"] for n in notes})
            text.append(self.tasks.line(
                "nudge_notifications", count=len(notes), apps=", ".join(apps[:3])
            ))  # fmt: skip
        return {
            "text": " ".join(text),
            "kind": "tasks" if parts else "notifications",
            "tasks": len(overdue) + len(soon),
            "overdue": len(overdue),
            "notifications": len(notes),
            "signature": (tuple(t.id for t in overdue + soon), tuple(n["id"] for n in notes)),
        }

    def _new_notifications(self) -> list[dict]:
        """Notificaciones llegadas desde el último resumen (solo cuántas y de qué app)."""
        if self.system is None:
            return []
        since = self.last_nudge_at or self.started_at
        return [n for n in self.system.notifications() if n["time"] > since]

    def _quiet(self, now: float) -> bool:
        if not self.quiet:
            return False
        moment = datetime.fromtimestamp(now)
        minute = moment.hour * 60 + moment.minute
        start, end = self.quiet
        return start <= minute < end if start < end else minute >= start or minute < end

    @staticmethod
    def _day(now: float) -> str:
        return datetime.fromtimestamp(now).strftime("%Y-%m-%d")

    def status(self) -> dict:
        now = time.time()
        next_digest = max(
            self.started_at + self.startup_seconds,
            (self.last_nudge_at or 0) + self.digest_seconds,
        )
        return {
            "enabled": self.enabled,
            "next_check": now + self.check_seconds if self._task else None,
            "next_digest": next_digest if self.enabled else None,
            "last_nudge": self.last_nudge_at,
            "nudges_today": self.sent_today.get(self._day(now), 0),
            "waiting": self.why_not(now),
        }


def _titles(tasks) -> str:
    names = [f"«{t.title}»" for t in tasks[:3]]
    more = f" y {len(tasks) - 3} más" if len(tasks) > 3 else ""
    return ", ".join(names) + more
