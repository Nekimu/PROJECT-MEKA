import asyncio
import shutil
import subprocess

import pytest

from ai.tts import TTSService


def make_tts(tmp_path, **overrides):
    config = {"tts": {"enabled": True, "output_dir": str(tmp_path), **overrides}}
    return TTSService(config)


def test_disabled_returns_none(tmp_path):
    assert asyncio.run(make_tts(tmp_path, enabled=False).generate_audio("hola")) is None


def test_text_without_speech_returns_none(tmp_path):
    assert asyncio.run(make_tts(tmp_path).generate_audio("💖✨ [AUDIO]")) is None


def test_fallback_engine_is_used_when_primary_fails(tmp_path):
    tts = make_tts(tmp_path, engine="qwen-tts", fallback_engine="edge-tts", convert_to_ogg=False)
    used = []

    async def failing(text):
        used.append("qwen-tts")
        return None

    async def working(text):
        used.append(("edge-tts", text))
        path = tmp_path / "audio.mp3"
        path.write_bytes(b"mp3")
        return path

    tts._generate_qwen_tts = failing
    tts._generate_edge_tts = working
    result = asyncio.run(tts.generate_audio("¡Hola! 😳 (nerviosa) [AUDIO]"))
    assert result == tmp_path / "audio.mp3"
    assert used == ["qwen-tts", ("edge-tts", "¡Hola!")]


def test_unknown_engine_fails_health_check(tmp_path):
    assert not make_tts(tmp_path, engine="no-existe").check_health()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requiere FFmpeg")
def test_wav_is_converted_to_ogg_opus(tmp_path):
    wav = tmp_path / "voz.wav"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=0.3", str(wav)],
        check=True,
    )
    tts = make_tts(tmp_path)
    result = asyncio.run(tts._to_ogg_opus(wav))
    assert result.suffix == ".ogg" and result.exists() and not wav.exists()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(result)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert probe.stdout.strip() == "opus"


class FakeQwenModel:
    def __init__(self):
        self.prompt_calls = 0
        self.generate_kwargs = []

    def create_voice_clone_prompt(self, **kwargs):
        self.prompt_calls += 1
        return ["prompt-item"]

    def generate_voice_clone(self, **kwargs):
        self.generate_kwargs.append(kwargs)
        return [[0.0, 0.1, 0.0]], 24000


def test_qwen_voice_prompt_is_computed_once_and_released(tmp_path, monkeypatch):
    pytest.importorskip("soundfile")
    tts = make_tts(
        tmp_path,
        engine="qwen-tts",
        qwen={"ref_audio": "audio/YotsubaAudio.wav", "ref_text": "hola"},
    )
    model = FakeQwenModel()

    def fake_init():
        tts.qwen_model = model
        tts._qwen_voice_prompt = model.create_voice_clone_prompt()
        return True

    monkeypatch.setattr(tts, "_init_qwen", lambda: tts.qwen_model is not None or fake_init())
    tts.convert_to_ogg = False
    for text in ("primera frase", "segunda frase"):
        assert asyncio.run(tts.generate_audio(text)).exists()

    assert model.prompt_calls == 1
    assert all(k["voice_clone_prompt"] == ["prompt-item"] for k in model.generate_kwargs)
    tts.release()
    assert tts.qwen_model is None and tts._qwen_voice_prompt is None
