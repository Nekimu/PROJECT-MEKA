import asyncio
from types import SimpleNamespace

from ollama import Image, Message

from ai.service import AIService
from core.memory import MemorySystem
from core.persona import Persona, load_persona


class FakeClient:
    """Imita ollama.Client: registra las llamadas y devuelve respuestas programadas."""

    def __init__(self, *replies, fail=False):
        self.replies = list(replies)
        self.fail = fail
        self.calls = []

    def chat(self, **kwargs):
        # Igual que el cliente real: serializa los mensajes, lo que lee del disco cada imagen
        for message in kwargs["messages"]:
            images = [Image(value=image) for image in message.get("images") or []]
            Message(**{**message, "images": images or None}).model_dump()
        self.calls.append(kwargs)
        if self.fail:
            raise ConnectionError("Ollama caído")
        return SimpleNamespace(message=SimpleNamespace(content=self.replies.pop(0)))


TEST_PERSONA = Persona(
    id="prueba",
    name="Prueba",
    prompt="Eres un personaje de prueba.",
    lines={"error": ["ERROR DE PRUEBA"], "vision_error": ["VISION"], "empty_reply": ["VACIO"]},
)


def make_service(tmp_path, client, **ai_overrides):
    config = {"ai": {"model": "test-model", "temperature": 0.3, **ai_overrides}}
    memory = MemorySystem(tmp_path / "memory.json")
    return AIService(config=config, client=client, memory=memory, persona=TEST_PERSONA)


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
    memory_path = tmp_path / "memory.json"
    marin = load_persona("marin")
    service = AIService(
        config={"ai": {}},
        client=FakeClient(fail=True),
        memory=MemorySystem(memory_path),
        persona=marin,
    )
    assert run(service.generate_response(1, 1, "hola"))[0] in marin.lines["error"]
