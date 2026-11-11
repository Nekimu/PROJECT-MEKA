"""El contrato publicado (GET /v1/contract) es exactamente lo que hace el núcleo."""

import hashlib
import json
import threading

import pytest

from core import contract
from tests.fakes import FakeClient
from tests.test_server import make_client, make_engine

# Huella del contrato por versión. Si este test falla, cambiaste eventos, campos, emociones o
# rutas: sube CONTRACT_VERSION en core/contract.py (reglas en su docstring), anótalo en su
# historial y añade aquí la huella nueva. Si quitaste o renombraste algo, avisa antes al
# frontend en coordinacion/README.md.
FINGERPRINTS = {
    "1.4": "dc763f817ee8390f",
    "1.5": "2b570112825a18d4",
    "1.6": "0e5f228573640fe0",
    "1.7": "d59efebe67ae41cc",
    "1.8": "b150bda941daf0ec",
}


def fingerprint(document: dict) -> str:
    payload = {key: value for key, value in document.items() if key != "version"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def test_contract_changes_require_a_new_version(tmp_path):
    with make_client(make_engine(tmp_path)) as client:
        document = client.get("/v1/contract").json()
        assert client.get("/v1/health").json()["contract"] == document["version"]
    current = fingerprint(document)
    assert FINGERPRINTS.get(document["version"]) == current, (
        f"El contrato cambió (huella {current}) sin subir CONTRACT_VERSION "
        f"({document['version']}). Lee la cabecera de este test."
    )


def test_contract_is_public_and_complete(tmp_path):
    with make_client(make_engine(tmp_path), token="secreto") as client:
        document = client.get("/v1/contract").json()  # Sin token, como /v1/health
    assert set(document["emotions"]) == set(contract.EMOTIONS)
    assert set(document["events"]["inbound"]) == {
        "client.hello",
        "user.message",
        "user.confirm",
        "user.media",
        "user.notification",
    }
    rest = {(r["method"], r["path"]): r["auth"] for r in document["rest"]}
    assert rest[("GET", "/v1/health")] is False and rest[("GET", "/v1/contract")] is False
    assert rest[("POST", "/v1/chat")] is True and rest[("WEBSOCKET", "/v1/events")] is True
    assert ("POST", "/v1/confirmations/{confirmation_id}") in rest


def test_every_event_the_core_emits_follows_the_contract(tmp_path):
    """Recorre lo que el núcleo emite de verdad: chat, fallos, permisos y eventos externos."""
    engine = make_engine(tmp_path, "¡Hola! [AUDIO]")
    events = engine.bus.subscribe()
    with make_client(engine) as client:
        client.post("/v1/chat", json={"session": "s", "user": "u", "text": "hola"})
        engine.ai.providers["ollama"].client = FakeClient(fail=True)
        client.post("/v1/chat", json={"session": "s", "user": "u", "text": "otra vez"})
        engine.stt.text = ""  # Nota de voz que no se entiende → emotion: sad
        client.post(
            "/v1/voice",
            data={"session": "s", "user": "u"},
            files={"file": ("nota.ogg", b"OggS", "audio/ogg")},
        )
        for type_, data in [
            ("agent.working", {"task": "Ordenar"}),
            ("agent.done", {}),
            ("agent.error", {"message": "falló"}),
            ("emotion", {"emotion": "celebrate"}),
            ("budget.low", {}),
        ]:
            assert client.post("/v1/events", json={"type": type_, "data": data}).status_code == 202

        thread = threading.Thread(
            target=lambda: client.post("/v1/confirmations", json={"action": "x", "timeout": 1})
        )
        thread.start()
        thread.join(timeout=10)  # Caduca → agent.confirmed con by: timeout

    emitted = []
    while not events.empty():
        emitted.append(events.get_nowait())
    types = {event["type"] for event in emitted}
    assert {"message", "emotion", "agent.confirm", "agent.confirmed", "agent.working"} <= types
    for event in emitted:
        assert contract.validate(event["type"], event["data"]) == [], event


@pytest.mark.parametrize(
    ("type_", "data"),
    [
        ("client.hello", {"client": "pet", "skin": "meka"}),
        ("user.message", {"text": "hola", "private": True}),
        ("user.confirm", {"id": "a1b2", "approved": False}),
    ],
)
def test_client_messages_follow_the_contract(type_, data):
    assert contract.validate(type_, data, inbound=True) == []


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"type": "message", "data": {"emotion": "happy"}}, "falta el campo obligatorio 'text'"),
        ({"type": "emotion", "data": {"emotion": "furiosa"}}, "emotion.emotion"),
        ({"type": "agent.working", "data": {"task": 42}}, "agent.working.task"),
        ({"type": "agent.bailando", "data": {}}, "Evento desconocido"),
    ],
)
def test_external_events_are_validated(tmp_path, data, error):
    with make_client(make_engine(tmp_path)) as client:
        response = client.post("/v1/events", json=data)
    assert response.status_code == 422 and error in response.json()["detail"]


def test_unknown_extra_fields_are_allowed():
    """Compatibilidad hacia delante: un núcleo más nuevo puede añadir campos."""
    assert contract.validate("agent.done", {"summary": "ok", "nuevo": 1}) == []
