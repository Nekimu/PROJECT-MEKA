"""Privacidad (filosofía híbrida §5.3 y §8): lo privado nunca llega a la nube."""

import asyncio

import pytest

from ai import privacy
from ai.routing import PrivacyError, Router
from ai.service import AIService
from core.memory import MemoryStore
from core.persona import load_persona
from tests.fakes import FakeProvider
from tests.test_server import make_client, make_engine

PERSONA = load_persona("dva")


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------- detector

# Credenciales FALSAS armadas al vuelo: así ningún escáner de secretos (GitGuardian)
# las confunde con reales, y el detector sigue viendo el texto completo.
FAKE_JWT = ".".join(["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiJwcnVlYmEifQ", "x" * 43])
FAKE_ANTHROPIC_KEY = "sk-ant-" + "api03-" + "a" * 24
FAKE_AWS_KEY = "AKIA" + "EXAMPLE0" * 2


@pytest.mark.parametrize(
    "text",
    [
        "mi contraseña es Gato.2026",
        "el password: hunter2!",
        "Mi NIP es 4821",
        f"usa esta key {FAKE_ANTHROPIC_KEY}",
        f"{FAKE_AWS_KEY} es la de AWS",
        "mi tarjeta 4111 1111 1111 1111 vence en 2028",
        "CURP: GOMA800101HDFRRN09",
        FAKE_JWT,
        "-----BEGIN OPENSSH PRIVATE KEY-----",
    ],
)
def test_detects_sensitive_data(text):
    assert privacy.detect(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "olvidé mi contraseña otra vez",
        "¿qué es un token en IA?",
        "mi número de la suerte es 1234567890123",  # No pasa la validación Luhn
        "llámame al 55 1234 5678",
        "hoy jugué Overwatch con D.Va",
    ],
)
def test_ignores_normal_text(text):
    assert privacy.detect(text) is None


# ---------------------------------------------------------------------- enrutamiento


def providers(**names):
    return {name: FakeProvider(name, local=local) for name, local in names.items()}


def test_router_by_task_and_compatibility():
    router = Router(
        {"provider": "claude", "vision_provider": "gemini", "routing": {"document": "ollama"}},
        providers(claude=False, gemini=False, ollama=True),
    )
    assert router.order("chat") == ["claude"]
    assert router.order("vision") == ["gemini"]  # vision_provider sigue funcionando
    assert router.order("document") == ["ollama"]


def test_private_never_goes_to_the_cloud_even_as_fallback():
    router = Router(
        {"provider": "claude", "fallback_provider": "gemini", "privacy": {"provider": "ollama"}},
        providers(claude=False, gemini=False, ollama=True),
    )
    assert router.order("chat") == ["claude", "gemini"]
    assert router.order("chat", private=True) == ["ollama"]

    cloud_only = Router({"provider": "claude"}, providers(claude=False))
    with pytest.raises(PrivacyError):
        cloud_only.order("chat", private=True)


# ---------------------------------------------------------------------- servicio


def make_service(tmp_path, **ai):
    claude = FakeProvider("claude", *["nube"] * 5)
    ollama = FakeProvider("ollama", *["local"] * 5, local=True)
    service = AIService(
        {"ai": {"provider": "claude", **ai}},
        memory=MemoryStore(tmp_path / "meka.db"),
        persona=PERSONA,
        providers={"claude": claude, "ollama": ollama},
    )
    return service, claude, ollama


def test_private_request_and_sticky_session(tmp_path):
    service, claude, _ = make_service(tmp_path)
    assert run(service.answer("s", "u", "hola")).provider == "claude"

    answer = run(service.answer("s", "u", "esto es confidencial", private=True))
    assert answer.private and answer.provider == "ollama"
    # El historial ya tiene algo privado: el siguiente mensaje tampoco puede ir a la nube
    follow_up = run(service.answer("s", "u", "¿y qué opinas?"))
    assert follow_up.private and follow_up.provider == "ollama"
    assert len(claude.calls) == 1

    # Otra conversación no se ve afectada; reiniciar la sesión quita la marca
    assert run(service.answer("otra", "u", "hola")).provider == "claude"
    service.reset_conversation("s")
    assert run(service.answer("s", "u", "hola de nuevo")).provider == "claude"


def test_privacy_survives_a_restart(tmp_path):
    service, _, _ = make_service(tmp_path)
    run(service.answer("s", "u", "secreto", private=True))
    restarted, claude, _ = make_service(tmp_path)  # Misma base de datos
    assert run(restarted.answer("s", "u", "hola")).private and not claude.calls


def test_sensitive_text_switches_to_private(tmp_path):
    service, claude, _ = make_service(tmp_path)
    answer = run(service.answer("s", "u", "mi contraseña es Gato.2026, guárdala"))
    assert answer.private and not claude.calls


def test_documents_are_private_by_default(tmp_path):
    service, _, _ = make_service(tmp_path)
    assert run(service.answer("s", "u", "resume", task="document")).provider == "ollama"
    service, _, _ = make_service(tmp_path / "b", privacy={"documents": False})
    assert run(service.answer("s", "u", "resume", task="document")).provider == "claude"


def test_private_without_local_provider_is_not_sent(tmp_path):
    claude = FakeProvider("claude", "nube")
    service = AIService(
        {"ai": {"provider": "claude", "privacy": {"provider": "claude"}}},
        memory=MemoryStore(tmp_path / "meka.db"),
        persona=PERSONA,
        providers={"claude": claude, "ollama": FakeProvider("ollama", local=False)},
    )
    answer = run(service.answer("s", "u", "algo privado", private=True))
    assert not answer.ok and answer.private and not claude.calls


# ---------------------------------------------------------------------- API


def test_api_private_flag(tmp_path):
    engine = make_engine(tmp_path, "solo en tu PC")
    with make_client(engine) as client:
        body = client.post(
            "/v1/chat", json={"session": "s", "user": "u", "text": "hola", "private": True}
        ).json()
    assert body["replies"][0]["private"] is True
    assert engine.ai.history.is_private("s")


# ---------------------------------------------------------------------- recuerdos (T-031)


def test_private_facts_are_hidden_when_asked(tmp_path):
    memory = MemoryStore(tmp_path / "meka.db")
    memory.add_fact("u", "mi perro se llama Toby")
    memory.add_fact("u", "mi diagnóstico es reservado", private=True)
    assert memory.get_facts("u") == ["mi perro se llama Toby", "mi diagnóstico es reservado"]
    assert memory.get_facts("u", include_private=False) == ["mi perro se llama Toby"]
    assert memory.search("u", "diagnóstico", include_private=False) == ["mi perro se llama Toby"]

    # Repetido en privado: pasa a privado
    assert not memory.add_fact("u", "mi perro se llama Toby", private=True)
    assert memory.get_facts("u", include_private=False) == []

    memory.set_vectors("m", [(1, [1.0, 0.0]), (2, [0.9, 0.1])])
    assert memory.nearest("u", "m", [1.0, 0.0], 5, include_private=False) == []
    assert len(memory.nearest("u", "m", [1.0, 0.0], 5)) == 2


def test_old_databases_are_migrated(tmp_path):
    import sqlite3

    db = tmp_path / "vieja.db"
    old = sqlite3.connect(db)
    old.execute(
        "CREATE TABLE facts (id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, fact TEXT NOT NULL,"
        " created_at REAL NOT NULL, UNIQUE (user_id, fact))"
    )
    old.execute(
        "INSERT INTO facts (user_id, fact, created_at) VALUES ('u', 'me gusta el ramen', 0)"
    )
    old.commit()
    old.close()

    memory = MemoryStore(db)
    assert memory.get_facts("u", include_private=False) == ["me gusta el ramen"]
    memory.add_fact("u", "dato privado", private=True)
    assert memory.get_facts("u", include_private=False) == ["me gusta el ramen"]


def test_private_memories_only_reach_local_prompts(tmp_path):
    service, claude, ollama = make_service(tmp_path)
    run(service.answer("s1", "u", "Recuerda esto: mi diagnóstico es reservado", private=True))
    assert service.memory.get_facts("u", include_private=False) == []

    # Conversación normal con Claude (nube): el recuerdo privado no entra en el prompt
    run(service.answer("s2", "u", "¿te acuerdas de mi diagnóstico?"))
    assert "diagnóstico es reservado" not in claude.calls[-1]["system"]

    # Conversación privada (Ollama, local): sí puede usarlo
    run(service.answer("s3", "u", "¿te acuerdas de mi diagnóstico?", private=True))
    assert "diagnóstico es reservado" in ollama.calls[-1]["system"]


def test_cloud_fallback_also_blocks_private_memories(tmp_path):
    """Aunque el principal sea local, si el respaldo es la nube el prompt podría acabar allí."""
    service, _, ollama = make_service(tmp_path, provider="ollama", fallback_provider="claude")
    service.memory.add_fact("u", "mi diagnóstico es reservado", private=True)
    run(service.answer("s", "u", "¿te acuerdas de mi diagnóstico?"))
    assert "diagnóstico es reservado" not in ollama.calls[-1]["system"]


def test_api_can_hide_private_memories(tmp_path):
    engine = make_engine(tmp_path)
    with make_client(engine) as client:
        client.post("/v1/users/u/memories", json={"fact": "público"})
        client.post("/v1/users/u/memories", json={"fact": "secreto", "private": True})
        assert client.get("/v1/users/u/memories").json()["memories"] == ["público", "secreto"]
        hidden = client.get("/v1/users/u/memories", params={"include_private": "false"})
        assert hidden.json()["memories"] == ["público"]
