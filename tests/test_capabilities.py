"""Enrutamiento por capacidades (T-053): el objetivo es fijo, la ruta depende del cerebro."""

import asyncio
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from ai.multimodal import VOICE_NOTE
from ai.providers import ProviderError
from ai.providers.base import build_provider
from ai.routing import CapabilityError, Router
from ai.service import AIService
from core.memory import MemoryStore
from core.persona import load_persona
from tests.fakes import FakeProvider, FakeSTT
from tests.test_providers import claude_with, gemini_with
from tests.test_server import make_client, make_engine

PERSONA = load_persona("dva")
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requiere FFmpeg")


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------- capacidades declaradas


def test_default_and_declared_capabilities():
    assert build_provider("ollama", {}).capabilities == {"text", "vision"}
    declared = {"ai": {"providers": {"ollama": {"capabilities": ["audio"]}}}}
    assert build_provider("ollama", declared).capabilities == {"text", "audio"}  # text siempre
    with pytest.raises(ProviderError):
        build_provider("ollama", {"ai": {"providers": {"ollama": {"capabilities": ["telepatía"]}}}})


def test_router_only_offers_capable_brains():
    providers = {
        "claude": FakeProvider("claude", capabilities=("text", "vision", "pdf")),
        "gemini": FakeProvider("gemini", capabilities=("text", "vision", "audio", "pdf")),
        "ollama": FakeProvider("ollama", local=True),
    }
    router = Router({"provider": "claude", "fallback_provider": "gemini"}, providers)
    assert router.order("chat") == ["claude", "gemini"]
    assert router.order("chat", need="audio") == ["gemini"]  # Claude no oye
    assert router.can("chat", "audio")
    assert not router.can("chat", "audio", local_only=True)  # Gemini está en la nube
    with pytest.raises(CapabilityError):
        router.order("chat", need="audio", private=True)  # Ollama (local) no oye


# ---------------------------------------------------------------------- notas de voz


def service(tmp_path, providers, **ai):
    return AIService(
        {"ai": ai},
        memory=MemoryStore(tmp_path / "meka.db"),
        persona=PERSONA,
        providers=providers,
    )


def test_audio_to_the_cloud_only_if_allowed(tmp_path):
    gemini = FakeProvider("gemini", "¡te oí!", capabilities=("text", "audio"))
    providers = {"gemini": gemini, "ollama": FakeProvider("ollama", local=True)}
    assert not service(tmp_path, providers, provider="gemini").hears_natively()
    allowed = service(
        tmp_path / "b", providers, provider="gemini", privacy={"audio_to_cloud": True}
    )
    assert allowed.hears_natively()
    assert not allowed.hears_natively(private=True)  # Lo privado, nunca a la nube


def test_native_voice_note(tmp_path):
    local = FakeProvider("ollama", "¡Claro, te recuerdo la factura!", local=True,
                         capabilities=("text", "audio"))  # fmt: skip
    ai = service(tmp_path, {"ollama": local}, provider="ollama")
    note = tmp_path / "nota.wav"
    note.write_bytes(b"RIFF")
    answer = run(ai.answer_audio("s", "u", note))
    assert answer.ok and answer.messages == ["¡Claro, te recuerdo la factura!"]
    sent = local.calls[0]["messages"][-1]
    assert sent == {"role": "user", "content": VOICE_NOTE, "audio": [str(note)]}
    assert ai.history.get("s")[0]["content"] == "[Te envié una nota de voz]"


def test_native_voice_failure_returns_none(tmp_path):
    broken = FakeProvider("ollama", error=ProviderError("se colgó"), local=True,
                          capabilities=("text", "audio"))  # fmt: skip
    ai = service(tmp_path, {"ollama": broken}, provider="ollama")
    assert run(ai.answer_audio("s", "u", tmp_path / "x.wav")) is None  # → transcribir


@pytest.fixture
def voice_note(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("requiere FFmpeg")
    path = tmp_path / "nota.ogg"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=0.5",
         "-c:a", "libopus", str(path)],
        check=True,
    )  # fmt: skip
    return path


@needs_ffmpeg
def test_engine_skips_transcription_when_the_brain_hears(tmp_path, voice_note):
    engine = make_engine(tmp_path)
    engine.stt = FakeSTT("no debería usarse")
    engine.ai.providers["ollama"] = FakeProvider(
        "ollama", "Te escuché perfecto", local=True, capabilities=("text", "audio")
    )
    transcription, replies = run(engine.voice("s", "u", voice_note, audio=False))
    assert transcription is None and replies[0].text == "Te escuché perfecto"
    assert engine.stt.released == 0  # Ni se cargó Whisper


@needs_ffmpeg
def test_engine_falls_back_to_transcription(tmp_path, voice_note):
    engine = make_engine(tmp_path, "Respuesta tras transcribir")
    engine.stt = FakeSTT("hola desde la voz")
    # El cerebro por defecto (Ollama) no oye: se transcribe como siempre
    transcription, replies = run(engine.voice("s", "u", voice_note, audio=False))
    assert transcription == "hola desde la voz" and replies[0].text == "Respuesta tras transcribir"

    engine.stt_mode = "always"  # Aunque el cerebro oyera, transcribir siempre
    engine.ai.providers["ollama"] = FakeProvider(
        "ollama", "con transcripción", local=True, capabilities=("text", "audio")
    )
    assert run(engine.voice("s", "u", voice_note, audio=False))[0] == "hola desde la voz"


def test_api_voice_without_transcription(tmp_path, voice_note):
    engine = make_engine(tmp_path)
    engine.ai.providers["ollama"] = FakeProvider(
        "ollama", "Respondo a tu audio", local=True, capabilities=("text", "audio")
    )
    with make_client(engine) as client:
        body = client.post(
            "/v1/voice",
            data={"session": "s", "user": "u", "audio": "false"},
            files={"file": ("nota.ogg", voice_note.read_bytes(), "audio/ogg")},
        ).json()
    assert body["transcription"] is None and body["replies"][0]["text"] == "Respondo a tu audio"


# ---------------------------------------------------------------------- PDF


def test_pdf_goes_whole_when_the_brain_reads_it(tmp_path):
    reader = FakeProvider("ollama", "El total es 200 €", local=True,
                          capabilities=("text", "pdf"))  # fmt: skip
    ai = service(tmp_path, {"ollama": reader}, provider="ollama")
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    answer = run(ai.answer_pdf("s", "u", pdf, "¿Cuánto es?"))
    assert answer.messages == ["El total es 200 €"] and answer.private  # Documentos: privados
    assert reader.calls[0]["messages"][-1]["documents"] == [str(pdf)]


def test_pdf_falls_back_to_text_extraction(tmp_path):
    ai = service(tmp_path, {"ollama": FakeProvider("ollama", local=True)}, provider="ollama")
    assert run(ai.answer_pdf("s", "u", tmp_path / "f.pdf", "resume")) is None


# ---------------------------------------------------------------------- adaptadores


def test_gemini_receives_audio_and_pdf(tmp_path):
    provider, models = gemini_with(SimpleNamespace(text="ok", prompt_feedback=None))
    audio, pdf = tmp_path / "nota.wav", tmp_path / "doc.pdf"
    audio.write_bytes(b"RIFF")
    pdf.write_bytes(b"%PDF")
    run(
        provider.chat("s", [{"role": "user", "content": "x", "audio": [audio], "documents": [pdf]}])
    )
    parts = models.calls[0]["contents"][0].parts
    assert [p.inline_data.mime_type for p in parts[:2]] == ["audio/wav", "application/pdf"]


def test_claude_receives_pdf(tmp_path):
    provider, sent = claude_with(
        {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
    )
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")
    run(provider.chat("s", [{"role": "user", "content": "resume", "documents": [pdf]}]))
    document, text = sent["body"]["messages"][0]["content"]
    assert document["type"] == "document" and document["source"]["media_type"] == "application/pdf"
    assert text == {"type": "text", "text": "resume"}
