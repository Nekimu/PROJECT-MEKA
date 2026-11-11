"""Datos del sistema para la Dynamic Island (T-044): música y batería como eventos."""

import asyncio

import pytest

from core import contract
from core.events import EventBus
from core.system import SystemMonitor
from core.system.sources import _app_name
from tests.test_server import make_client, make_engine


class FakeMedia:
    available = True

    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)
        self.actions = []

    async def snapshot(self):
        return self.snapshots.pop(0) if len(self.snapshots) > 1 else self.snapshots[0]

    async def control(self, action):
        self.actions.append(action)
        return True


def battery_reader(*values):
    values = list(values)

    async def read():
        return values.pop(0) if len(values) > 1 else values[0]

    return read


def make_monitor(media=None, battery=None):
    bus = EventBus()
    events = bus.subscribe()
    config = {
        "system": {
            "enabled": True,
            "media_interval": 0.01,
            "battery_interval": 0.01,
            "notifications": False,  # Nunca las notificaciones reales del equipo en los tests
        }
    }
    return SystemMonitor(config, bus, media=media, battery=battery), events


def drain(queue):
    return [queue.get_nowait() for _ in range(queue.qsize())]


SONG = {"playing": True, "title": "Idol", "artist": "YOASOBI", "app": "Spotify", "duration": 213.0}


def test_media_events_only_when_something_changes():
    media = FakeMedia(
        {**SONG, "position": 1.0},
        {**SONG, "position": 3.0},  # Solo avanza la canción: no es un cambio
        {**SONG, "playing": False, "position": 3.0},  # Pausa
        {**SONG, "title": "Racing into the Night", "position": 0.0},  # Otra canción
        {"playing": False},  # Nada sonando
    )
    monitor, events = make_monitor(media=media)

    async def scenario():
        return [await monitor.refresh("media") for _ in range(5)]

    assert asyncio.run(scenario()) == [True, False, True, True, True]
    emitted = drain(events)
    assert [e["data"].get("title") for e in emitted] == [
        "Idol",
        "Idol",
        "Racing into the Night",
        None,
    ]
    assert emitted[0]["data"]["position"] == 1.0
    assert emitted[-1]["data"] == {"playing": False}  # Los campos vacíos no viajan
    assert monitor.snapshot()["media"] == {"playing": False}


def test_battery_events_and_desktops_without_battery():
    monitor, events = make_monitor(
        battery=battery_reader(
            {"percent": 30, "charging": True},
            {"percent": 30, "charging": True},
            {"percent": 31, "charging": True},
        )
    )

    async def scenario():
        return [await monitor.refresh("battery") for _ in range(3)]

    assert asyncio.run(scenario()) == [True, False, True]
    assert [e["data"] for e in drain(events)] == [
        {"percent": 30, "charging": True},
        {"percent": 31, "charging": True},
    ]

    desktop, events = make_monitor(battery=battery_reader(None))
    assert asyncio.run(desktop.refresh("battery")) is False and drain(events) == []


def test_every_system_event_follows_the_contract():
    media = FakeMedia({**SONG, "position": 12.5}, {"playing": False})
    monitor, events = make_monitor(
        media=media, battery=battery_reader({"percent": 80, "charging": False})
    )

    async def scenario():
        await monitor.refresh("media")
        await monitor.refresh("media")
        await monitor.refresh("battery")

    asyncio.run(scenario())
    for event in drain(events):
        assert contract.validate(event["type"], event["data"]) == [], event


def test_media_control():
    media = FakeMedia(SONG)
    monitor, _ = make_monitor(media=media)
    assert asyncio.run(monitor.media_control("next")) is True
    assert media.actions == ["next"]
    with pytest.raises(ValueError):
        asyncio.run(monitor.media_control("borrar_todo"))
    assert media.actions == ["next"]


def test_disabled_by_default():
    monitor = SystemMonitor({}, EventBus())
    assert monitor.media is None and monitor.battery is None
    assert asyncio.run(monitor.media_control("next")) is False


@pytest.mark.parametrize(
    ("app_id", "name"),
    [
        ("Spotify.exe", "Spotify"),
        ("SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify", "Spotify"),
        ("Microsoft.ZuneMusic_8wekyb3d8bbwe!Microsoft.ZuneMusic", "ZuneMusic"),
        ("MSEdge", "MSEdge"),
        (None, None),
    ],
)
def test_app_names(app_id, name):
    assert _app_name(app_id) == name


def test_live_monitor_reaches_the_pet_and_the_api(tmp_path):
    import time

    engine = make_engine(tmp_path)
    media = FakeMedia(SONG)
    battery = {"percent": 55, "charging": False}

    async def read_battery():
        return dict(battery)

    engine.system, _ = make_monitor(media=media, battery=read_battery)
    engine.system.bus = engine.bus
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        # El monitor arranca con el servidor; quien llega tarde pide el estado por REST
        for _ in range(200):
            state = client.get("/v1/system").json()
            if state["battery"] and state["media"]:
                break
            time.sleep(0.01)
        assert state["battery"] == {"percent": 55, "charging": False}
        assert state["media"]["title"] == "Idol"

        battery["charging"] = True  # Enchufas el portátil → la mascota se entera
        expected = {"type": "system.battery", "data": {"percent": 55, "charging": True}}
        # Pueden llegar antes las lecturas iniciales si el WebSocket se conectó primero
        assert any(ws.receive_json() == expected for _ in range(3))

        ws.send_json({"type": "user.media", "data": {"action": "play_pause"}})
        assert client.post("/v1/system/media", json={"action": "previous"}).json() == {"done": True}
        assert client.post("/v1/system/media", json={"action": "x"}).status_code == 422
        # Solo el núcleo publica datos del sistema
        fake = client.post(
            "/v1/events", json={"type": "system.battery", "data": {"percent": 1, "charging": False}}
        )
        assert fake.status_code == 422
    assert media.actions == ["play_pause", "previous"]
