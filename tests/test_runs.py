"""Registro de ejecución (core/runs.py) y su uso desde el servicio de IA y el servidor."""

import asyncio
import sqlite3

import pytest

from ai.providers import ProviderError
from ai.service import AIService
from core.memory import MemoryStore
from core.persona import load_persona
from core.runs import Run, RunLog
from tests.fakes import FakeClient, FakeProvider
from tests.test_server import make_client, make_engine

PERSONA = load_persona("dva")


def test_run_log_records_summarizes_and_prunes(tmp_path):
    log = RunLog(tmp_path / "meka.db", keep=3)
    for i in range(5):
        log.record(Run("chat", "ollama", "gemma3", ok=i != 0, latency_ms=100, output_tokens=10))
    log.record(Run("vision", "claude", "opus", ok=True, latency_ms=300, input_tokens=50))
    recent = log.recent(10)
    assert len(recent) == 3  # Solo conserva las últimas `keep`
    assert recent[0]["provider"] == "claude" and recent[0]["task"] == "vision"
    summary = log.summary()
    assert summary["ollama"] == {
        "calls": 2, "errors": 0, "input_tokens": 0, "output_tokens": 20, "avg_latency_ms": 100,
    }  # fmt: skip
    assert summary["claude"]["input_tokens"] == 50


def test_service_logs_fallback_attempts_without_content(tmp_path):
    db = tmp_path / "meka.db"
    runs = RunLog(db)
    service = AIService(
        {"ai": {"provider": "claude", "fallback_provider": "ollama"}},
        memory=MemoryStore(db),
        persona=PERSONA,
        providers={
            "claude": FakeProvider("claude", error=ProviderError("caído")),
            "ollama": FakeProvider("ollama", "Respuesta local", local=True),
        },
        runs=runs,
    )
    answer = asyncio.run(service.answer(1, 1, "mi diario secreto dice que me gusta el ramen"))
    assert answer.ok and answer.provider == "ollama" and answer.model == "ollama-test"

    claude, ollama = reversed(runs.recent())
    assert (claude["provider"], claude["ok"], claude["error"]) == ("claude", False, "ProviderError")
    assert (ollama["provider"], ollama["ok"], ollama["output_tokens"]) == ("ollama", True, 5)
    # Nada del contenido llega a la tabla del registro
    dump = "\n".join(map(str, sqlite3.connect(db).execute("SELECT * FROM runs").fetchall()))
    assert "diario" not in dump and "Respuesta local" not in dump


def test_failed_answer_is_reported(tmp_path):
    service = AIService(
        {}, memory=MemoryStore(tmp_path / "m.db"), persona=PERSONA,
        providers={"ollama": FakeProvider("ollama", error=ProviderError("caído"), local=True)},
    )  # fmt: skip
    answer = asyncio.run(service.answer(1, 1, "hola"))
    assert not answer.ok and answer.messages[0] in PERSONA.lines["error"]


def test_pet_gets_error_emotion_when_the_brain_fails(tmp_path):
    engine = make_engine(tmp_path)
    engine.ai.providers["ollama"].client = FakeClient(fail=True)
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        ws.send_json({"type": "user.message", "data": {"text": "hola"}})
        assert ws.receive_json() == {"type": "emotion", "data": {"emotion": "thinking"}}
        message = ws.receive_json()
        assert message["type"] == "message" and message["data"]["emotion"] == "error"


def test_pet_gets_error_emotion_on_unexpected_crash(tmp_path):
    engine = make_engine(tmp_path, "hola")
    events = engine.bus.subscribe()

    async def crash(*args, **kwargs):
        raise RuntimeError("bug")

    engine.ai.answer = crash
    with pytest.raises(RuntimeError):
        asyncio.run(engine.chat("s", "u", "hola"))
    emotions = []
    while not events.empty():
        emotions.append(events.get_nowait()["data"].get("emotion"))
    assert emotions == ["thinking", "error"]  # Ya no se queda "pensando" para siempre


def test_runs_endpoint(tmp_path):
    engine = make_engine(tmp_path, "¡GG!")
    with make_client(engine, token="secreto") as client:
        assert client.get("/v1/runs").status_code == 401
        auth = {"Authorization": "Bearer secreto"}
        client.post("/v1/chat", json={"session": "s", "user": "u", "text": "hola"}, headers=auth)
        body = client.get("/v1/runs", headers=auth).json()
    assert body["runs"][0]["provider"] == "ollama" and body["runs"][0]["ok"] is True
    assert body["summary"]["ollama"]["calls"] == 1
