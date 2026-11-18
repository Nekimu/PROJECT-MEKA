"""«Mientras no estabas…»: al volver al equipo, Hanna te cuenta en una frase lo que pasó.

`WelcomeMixin` es parte de `Proactive` (core/tasks/proactive.py). Usa la inactividad de Windows
(core/system/presence.py): si llevas `welcome_minutes` sin tocar teclado ni ratón cuentas como
fuera; al volver a tocarlo, resume los avisos que sonaron, lo vencido y cuántas notificaciones
llegaron (nunca su texto). Un solo `nudge` (`kind: welcome`) por regreso, y solo si hay algo.
Respeta las horas de silencio, el modo concentración y el límite diario.
"""


class WelcomeMixin:
    def _setup_welcome(self, cfg: dict):
        self.welcome_seconds = float(cfg.get("welcome_minutes", 20)) * 60
        self.away_since: float | None = None
        self.missed: list[str] = []  # Avisos que sonaron mientras no estabas

    def track_presence(self, now: float) -> dict | None:
        """Anota si te fuiste o volviste. Al volver, publica el resumen (si hay algo)."""
        idle = self.idle()
        if idle is None or self.welcome_seconds <= 0:
            return None
        if self.away_since is None:
            if idle >= self.welcome_seconds:
                self.away_since = now - idle
            return None
        if idle >= max(self.check_seconds * 1.5, 90):
            return None  # Sigues fuera
        since, self.away_since = self.away_since, None
        missed, self.missed = self.missed, []
        if self._quiet(now) or (self.focus is not None and self.focus.active):
            return None
        if self.sent_today.get(self._day(now), 0) >= self.max_per_day:
            return None
        return self.welcome(now, since, missed)

    def mark_leaving(self, now: float):
        """Antes de los avisos: así los que suenen ahora ya cuentan como «mientras no estabas»."""
        idle = self.idle()
        if self.away_since is None and idle is not None and 0 < self.welcome_seconds <= idle:
            self.away_since = now - idle

    def note_missed(self, title: str):
        if self.away_since is not None:
            self.missed.append(title)

    def welcome(self, now: float, since: float, missed: list[str]) -> dict | None:
        pending = self.tasks.store.list(self.user)
        overdue = [t for t in pending if t.due_at is not None and t.due_at < now]
        notes = [n for n in self.system.notifications() if n["time"] > since] if self.system else []
        parts = []
        if missed:
            names = ", ".join(f"«{t}»" for t in missed[:3])
            more = f" y {len(missed) - 3} más" if len(missed) > 3 else ""
            parts.append(f"te avisé de {names}{more}")
        if overdue:
            parts.append(f"tienes {len(overdue)} vencida(s)")
        if notes:
            apps = ", ".join(sorted({n["app"] for n in notes})[:3])
            parts.append(f"llegaron {len(notes)} notificación(es) de {apps}")
        if not parts:
            return None
        summary = (", ".join(parts[:-1]) + " y " + parts[-1]) if len(parts) > 1 else parts[0]
        content = {
            "text": self.tasks.line("nudge_welcome", summary=summary + "."),
            "kind": "welcome",
            "tasks": len(overdue),
            "overdue": len(overdue),
            "notifications": len(notes),
            "remote": False,  # Acabas de volver al equipo: solo la isla
        }
        self.bus.publish("nudge", **content)
        self.last_nudge_at = now
        day = self._day(now)
        self.sent_today = {day: self.sent_today.get(day, 0) + 1}
        return content
