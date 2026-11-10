import asyncio

import pytest

from ai.providers import ProviderError, RefusalError
from ai.providers.ollama import OllamaProvider
from ai.service import AIService
from core.memory import MemoryStore
from core.persona import Persona, load_persona
from tests.fakes import FakeClient, FakeProvider

TEST_PERSONA = Persona(
    id="prueba",
    name="Prueba",
    prompt="Eres un personaje de prueba.",
    lines={"error": ["ERROR DE PRUEBA"], "vision_error": ["VISION"], "empty_reply": ["VACIO"]},
)


OLLAMA_KEYS = {"model", "temperature", "keep_alive", "options", "vision_options"}


def make_service(tmp_path, client, **overrides):
    ollama = {"model": "test-model", "temperature": 0.3}
    ollama.update({k: v for k, v in overrides.items() if k in OLLAMA_KEYS})
    ai = {k: v for k, v in overrides.items() if k not in OLLAMA_KEYS}
    return AIService(
        config={"ai": ai},
        memory=MemoryStore(tmp_path / "meka.db"),
        persona=TEST_PERSONA,
        providers={"ollama": OllamaProvider(ollama, client=client)},
    )


def run(coro):
    return asyncio.run(coro)


def test_options_come_from_config(tmp_path):
    client = FakeClient("Hola")
    service = make_service(tmp_path, client, keep_alive="5m", options={"num_predict": 64})
    run(service.generate_response(1, 1, "hola"))
    call = client.calls[0]
    assert call["options"]["temperature"] == 0.3  # antes estaba fijo a 0.8
    assert call["options"]["num_predict"] == 64
    assert call["keep_alive"] == "5m"


def test_history_is_isolated_per_chat(tmp_path):
    client = FakeClient("Respuesta A", "Respuesta B", "Respuesta A2")
    service = make_service(tmp_path, client)
    run(service.generate_response(chat_id=1, user_id=1, user_text="secreto del chat 1"))
    run(service.generate_response(chat_id=2, user_id=2, user_text="hola desde chat 2"))
    run(service.generate_response(chat_id=1, user_id=1, user_text="sigo en chat 1"))

    chat2_prompt = str(client.calls[1]["messages"])
    assert "secreto del chat 1" not in chat2_prompt
    assert "secreto del chat 1" in str(client.calls[2]["messages"])


def test_chat_keeps_working_after_image_is_deleted(tmp_path):
    """Regresión: la ruta de la imagen quedaba en el historial y rompía el chat."""
    image = tmp_path / "foto.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    client = FakeClient("¡Qué foto tan linda!", "¡Claro que me acuerdo!")
    service = make_service(tmp_path, client)

    run(service.generate_multimodal_response(1, "mira mi cosplay", image))
    image.unlink()  # handlers.py borra el archivo tras procesarlo
    reply = run(service.generate_response(1, 1, "¿te gustó la foto?"))

    assert reply == ["¡Claro que me acuerdo!"]
    assert "mira mi cosplay" in str(client.calls[1]["messages"])


def test_failed_call_does_not_pollute_history(tmp_path):
    service = make_service(tmp_path, FakeClient(fail=True))
    assert run(service.generate_response(1, 1, "hola")) == ["ERROR DE PRUEBA"]
    assert service.history.get(1) == []


def test_error_reply_does_not_leak_exception_details(tmp_path):
    service = make_service(tmp_path, FakeClient(fail=True))
    reply = run(service.generate_response(1, 1, "hola"))
    assert "Ollama caído" not in " ".join(reply)


def test_remember_and_recall_are_per_user(tmp_path):
    client = FakeClient("Anotado", "Sí", "No sé")
    service = make_service(tmp_path, client)
    run(service.generate_response(1, 1, "Recuerda  esto:  mi color favorito es el azul"))
    assert service.memory.get_facts(1) == ["mi color favorito es el azul"]

    run(service.generate_response(1, 1, "¿Te acuerdas de mi color favorito?"))
    assert "azul" in client.calls[1]["messages"][0]["content"]

    run(service.generate_response(2, 2, "¿Te acuerdas de mi color favorito?"))
    assert "azul" not in client.calls[2]["messages"][0]["content"]


def test_documents_do_not_trigger_memory(tmp_path):
    service = make_service(tmp_path, FakeClient("Leído"))
    run(service.generate_response(1, 1, "contenido: recuerda esto: algo", use_memory=False))
    assert service.memory.get_facts(1) == []


def test_reset_conversation(tmp_path):
    service = make_service(tmp_path, FakeClient("Hola"))
    run(service.generate_response(1, 1, "hola"))
    service.reset_conversation(1)
    assert service.history.get(1) == []


def test_history_size_limit(tmp_path):
    service = make_service(tmp_path, FakeClient(*["ok"] * 5), history_size=4)
    for i in range(5):
        run(service.generate_response(1, 1, f"mensaje {i}"))
    assert len(service.history.get(1)) == 4


def test_system_prompt_uses_persona_and_shared_format_rules(tmp_path):
    client = FakeClient("Hola")
    service = make_service(tmp_path, client)
    run(service.generate_response(1, 1, "hola"))
    system = client.calls[0]["messages"][0]["content"]
    assert system.startswith("Eres un personaje de prueba.")
    assert '"---"' in system and "[AUDIO]" in system  # reglas de formato comunes


def test_vision_prompt_names_the_persona(tmp_path):
    image = tmp_path / "foto.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    client = FakeClient("Bonita")
    service = make_service(tmp_path, client)
    run(service.generate_multimodal_response(1, "mira", image))
    assert client.calls[0]["messages"][0]["content"].startswith("Eres Prueba.")


def test_real_persona_pack_drives_replies(tmp_path):
    marin = load_persona("marin")
    service = AIService(
        config={"ai": {}},
        memory=MemoryStore(tmp_path / "meka.db"),
        persona=marin,
        providers={"ollama": OllamaProvider({}, client=FakeClient(fail=True))},
    )
    assert run(service.generate_response(1, 1, "hola"))[0] in marin.lines["error"]


# ---------------------------------------------------------------------- enrutamiento


def routed_service(tmp_path, providers, **ai):
    return AIService(
        config={"ai": ai},
        memory=MemoryStore(tmp_path / "meka.db"),
        persona=TEST_PERSONA,
        providers=providers,
    )


def test_history_survives_restart(tmp_path):
    """El historial vive en SQLite: un reinicio de MEKA Core no olvida la conversación."""
    run(make_service(tmp_path, FakeClient("Hola, Nekimu")).generate_response(1, 1, "soy Nekimu"))
    client = FakeClient("Te recuerdo")
    run(make_service(tmp_path, client).generate_response(1, 1, "¿quién soy?"))
    assert "soy Nekimu" in str(client.calls[0]["messages"])


def test_each_task_uses_its_provider(tmp_path):
    claude, gemini = FakeProvider("claude", "Hola"), FakeProvider("gemini", "Una foto")
    service = routed_service(
        tmp_path, {"claude": claude, "gemini": gemini}, provider="claude", vision_provider="gemini"
    )
    image = tmp_path / "foto.png"
    image.write_bytes(b"\x89PNG")
    run(service.generate_response(1, 1, "hola"))
    run(service.generate_multimodal_response(1, "mira", image))
    assert len(claude.calls) == 1 and len(gemini.calls) == 1
    assert gemini.calls[0]["vision"] and gemini.calls[0]["messages"][0]["images"] == [str(image)]
    assert claude.calls[0]["system"].startswith("Eres un personaje de prueba.")


@pytest.mark.parametrize("error", [ProviderError("caído"), RefusalError("declinó")])
def test_fallback_provider_takes_over(tmp_path, error):
    claude = FakeProvider("claude", error=error)
    ollama = FakeProvider("ollama", "Respuesta local", local=True)
    service = routed_service(
        tmp_path,
        {"claude": claude, "ollama": ollama},
        provider="claude",
        fallback_provider="ollama",
    )
    assert run(service.generate_response(1, 1, "hola")) == ["Respuesta local"]


def test_local_only_never_calls_the_cloud(tmp_path):
    claude = FakeProvider("claude", "Desde la nube")
    ollama = FakeProvider("ollama", "Desde tu PC", local=True)
    service = routed_service(
        tmp_path, {"claude": claude, "ollama": ollama}, provider="claude", local_only=True
    )
    assert run(service.generate_response(1, 1, "hola")) == ["Desde tu PC"]
    assert claude.calls == []
