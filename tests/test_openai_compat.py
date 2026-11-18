"""Adaptador compatible con OpenAI (T-054): llama.cpp, LM Studio, vLLM, Ollama /v1."""

import asyncio
import base64
import json

import httpx
import pytest

from ai.providers import ProviderError
from ai.providers.base import build_provider
from ai.providers.openai_compat import OpenAICompatProvider


def run(coro):
    return asyncio.run(coro)


def provider_with(handler, **settings):
    sent = []

    def capture(request):
        sent.append(json.loads(request.content) if request.content else None)
        return handler(request)

    client = httpx.AsyncClient(
        base_url="http://127.0.0.1:8080", transport=httpx.MockTransport(capture)
    )
    return OpenAICompatProvider({"model": "gemma-4-e4b", **settings}, client=client), sent


def ok(text="¡Hola!", usage=None):
    body = {"choices": [{"message": {"role": "assistant", "content": text}}]}
    if usage:
        body["usage"] = usage
    return lambda request: httpx.Response(200, json=body)


def test_text_request_and_usage():
    provider, sent = provider_with(ok("Respuesta", {"prompt_tokens": 12, "completion_tokens": 3}))
    reply = run(provider.chat("Eres MEKA", [{"role": "user", "content": "hola"}]))
    assert (reply.text, reply.input_tokens, reply.output_tokens) == ("Respuesta", 12, 3)
    assert sent[0]["model"] == "gemma-4-e4b"
    assert sent[0]["messages"] == [
        {"role": "system", "content": "Eres MEKA"},
        {"role": "user", "content": "hola"},
    ]


def test_image_and_audio_parts(tmp_path):
    image, audio = tmp_path / "foto.png", tmp_path / "nota.wav"
    image.write_bytes(b"\x89PNG")
    audio.write_bytes(b"RIFFdata")
    provider, sent = provider_with(ok())
    message = {"role": "user", "content": "escucha", "images": [image], "audio": [audio]}
    run(provider.chat("s", [message]))
    image_part, audio_part, text_part = sent[0]["messages"][1]["content"]
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")
    assert audio_part == {
        "type": "input_audio",
        "input_audio": {"data": base64.b64encode(b"RIFFdata").decode(), "format": "wav"},
    }
    assert text_part == {"type": "text", "text": "escucha"}


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500, text="model not loaded"),
        lambda request: httpx.Response(200, json={"error": "sin choices"}),
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("rechazada")),
    ],
)
def test_errors_become_provider_errors(handler):
    provider, _ = provider_with(handler)
    with pytest.raises(ProviderError):
        run(provider.chat("s", [{"role": "user", "content": "hola"}]))


@pytest.mark.parametrize(
    ("settings", "local"),
    [
        ({"base_url": "http://127.0.0.1:8080"}, True),
        ({"base_url": "http://localhost:1234"}, True),  # LM Studio
        ({"base_url": "http://192.168.1.50:8080"}, False),  # Otra máquina: como nube
        ({"base_url": "https://api.ejemplo.com"}, False),
        ({"base_url": "http://192.168.1.50:8080", "local": True}, True),  # Declarado por ti
    ],
)
def test_only_this_machine_counts_as_local(settings, local):
    assert OpenAICompatProvider(settings).local is local


def test_built_from_config_with_declared_capabilities():
    config = {
        "ai": {
            "providers": {
                "openai_compat": {
                    "base_url": "http://127.0.0.1:8080",
                    "model": "gemma-4-e4b",
                    "capabilities": ["vision", "audio"],
                }
            }
        }
    }
    provider = build_provider("openai_compat", config)
    assert provider.capabilities == {"text", "vision", "audio"}
    assert provider.local and provider.model == "gemma-4-e4b"
    assert build_provider("openai_compat", {}).capabilities == {"text"}  # Prudente por defecto


def test_thinking_switch_reaches_the_template():
    provider, sent = provider_with(ok(), thinking=False)
    run(provider.chat("s", [{"role": "user", "content": "hola"}]))
    assert sent[0]["chat_template_kwargs"] == {"enable_thinking": False}
    provider, sent = provider_with(ok())
    run(provider.chat("s", [{"role": "user", "content": "hola"}]))
    assert "chat_template_kwargs" not in sent[0]  # Sin opinión: no se envía


def test_only_reasoning_is_an_error():
    body = {"choices": [{"message": {"content": "", "reasoning_content": "Thinking..."}}]}
    provider, _ = provider_with(lambda request: httpx.Response(200, json=body))
    with pytest.raises(ProviderError, match="thinking"):
        run(provider.chat("s", [{"role": "user", "content": "hola"}]))
