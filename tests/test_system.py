"""Datos del sistema para la Dynamic Island (T-044): música y batería como eventos."""

import asyncio

import pytest

from core import contract
from core.events import EventBus
from core.system import SystemMonitor
from core.system.sources import _PLAYING, _app_name, pick_session
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
            "media": False,  # Solo las fuentes falsas que pase cada test, nunca las reales
            "battery": False,
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


# ---------------------------------------------------------------------- al arrancar


class FakeSession:
    def __init__(self, name, playing):
        self.name, self.status = name, _PLAYING if playing else 5  # 5 = en pausa

    def get_playback_info(self):
        return type("Info", (), {"playback_status": self.status})()


def test_the_island_shows_what_is_playing():
    paused_video, spotify = FakeSession("Edge", False), FakeSession("Spotify", True)
    # Windows dice que la "actual" es el vídeo en pausa, pero suena Spotify
    assert pick_session(paused_video, [paused_video, spotify]) is spotify
    assert pick_session(spotify, [paused_video, spotify]) is spotify
    assert pick_session(paused_video, [paused_video]) is paused_video  # Nada suena: la actual
    assert pick_session(None, [paused_video]) is paused_video
    assert pick_session(None, []) is None


def test_state_is_ready_before_the_first_client():
    paused = {**SONG, "playing": False}
    monitor, _ = make_monitor(media=FakeMedia(paused), battery=battery_reader(
        {"percent": 80, "charging": True}
    ))  # fmt: skip

    async def scenario():
        await monitor.start()
        snapshot = monitor.snapshot()  # Sin esperar a ningún ciclo de vigilancia
        await monitor.stop()
        return snapshot

    snapshot = asyncio.run(scenario())
    assert snapshot["media"]["title"] == "Idol" and snapshot["battery"]["percent"] == 80
    assert dict(monitor.initial_events())["system.media"]["playing"] is False


def test_a_new_websocket_client_gets_the_current_state(tmp_path):
    engine = make_engine(tmp_path)
    engine.system, _ = make_monitor(
        media=FakeMedia({**SONG, "playing": False}),
        battery=battery_reader({"percent": 40, "charging": False}),
    )
    engine.system.bus = engine.bus
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        first = [ws.receive_json() for _ in range(2)]
    # La canción en pausa no "cambia", pero quien llega la ve igual
    assert {m["type"] for m in first} == {"system.media", "system.battery"}
    media = next(m for m in first if m["type"] == "system.media")["data"]
    assert media["title"] == "Idol" and media["playing"] is False


# ---------------------------------------------------------------------- carátulas


def test_artwork_is_read_only_when_the_song_changes():
    from core.system.artwork import MAX_BYTES, ArtworkCache

    cache, reads = ArtworkCache(), []

    def reader(data, mime="image/png"):
        async def read():
            reads.append(data)
            return data, mime

        return read

    song = ("Spotify", "Esfinge", "Alemán", "Esfinge")
    url = asyncio.run(cache.update(song, reader(b"\x89PNG-uno")))
    assert url.startswith("/v1/system/media/artwork?v=") and cache.get() == (
        b"\x89PNG-uno",
        "image/png",
    )
    assert asyncio.run(cache.update(song, reader(b"otra"))) == url  # Misma canción: ni la lee
    assert reads == [b"\x89PNG-uno"]
    other = asyncio.run(
        cache.update(("Spotify", "Otra", "x", None), reader(b"\xff\xd8jpg", "image/jpeg"))
    )
    assert other != url and cache.get()[1] == "image/jpeg"
    assert asyncio.run(cache.update(("a",), reader(b"x" * (MAX_BYTES + 1)))) is None  # Enorme
    assert cache.get() is None

    async def broken():
        raise OSError("sin carátula")

    assert asyncio.run(cache.update(("b",), broken)) is None  # El reproductor no la da


def test_artwork_reaches_the_island(tmp_path):
    from core.system.artwork import ArtworkCache

    media = FakeMedia({**SONG, "artwork": "/v1/system/media/artwork?v=abc"})
    media.artwork = ArtworkCache()
    media.artwork.data, media.artwork.mime = b"\x89PNG", "image/png"
    engine = make_engine(tmp_path)
    engine.system, _ = make_monitor(media=media)
    engine.system.bus = engine.bus
    with make_client(engine) as client:
        state = client.get("/v1/system").json()
        assert state["media"]["artwork"] == "/v1/system/media/artwork?v=abc"
        image = client.get("/v1/system/media/artwork?v=abc")
        assert image.status_code == 200 and image.content == b"\x89PNG"
        assert image.headers["content-type"] == "image/png"
        media.artwork.data = None
        assert client.get("/v1/system/media/artwork").status_code == 404


def test_artwork_arriving_late_is_a_change():
    monitor, events = make_monitor(media=FakeMedia(SONG, {**SONG, "artwork": "/a?v=1"}))
    asyncio.run(monitor.refresh("media"))
    asyncio.run(monitor.refresh("media"))
    sent = [m for m in drain(events) if m["type"] == "system.media"]
    assert len(sent) == 2 and sent[1]["data"]["artwork"] == "/a?v=1"


def test_artwork_published_late_by_the_player_is_retried():
    from core.system.artwork import MAX_ATTEMPTS, ArtworkCache

    cache, calls = ArtworkCache(), []
    answers = [(None, None), (None, None), (b"\x89PNG-tarde", "image/png")]

    async def reader():
        calls.append(1)
        return answers.pop(0) if answers else (None, None)

    song = ("Spotify", "Tarde", "x", None)
    assert asyncio.run(cache.update(song, reader)) is None  # Aún no la tiene
    assert asyncio.run(cache.update(song, reader)) is None
    assert asyncio.run(cache.update(song, reader)).startswith("/v1/system/media/artwork?v=")
    for _ in range(10):
        asyncio.run(cache.update(song, reader))
    assert len(calls) == 3  # Con la carátula ya no se vuelve a leer

    other = ArtworkCache()
    for _ in range(MAX_ATTEMPTS + 3):
        asyncio.run(other.update(("sin carátula",), reader))
    assert len(calls) == 3 + MAX_ATTEMPTS  # Un reproductor sin carátula no se lee para siempre
