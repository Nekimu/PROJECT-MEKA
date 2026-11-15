"""Datos del sistema para la Dynamic Island: el núcleo los vigila y los publica como eventos.

    system.media   {playing, title?, artist?, app?, position?, duration?}
    system.battery {percent, charging}
    system.notification / system.notification_removed  (core/system/inbox.py)

Solo se publica cuando algo cambia (la posición de la canción no cuenta como cambio, para no
saturar el WebSocket: viaja con el siguiente evento y en GET /v1/system). Los clientes
controlan la música con `user.media {action}` o `POST /v1/system/media`.
"""

import asyncio
import contextlib

from core.events import EventBus
from core.logger import setup_logger
from core.system.inbox import InboxMixin
from core.system.notifications import NOTIFICATION_ACTIONS, build_notification_source
from core.system.sources import MEDIA_ACTIONS, battery_snapshot, build_media_source

__all__ = ["MEDIA_ACTIONS", "NOTIFICATION_ACTIONS", "SystemMonitor"]

logger = setup_logger("System")

# Lo que cuenta como "cambio" de la música (la posición avanza sola)
MEDIA_KEYS = ("playing", "title", "artist", "app", "duration")


class SystemMonitor(InboxMixin):
    def __init__(
        self, config: dict, bus: EventBus, *, media=None, battery=None, notifications=None
    ):
        cfg = config.get("system") or {}
        # Desactivado si config.yml no lo pide (los tests no vigilan el sistema real)
        self.enabled = bool(cfg.get("enabled", False))
        self.bus = bus
        self.media = media if media is not None else (
            build_media_source() if self.enabled and cfg.get("media", True) else None
        )  # fmt: skip
        self.battery = battery if battery is not None else (
            battery_snapshot if self.enabled and cfg.get("battery", True) else None
        )  # fmt: skip
        self.intervals = {
            "media": float(cfg.get("media_interval", 2)),
            "battery": float(cfg.get("battery_interval", 60)),
        }
        self.state: dict[str, dict | None] = {"media": None, "battery": None}
        self._tasks: list[asyncio.Task] = []
        inbox = cfg.get("notifications", True)
        inbox = inbox if isinstance(inbox, dict) else {"enabled": bool(inbox)}
        self._setup_inbox(
            inbox,
            notifications if notifications is not None else (
                build_notification_source() if self.enabled and inbox.get("enabled", True) else None
            ),
        )  # fmt: skip

    def snapshot(self) -> dict:
        return {"media": self.state["media"], "battery": self.state["battery"]}

    async def start(self):
        await self._first_read()
        if self.media is not None:
            self._tasks.append(asyncio.create_task(self._loop("media", self.media.snapshot)))
        if self.battery is not None:
            self._tasks.append(asyncio.create_task(self._loop("battery", self.battery)))
        if self.notifications_source is not None:
            self._tasks.append(asyncio.create_task(self._loop("notifications", None)))

    async def _first_read(self, timeout: float = 3.0):
        """Una lectura antes de abrir el servidor: quien se conecte al arrancar ya encuentra la
        música, la batería y las notificaciones que había (y no un estado vacío)."""
        reads = []
        if self.media is not None:
            reads.append(self.refresh("media", self.media.snapshot))
        if self.battery is not None:
            reads.append(self.refresh("battery", self.battery))
        if self.notifications_source is not None:
            reads.append(self.refresh_notifications())
        if not reads:
            return
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*reads, return_exceptions=True), timeout
            )
        except TimeoutError:
            logger.warning("El sistema tardó en responder; los datos llegarán en unos segundos")
            return
        for error in (r for r in results if isinstance(r, Exception)):
            logger.warning(f"Primera lectura del sistema fallida: {error}")
        notifications = "—" if self._inbox is None else len(self._inbox)
        logger.info(
            f"Sistema: música={_seen(self.state['media'], 'title')} · "
            f"batería={_seen(self.state['battery'], 'percent')} · notificaciones={notifications}"
        )

    def initial_events(self) -> list[tuple[str, dict]]:
        """El estado actual como eventos, para un cliente que acaba de conectarse por WebSocket.
        Las notificaciones no: llegarían como nuevas; la lista está en GET /v1/system/notifications."""
        return [
            (f"system.{kind}", {k: v for k, v in value.items() if v is not None})
            for kind, value in self.state.items()
            if value is not None
        ]

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()

    async def _loop(self, kind: str, fetch):
        warned = False
        while True:
            try:
                if kind == "notifications":
                    await self.refresh_notifications()
                else:
                    await self.refresh(kind, fetch)
                warned = False
            except Exception as e:  # Un fallo puntual de la API no detiene la vigilancia
                if not warned:
                    logger.warning(f"No se pudo leer {kind} del sistema: {e}")
                    warned = True
            await asyncio.sleep(self.intervals[kind])

    async def refresh(self, kind: str, fetch=None) -> bool:
        """Lee el dato y publica el evento si cambió. Devuelve si hubo cambio."""
        fetch = fetch or (self.media.snapshot if kind == "media" else self.battery)
        value = await fetch()
        previous = self.state[kind]
        self.state[kind] = value
        if value is None or not self._changed(kind, previous, value):
            return False
        self.bus.publish(f"system.{kind}", **{k: v for k, v in value.items() if v is not None})
        return True

    @staticmethod
    def _changed(kind: str, previous, value) -> bool:
        if previous is None:
            return True
        if kind == "media":
            return any(previous.get(k) != value.get(k) for k in MEDIA_KEYS)
        return previous != value

    async def media_control(self, action: str) -> bool:
        """Reproducir/pausar o cambiar de canción en el reproductor activo."""
        if action not in MEDIA_ACTIONS:
            raise ValueError(f"Acción no válida: {action!r}. Usa: {', '.join(MEDIA_ACTIONS)}")
        if self.media is None or not await self.media.control(action):
            return False
        await asyncio.sleep(0.3)  # Dar tiempo al reproductor y avisar ya a todos
        with contextlib.suppress(Exception):
            await self.refresh("media")
        return True


def _seen(value: dict | None, key: str) -> str:
    if value is None:
        return "—"
    return str(value.get(key) or ("sin reproducción" if key == "title" else "?"))
