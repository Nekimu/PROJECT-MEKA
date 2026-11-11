"""Bandeja de notificaciones de la isla: qué hay, qué es nuevo y qué desapareció.

`InboxMixin` es parte de `SystemMonitor` (core/system/__init__.py). Publica:
    system.notification          {id, app, title?, body?, time}  (una por cada nueva)
    system.notification_removed  {id}                            (al descartarla o caducar)
La primera lectura no genera eventos (serían todas las antiguas de golpe): quien se conecta
pide la lista con GET /v1/system/notifications.
"""

import asyncio
import contextlib

from core.system.notifications import NOTIFICATION_ACTIONS, allowed, present


class InboxMixin:
    def _setup_inbox(self, cfg, source):
        self.notifications_source = source
        self.notification_apps = list(cfg.get("apps") or ["*"])
        self.notification_blocked = list(cfg.get("blocked") or [])
        self.hide_codes = bool(cfg.get("hide_codes", True))
        self.max_notifications = int(cfg.get("max_items", 20))
        self.intervals["notifications"] = float(cfg.get("interval", 3))
        self._inbox: dict[int, dict] | None = None  # id → notificación (con su aumid)

    def notifications(self) -> list[dict]:
        """Las notificaciones visibles ahora, de la más reciente a la más antigua."""
        items = sorted((self._inbox or {}).values(), key=lambda n: -n["time"])
        return [present(n, hide_codes=self.hide_codes) for n in items]

    async def refresh_notifications(self) -> tuple[list[int], list[int]]:
        """Relee la bandeja y publica lo nuevo y lo que desapareció. Devuelve (nuevas, quitadas)."""
        raw = await self.notifications_source.snapshot()
        visible = [
            n for n in raw
            if allowed(n["app"], n.get("aumid", ""), self.notification_apps, self.notification_blocked)
        ]  # fmt: skip
        visible.sort(key=lambda n: -n["time"])
        current = {n["id"]: n for n in visible[: self.max_notifications]}
        first_read = self._inbox is None
        previous = self._inbox or {}
        self._inbox = current
        if first_read:
            return [], []
        added = [i for i in current if i not in previous]
        removed = [i for i in previous if i not in current]
        for notification_id in sorted(added, key=lambda i: current[i]["time"]):
            data = present(current[notification_id], hide_codes=self.hide_codes)
            self.bus.publish(
                "system.notification", **{k: v for k, v in data.items() if v is not None}
            )
        for notification_id in removed:
            self.bus.publish("system.notification_removed", id=notification_id)
        return added, removed

    async def notification_action(self, notification_id: int, action: str) -> bool:
        """Descartar una notificación o abrir la app que la envió."""
        if action not in NOTIFICATION_ACTIONS:
            raise ValueError(
                f"Acción no válida: {action!r}. Usa: {', '.join(NOTIFICATION_ACTIONS)}"
            )
        item = (self._inbox or {}).get(int(notification_id))
        if item is None or self.notifications_source is None:
            return False  # Solo sobre notificaciones que la isla puede ver
        if action == "open":
            return await self.notifications_source.open(item.get("aumid", ""))
        done = await self.notifications_source.dismiss(item["id"])
        with contextlib.suppress(Exception):
            await asyncio.sleep(0.2)
            await self.refresh_notifications()
        return done
