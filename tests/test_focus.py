"""Modo concentración (T-050): retener lo que distrae, dejar pasar lo importante."""

import asyncio
import time

import pytest

from core import contract
from core.events import EventBus
from core.focus import FocusMode
from tests.test_server import make_client, make_engine


def make_focus(**cfg):
    bus = EventBus()
    events = bus.subscribe()
    return FocusMode({"focus": cfg}, bus), bus, events


def drain(queue):
    return [queue.get_nowait() for _ in range(queue.qsize())]


def publish_everything(bus):
    bus.publish("system.notification", id=1, app="WhatsApp", title="Ana", time=1.0)
    bus.publish("system.notification", id=2, app="Teams", title="Llamada", time=2.0)
    bus.publish("system.media", playing=True, title="Idol")
    bus.publish("system.battery", percent=60, charging=False)
    bus.publish("system.battery", percent=12, charging=False)  # Crítica: pasa
    bus.publish("message", text="Respuesta por Telegram", emotion="happy")
    bus.publish("agent.working", task="Ordenar")
    bus.publish("agent.done", summary="Listo")
    bus.publish("agent.confirm", id="a1", action="borrar", timeout=60, expires_at=1.0)
    bus.publish("agent.error", message="falló")
    bus.publish("emotion", emotion="thinking")


def test_holds_distractions_and_lets_important_things_through():
    focus, bus, events = make_focus(allow_apps=["Teams"])

    async def scenario():
        await focus.start(25)
        drain(events)  # focus.started
        publish_everything(bus)
        passed = drain(events)
        return passed, focus.stop("user"), drain(events)

    passed, summary, ended = asyncio.run(scenario())
    assert [(e["type"], e["data"].get("app") or e["data"].get("percent")) for e in passed] == [
        ("system.notification", "Teams"),  # App importante
        ("system.battery", 12),  # Batería crítica
        ("agent.confirm", None),  # Un agente espera tu permiso
        ("agent.error", None),
        ("emotion", None),
    ]
    assert summary == {"reason": "user", "held": 6, "notifications": 1}
    assert ended == [{"type": "focus.ended", "data": summary}]


def test_everything_flows_again_after_stopping():
    focus, bus, events = make_focus()

    async def scenario():
        await focus.start(5)
        focus.stop()
        drain(events)
        publish_everything(bus)
        return drain(events)

    assert len(asyncio.run(scenario())) == 11
    assert focus.stop() is None  # Ya no había sesión


def test_session_expires_by_itself():
    focus, _, events = make_focus()

    async def scenario():
        await focus.start(1)
        focus.until = time.time() + 0.05  # Acortamos la sesión para el test
        focus._cancel_timer()
        focus._timer = asyncio.create_task(focus._expire(focus.until))
        await asyncio.sleep(0.2)
        return drain(events)

    started, ended = asyncio.run(scenario())
    assert started["type"] == "focus.started" and started["data"]["minutes"] == 1
    assert ended == {
        "type": "focus.ended",
        "data": {"reason": "timeout", "held": 0, "notifications": 0},
    }
    assert focus.status()["active"] is False


def test_extending_keeps_the_summary_and_validates_minutes():
    focus, bus, _ = make_focus(max_minutes=60)

    async def scenario():
        await focus.start(10)
        bus.publish("system.notification", id=1, app="X", time=1.0)
        status = await focus.start(30)  # Ampliar no reinicia lo retenido
        with pytest.raises(ValueError):
            await focus.start(61)
        with pytest.raises(ValueError):
            await focus.start(0)
        return status, focus.stop()

    status, summary = asyncio.run(scenario())
    assert status["active"] and status["held"] == 1 and 29 * 60 < status["remaining"] <= 30 * 60
    assert summary["notifications"] == 1


def test_focus_events_follow_the_contract():
    focus, _, events = make_focus()

    async def scenario():
        await focus.start(15)
        focus.stop()
        return drain(events)

    for event in asyncio.run(scenario()):
        assert contract.validate(event["type"], event["data"]) == [], event


# ---------------------------------------------------------------------- API y WebSocket


def test_api(tmp_path):
    with make_client(make_engine(tmp_path)) as client:
        assert client.get("/v1/focus").json()["active"] is False
        assert client.delete("/v1/focus").status_code == 404
        started = client.post("/v1/focus", json={"minutes": 50}).json()
        assert started["active"] and started["remaining"] > 49 * 60
        assert client.post("/v1/focus", json={"minutes": 0}).status_code == 422
        assert client.post("/v1/focus", json={"minutes": 999}).status_code == 422  # > max
        assert client.delete("/v1/focus").json() == {
            "reason": "user",
            "held": 0,
            "notifications": 0,
        }


def test_pet_chat_still_answers_while_focused(tmp_path):
    engine = make_engine(tmp_path, "¡Concéntrate, tú puedes!")
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        ws.send_json({"type": "user.focus", "data": {"action": "start", "minutes": 25}})
        assert ws.receive_json()["type"] == "focus.started"
        ws.send_json({"type": "user.message", "data": {"text": "¿cómo voy?"}})
        assert ws.receive_json() == {"type": "emotion", "data": {"emotion": "thinking"}}
        assert ws.receive_json() == {
            "type": "message",
            "data": {"text": "¡Concéntrate, tú puedes!", "emotion": "happy"},
        }  # Llega directa, aunque la difusión esté retenida
        ws.send_json({"type": "user.focus", "data": {"action": "stop"}})
        ended = ws.receive_json()
    assert ended["type"] == "focus.ended"
    assert ended["data"]["held"] == 0  # Tu propia respuesta no cuenta como pendiente
