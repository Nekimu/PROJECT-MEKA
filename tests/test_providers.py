"""Adaptadores de cerebro con los SDK reales y la red simulada (no se gasta nada)."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from ai.providers import ProviderError, RefusalError, build_provider
from ai.providers.ollama import OllamaProvider
from tests.fakes import FakeClient


def run(coro):
    return asyncio.run(coro)


def test_unknown_provider_is_rejected():
    with pytest.raises(ProviderError):
        build_provider("skynet", {})


def test_ollama_receives_system_prompt_and_images(tmp_path):
    image = tmp_path / "foto.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    client = FakeClient("Bonita")
    provider = OllamaProvider({"model": "gemma3:4b"}, client=client)
    text = run(
        provider.chat(
            "SISTEMA", [{"role": "user", "content": "mira", "images": [image]}], vision=True
        )
    )
    call = client.calls[0]
    assert text == "Bonita" and call["model"] == "gemma3:4b"
    assert call["messages"][0] == {"role": "system", "content": "SISTEMA"}
    assert call["messages"][1]["images"] == [str(image)]
    assert call["options"]["temperature"] == 0.6  # opciones de visión


def test_ollama_errors_become_provider_errors():
    with pytest.raises(ProviderError):
        run(
            OllamaProvider({}, client=FakeClient(fail=True)).chat(
                "s", [{"role": "user", "content": "hola"}]
            )
        )


# ---------------------------------------------------------------------- Claude


def claude_with(reply: dict):
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")
    from ai.providers.claude import ClaudeProvider

    sent = {}

    def handler(request):
        sent["headers"] = dict(request.headers)
        sent["body"] = json.loads(request.content)
        body = {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
            **reply,
        }
        return httpx2.Response(200, json=body)

    client = anthropic.AsyncAnthropic(
        api_key="test",
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    return ClaudeProvider({}, client=client), sent


def test_claude_request_shape(tmp_path):
    provider, sent = claude_with(
        {"content": [{"type": "text", "text": "¡GG!"}], "stop_reason": "end_turn"}
    )
    image = tmp_path / "foto.png"
    image.write_bytes(b"\x89PNG")
    messages = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "¡hey!"},
        {"role": "user", "content": "mira", "images": [image]},
    ]
    assert run(provider.chat("Eres MEKA", messages)) == "¡GG!"

    body = sent["body"]
    assert body["model"] == "claude-opus-5-5" and body["system"] == "Eres MEKA"
    assert body["output_config"] == {"effort": "low"}
    assert body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in sent["headers"]["anthropic-beta"]
    assert "temperature" not in body  # Los modelos actuales no la aceptan
    image_block, text_block = body["messages"][2]["content"]
    assert image_block["source"]["media_type"] == "image/png"
    assert text_block == {"type": "text", "text": "mira"}


def test_claude_refusal_is_reported():
    provider, _ = claude_with({"content": [], "stop_reason": "refusal"})
    with pytest.raises(RefusalError):
        run(provider.chat("s", [{"role": "user", "content": "hola"}]))


# ---------------------------------------------------------------------- Gemini


class FakeGeminiModels:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def gemini_with(response):
    pytest.importorskip("google.genai")
    from ai.providers.gemini import GeminiProvider

    models = FakeGeminiModels(response)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return GeminiProvider({"temperature": 0.5}, client=client), models


def test_gemini_request_shape(tmp_path):
    provider, models = gemini_with(SimpleNamespace(text="Hola", prompt_feedback=None))
    image = tmp_path / "foto.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    messages = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "¡hey!"},
        {"role": "user", "content": "mira", "images": [image]},
    ]
    assert run(provider.chat("Eres MEKA", messages)) == "Hola"

    call = models.calls[0]
    assert call["model"] == "gemini-flash-latest"
    assert call["config"].system_instruction == "Eres MEKA" and call["config"].temperature == 0.5
    roles = [content.role for content in call["contents"]]
    assert roles == ["user", "model", "user"]
    image_part, text_part = call["contents"][2].parts
    assert image_part.inline_data.mime_type == "image/jpeg" and text_part.text == "mira"


def test_gemini_block_is_reported():
    feedback = SimpleNamespace(block_reason="SAFETY")
    provider, _ = gemini_with(SimpleNamespace(text=None, prompt_feedback=feedback))
    with pytest.raises(RefusalError):
        run(provider.chat("s", [{"role": "user", "content": "hola"}]))
