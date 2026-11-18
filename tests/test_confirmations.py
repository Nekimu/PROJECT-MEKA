"""Confirmación de acciones (T-003): agent.confirm → user.confirm → agent.confirmed."""

import asyncio
import threading

from core.confirmations import ConfirmationRegistry
from core.events import EventBus
from tests.test_server import make_client, make_engine


def drain(queue) -> list[dict]:
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    return events


def test_approved_by_the_user():
    async def scenario():
        bus = EventBus()
        events = bus.subscribe()
        registry = ConfirmationRegistry(bus)
        task = asyncio.create_task(registry.ask("borrar 3 duplicados", details={"files": 3}))
        await asyncio.sleep(0)
        [pending] = registry.pending()
        assert registry.resolve(pending["id"], True, by="pet")
        assert not registry.resolve(pending["id"], False)  # Ya resuelto
        return await task, drain(events), registry.pending()

    approved, events, pending = asyncio.run(scenario())
    assert approved and pending == []
    confirm, confirmed = events
    assert confirm["type"] == "agent.confirm"
    assert confirm["data"]["action"] == "borrar 3 duplicados"
    assert confirm["data"]["details"] == {"files": 3}
    assert 0 < confirm["data"]["timeout"] <= 120 and confirm["data"]["expires_at"] > 0
    assert confirmed == {
        "type": "agent.confirmed",
        "data": {"id": confirm["data"]["id"], "approved": True, "by": "pet"},
    }


def test_no_answer_means_no():
    async def scenario():
        bus = EventBus()
        events = bus.subscribe()
        approved = await ConfirmationRegistry(bus).ask("enviar correo", timeout=0.05)
        return approved, drain(events)

    approved, events = asyncio.run(scenario())
    assert approved is False
    assert events[-1]["type"] == "agent.confirmed"
    assert events[-1]["data"]["approved"] is False and events[-1]["data"]["by"] == "timeout"


def test_unknown_ids_and_shutdown():
    async def scenario():
        registry = ConfirmationRegistry(EventBus())
        assert not registry.resolve("no-existe", True)
        task = asyncio.create_task(registry.ask("mover archivos"))
        await asyncio.sleep(0)
        registry.cancel_all()  # Al apagar, todo lo pendiente se rechaza
        return await task

    assert asyncio.run(scenario()) is False


def test_permission_flow_through_the_pet(tmp_path):
    """Un agente pide permiso por REST; la mascota lo ve por WebSocket y lo concede."""
    engine = make_engine(tmp_path)
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        ws.send_json({"type": "client.hello", "data": {"client": "pet"}})
        result = {}

        def agent():
            result["response"] = client.post(
                "/v1/confirmations", json={"action": "aplicar cambios", "timeout": 30}
            )

        thread = threading.Thread(target=agent)
        thread.start()
        confirm = ws.receive_json()
        assert confirm["type"] == "agent.confirm" and confirm["data"]["action"] == "aplicar cambios"
        assert client.get("/v1/confirmations").json()["pending"][0]["id"] == confirm["data"]["id"]

        ws.send_json(
            {"type": "user.confirm", "data": {"id": confirm["data"]["id"], "approved": True}}
        )
        confirmed = ws.receive_json()
        thread.join(timeout=10)

    assert confirmed["type"] == "agent.confirmed"
    assert confirmed["data"] == {"id": confirm["data"]["id"], "approved": True, "by": "pet"}
    assert result["response"].json() == {"approved": True}


def test_rest_answers_and_validation(tmp_path):
    engine = make_engine(tmp_path)
    with make_client(engine) as client:
        missing = client.post("/v1/confirmations/no-existe", json={"approved": True})
        assert missing.status_code == 404
        # agent.confirm lo emite el núcleo: publicarlo a mano no tendría id del registro
        raw = client.post("/v1/events", json={"type": "agent.confirm", "data": {"action": "x"}})
        assert raw.status_code == 422 and "/v1/confirmations" in raw.json()["detail"]
        too_long = client.post("/v1/confirmations", json={"action": "x", "timeout": 9999})
        assert too_long.status_code == 422
