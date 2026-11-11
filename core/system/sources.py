"""Fuentes de datos del sistema para la Dynamic Island: música en reproducción y batería.

- Música: la API de Windows SMTC (`GlobalSystemMediaTransportControlsSessionManager`), que
  ve cualquier reproductor que se integre con Windows (Spotify, navegador, Media Player...).
  Requiere `winrt-Windows.Media.Control` (solo Windows); en otros sistemas no hay música.
- Batería: `psutil` (multiplataforma); en un equipo de sobremesa no hay batería.
"""

import contextlib

from core.logger import setup_logger

logger = setup_logger("System")

MEDIA_ACTIONS = ("play_pause", "next", "previous")
_PLAYING = 4  # GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING


async def battery_snapshot() -> dict | None:
    try:
        import psutil
    except ImportError:
        return None
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    return {"percent": round(battery.percent), "charging": bool(battery.power_plugged)}


class NullMediaSource:
    """Sin acceso a la música del sistema (no es Windows o falta la dependencia)."""

    available = False

    async def snapshot(self) -> dict | None:
        return None

    async def control(self, action: str) -> bool:
        return False


class WindowsMediaSource:
    available = True

    def __init__(self):
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Manager,
        )

        self._manager_class = Manager
        self._manager = None

    async def _session(self):
        if self._manager is None:
            self._manager = await self._manager_class.request_async()
        return self._manager.get_current_session()

    async def snapshot(self) -> dict | None:
        session = await self._session()
        if session is None:
            return {"playing": False}
        props = await session.try_get_media_properties_async()
        info = session.get_playback_info()
        data = {
            "playing": int(info.playback_status) == _PLAYING,
            "title": props.title or None,
            "artist": props.artist or None,
            "app": _app_name(session.source_app_user_model_id),
        }
        with contextlib.suppress(Exception):  # No todos los reproductores informan del tiempo
            timeline = session.get_timeline_properties()
            duration = timeline.end_time.total_seconds()
            if duration > 0:
                data["duration"] = round(duration, 1)
                data["position"] = round(timeline.position.total_seconds(), 1)
        return data

    async def control(self, action: str) -> bool:
        session = await self._session()
        if session is None:
            return False
        method = {
            "play_pause": session.try_toggle_play_pause_async,
            "next": session.try_skip_next_async,
            "previous": session.try_skip_previous_async,
        }[action]
        return bool(await method())


def _app_name(app_id: str | None) -> str | None:
    """'Spotify.exe' o 'SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify' → 'Spotify'."""
    if not app_id:
        return None
    name = app_id.split("!")[-1].removesuffix(".exe")
    return name.split(".")[-1] or None


def build_media_source():
    try:
        return WindowsMediaSource()
    except Exception as e:  # ImportError fuera de Windows o sin el paquete
        logger.info(f"Música del sistema no disponible ({type(e).__name__})")
        return NullMediaSource()
