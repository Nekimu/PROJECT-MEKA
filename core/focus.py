"""Modo concentración: MEKA ayuda, no distrae (docs/VISION.md).

Durante una sesión el núcleo **retiene** lo que distrae (notificaciones, cambios de canción,
mensajes que llegan por otros canales, avisos de agentes trabajando o terminando) y deja
pasar lo que necesita tu atención: permisos, errores, notificaciones de apps importantes y
la batería crítica. Al terminar publica `focus.ended` con el resumen de lo que esperó.

    focus.started {until, minutes}
    focus.ended   {reason, held, notifications}

Se maneja con `user.focus {action: start|stop, minutes?}`, `POST/DELETE /v1/focus` o el MCP.
"""

import asyncio
import collections
import contextlib
import time

from core.events import EventBus
from core.logger import setup_logger

logger = setup_logger("Focus")

# Siempre pasan, aunque estés concentrado
ALWAYS = frozenset({
    "agent.confirm", "agent.confirmed",  # Un agente no puede quedarse esperando tu permiso
    "agent.error", "emotion", "budget.low", "focus.started", "focus.ended",
    "reminder.due", "task.changed",  # Los avisos los pediste tú; la lista debe seguir al día
})  # fmt: skip
# Se retienen (y se cuentan para el resumen)
HELD = frozenset({
    "system.notification", "system.notification_removed", "system.media", "system.battery",
    "message", "agent.working", "agent.done", "nudge",
})  # fmt: skip


class FocusMode:
    def __init__(self, config: dict, bus: EventBus):
        cfg = config.get("focus") or {}
        self.default_minutes = int(cfg.get("default_minutes", 25))
        self.max_minutes = int(cfg.get("max_minutes", 240))
        self.allow_apps = {a.lower() for a in cfg.get("allow_apps") or []}
        self.battery_alert = int(cfg.get("battery_alert", 15))
        self.bus = bus
        self.until: float | None = None
        self.started_at: float | None = None
        self.held: collections.Counter = collections.Counter()
        self._timer: asyncio.Task | None = None
        bus.gate = self.allows

    @property
    def active(self) -> bool:
        return self.until is not None and time.time() < self.until

    def status(self) -> dict:
        return {
            "active": self.active,
            "until": self.until if self.active else None,
            "remaining": max(0, round(self.until - time.time())) if self.active else 0,
            "held": sum(self.held.values()) if self.active else 0,
        }

    # ------------------------------------------------------------------ filtro del bus

    def allows(self, type_: str, data: dict) -> bool:
        if not self.active or type_ in ALWAYS or type_ not in HELD:
            return True
        if type_ == "system.notification" and str(data.get("app", "")).lower() in self.allow_apps:
            return True  # App importante: pasa
        if (
            type_ == "system.battery"
            and not data.get("charging")
            and data.get("percent", 100) <= self.battery_alert
        ):
            return True  # Batería crítica: pasa
        self.held[type_] += 1
        return False

    def delivered(self, type_: str):
        """Un evento retenido que igual llegó a quien lo pidió (la respuesta del chat de la
        mascota): no cuenta como pendiente en el resumen."""
        if self.held[type_] > 0:
            self.held[type_] -= 1

    # ------------------------------------------------------------------ sesiones

    async def start(self, minutes: int | None = None) -> dict:
        minutes = self.default_minutes if minutes is None else int(minutes)  # 0 no es "vacío"
        if not 1 <= minutes <= self.max_minutes:
            raise ValueError(f"La duración debe estar entre 1 y {self.max_minutes} minutos")
        self._cancel_timer()
        if not self.active:  # Una sesión nueva empieza con el resumen a cero
            self.held.clear()
            self.started_at = time.time()
        self.until = time.time() + minutes * 60
        self._timer = asyncio.create_task(self._expire(self.until))
        self.bus.publish("focus.started", until=self.until, minutes=minutes)
        logger.info(f"Modo concentración: {minutes} min")
        return self.status()

    async def _expire(self, until: float):
        await asyncio.sleep(max(0.0, until - time.time()))
        if self.until == until:  # Nadie la amplió ni la terminó antes
            self._timer = None
            self.stop("timeout")

    def stop(self, reason: str = "user") -> dict | None:
        """Termina la sesión y publica el resumen. None si no había ninguna."""
        if self.until is None:
            return None
        self._cancel_timer()
        summary = {
            "reason": reason,
            "held": sum(self.held.values()),
            "notifications": self.held["system.notification"],
        }
        self.until = None
        self.bus.publish("focus.ended", **summary)
        logger.info(f"Fin del modo concentración ({reason}): {summary['held']} evento(s) retenidos")
        return summary

    def _cancel_timer(self):
        if self._timer is not None and self._timer is not asyncio.current_task():
            self._timer.cancel()
        self._timer = None

    def close(self):
        with contextlib.suppress(Exception):
            self._cancel_timer()
