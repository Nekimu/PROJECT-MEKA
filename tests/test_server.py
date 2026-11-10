"""MEKA Core de extremo a extremo: motor real con modelos simulados, servidor y cliente."""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from ai.service import AIService
from channels.client import CoreClient
from core.config import core_url, default_user
from core.engine import MekaEngine
from core.memory import MemorySystem
from core.persona import load_persona
from server.app import ConfigError, create_app, server_token
from tests.fakes import FakeClient, FakeSTT, FakeTTS

PERSONA = load_persona("dva")


def make_engine(tmp_path, *replies, broadcast=True):
    config = {
        "paths": {"temp_dir": str(tmp_path / "temp")},
        "server": {"broadcast_messages": broadcast},
    }
    memory = MemorySystem(tmp_path / "memory.json")
    ai = AIService(config, client=FakeClient(*replies), memory=memory, persona=PERSONA)
    return MekaEngine(
        config,
        persona=PERSONA,
        memory=memory,
        ai=ai,
        stt=FakeSTT(),
        tts=FakeTTS(tmp_path),
    )


def make_client(engine, token="", **server):
    config = {"server": {"token": token, **server}}
    return TestClient(create_app(config, engine, startup_checks=False))


AUTH = {"Authorization": "Bearer secreto"}


# ---------------------------------------------------------------------- seguridad


def test_token_is_required_outside_localhost():
    with pytest.raises(ConfigError):
        server_token({"server": {"host": "0.0.0.0"}})
    assert server_token({"server": {"host": "0.0.0.0", "token": "x"}}) == "x"
    assert server_token({"server": {"host": "127.0.0.1"}}) == ""


def test_health_is_public_but_the_rest_needs_token(tmp_path):
    with make_client(make_engine(tmp_path), token="secreto") as client:
        assert client.get("/v1/health").json()["persona"] == "dva"
        assert client.get("/v1/persona").status_code == 401
        assert (
            client.get("/v1/persona", headers={"Authorization": "Bearer otro"}).status_code == 401
        )
        persona = client.get("/v1/persona", headers=AUTH).json()
        assert persona["name"] == PERSONA.name
        assert "prompt" not in persona  # La personalidad no sale del núcleo


def test_foreign_websites_are_rejected(tmp_path):
    with make_client(make_engine(tmp_path), allowed_origins=["https://mi-app.example"]) as client:
        assert (
            client.get("/v1/health", headers={"Origin": "https://malicioso.example"}).status_code
            == 403
        )
        assert (
            client.get("/v1/health", headers={"Origin": "http://localhost:5173"}).status_code == 200
        )
        assert client.get("/v1/health", headers={"Origin": "tauri://localhost"}).status_code == 200
        assert (
            client.get("/v1/health", headers={"Origin": "https://mi-app.example"}).status_code
            == 200
        )


# ---------------------------------------------------------------------- conversación


def test_chat_returns_replies_and_audio(tmp_path):
    engine = make_engine(tmp_path, "¡Hola! [AUDIO] --- ¿Jugamos? [STICKER]")
    with make_client(engine) as client:
        replies = client.post(
            "/v1/chat", json={"session": "telegram:1", "user": "1", "text": "hola"}
        ).json()["replies"]
        assert [r["text"] for r in replies] == ["¡Hola!", "¿Jugamos?"]
        assert replies[1]["sticker"] and not replies[1]["audio"]
        assert engine.tts.released == 1  # Se libera una sola vez por tanda

        audio = client.get(f"/v1/audio/{replies[0]['audio']}")
        assert audio.status_code == 200 and audio.content.startswith(b"OggS")
        # Un audio se entrega una sola vez
        assert client.get(f"/v1/audio/{replies[0]['audio']}").status_code == 404


def test_chat_without_audio_does_not_touch_tts(tmp_path):
    engine = make_engine(tmp_path, "Hola [AUDIO]")
    with make_client(engine) as client:
        body = {"session": "s", "user": "1", "text": "hola", "audio": False}
        replies = client.post("/v1/chat", json=body).json()["replies"]
    assert replies[0]["audio"] is None and engine.tts.generated == []


def test_voice_is_transcribed_and_answered(tmp_path):
    engine = make_engine(tmp_path, "Te escuché")
    with make_client(engine) as client:
        response = client.post(
            "/v1/voice",
            data={"session": "s", "user": "1", "audio": "false"},
            files={"file": ("voz.ogg", b"OggS...")},
        ).json()
    assert response["transcription"] == "hola desde la voz"
    assert response["replies"][0]["text"] == "Te escuché"
    assert engine.stt.released == 1
    assert not any(engine.uploads_dir.iterdir())  # La subida se borra


def test_documents_are_analyzed_and_unknown_types_rejected(tmp_path):
    engine = make_engine(tmp_path, "Es una lista de la compra (con IVA)")
    with make_client(engine, max_upload_mb=1) as client:
        response = client.post(
            "/v1/files",
            data={"session": "s", "user": "1"},
            files={"file": ("lista.txt", b"leche, pan")},
        )
        assert response.json()["replies"][0]["text"] == "Es una lista de la compra (con IVA)"
        prompt = engine.ai.client.calls[0]["messages"][-1]["content"]
        assert "leche, pan" in prompt and "lista.txt" in prompt

        assert (
            client.post(
                "/v1/files", data={"session": "s", "user": "1"}, files={"file": ("x.exe", b"MZ")}
            ).status_code
            == 415
        )
        big = b"x" * (1024 * 1024 + 1)
        assert (
            client.post(
                "/v1/files", data={"session": "s", "user": "1"}, files={"file": ("a.txt", big)}
            ).status_code
            == 413
        )


def test_memories_and_reset(tmp_path):
    engine = make_engine(tmp_path, "Anotado", "Hola de nuevo")
    with make_client(engine) as client:
        client.post(
            "/v1/chat",
            json={"session": "s", "user": "7", "text": "Recuerda esto: me gusta el ramen"},
        )
        assert client.get("/v1/users/7/memories").json() == {"memories": ["me gusta el ramen"]}
        assert client.post("/v1/users/7/memories", json={"fact": "juego Overwatch"}).json() == {
            "added": True
        }
        assert client.get("/v1/users/8/memories").json() == {"memories": []}  # Aislada por usuario

        assert client.post("/v1/sessions/s/reset").status_code == 204
        assert engine.ai.history.get("s") == []
        assert client.delete("/v1/users/7/memories").json() == {"removed": 2}


# ---------------------------------------------------------------------- eventos


def test_websocket_receives_events_and_chats(tmp_path):
    engine = make_engine(tmp_path, "¡Hola, mascota!")
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        ws.send_json({"type": "client.hello", "data": {"client": "pet", "skin": "meka"}})

        accepted = client.post(
            "/v1/events", json={"type": "agent.working", "data": {"task": "Ordenar"}}
        )
        assert accepted.status_code == 202 and accepted.json()["delivered"] == 1
        assert ws.receive_json() == {"type": "agent.working", "data": {"task": "Ordenar"}}

        ws.send_json({"type": "user.message", "data": {"text": "hola"}})
        assert ws.receive_json() == {"type": "emotion", "data": {"emotion": "thinking"}}
        assert ws.receive_json() == {
            "type": "message",
            "data": {"text": "¡Hola, mascota!", "emotion": "happy"},
        }


def test_invalid_events_are_rejected(tmp_path):
    with make_client(make_engine(tmp_path)) as client:
        assert client.post("/v1/events", json={"type": "borrar.todo"}).status_code == 422
        bad = {"type": "emotion", "data": {"emotion": "furiosa"}}
        assert client.post("/v1/events", json=bad).status_code == 422


def test_websocket_requires_token(tmp_path):
    from starlette.websockets import WebSocketDisconnect

    with make_client(make_engine(tmp_path), token="secreto") as client:
        with pytest.raises(WebSocketDisconnect), client.websocket_connect("/v1/events") as ws:
            ws.receive_json()
        with client.websocket_connect("/v1/events?token=secreto") as ws:
            client.post("/v1/events", json={"type": "budget.low"}, headers=AUTH)
            assert ws.receive_json()["type"] == "budget.low"


# ---------------------------------------------------------------------- cliente


def test_core_client_talks_to_the_server(tmp_path):
    """El mismo CoreClient que usan Telegram y MCP, contra la app ASGI real."""
    engine = make_engine(tmp_path, "¡GG! [AUDIO]")
    app = create_app({"server": {"token": "secreto"}}, engine, startup_checks=False)

    async def scenario():
        core = CoreClient("http://meka", "secreto", transport=httpx.ASGITransport(app=app))
        try:
            persona = await core.wait_ready(attempts=1)
            replies = await core.chat("telegram:1", "1", "hola")
            audio = await core.audio(replies[0]["audio"])
            added = await core.remember("1", "main D.Va")
            facts = await core.memories("1")
            removed = await core.forget("1")
            await core.reset("telegram:1")
            return persona, replies, audio, added, facts, removed
        finally:
            await core.close()

    persona, replies, audio, added, facts, removed = asyncio.run(scenario())
    assert persona.name == PERSONA.name and persona.line("reset")
    assert replies[0]["text"] == "¡GG!" and audio.startswith(b"OggS")
    assert (added, facts, removed) == (True, ["main D.Va"], 1)


def test_core_url_and_default_user():
    assert core_url({}) == "http://127.0.0.1:8765"
    assert core_url({"server": {"host": "0.0.0.0", "port": 9000}}) == "http://127.0.0.1:9000"
    assert core_url({"server": {"url": "http://pc.tailnet:8765/"}}) == "http://pc.tailnet:8765"
    assert default_user({"telegram": {"allowed_user_ids": [42, 7]}}) == "42"
    assert default_user({}) == "local"
