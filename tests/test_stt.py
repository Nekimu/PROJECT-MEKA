"""Voz a texto (T-008): motores intercambiables, respaldo y decodificación con FFmpeg."""

import shutil
import subprocess

import pytest

from ai.stt import STTService
from ai.stt.base import SAMPLE_RATE, decode_audio


class FakeEngine:
    def __init__(self, name, text=None, error=None, installed=True):
        self.name = name
        self.text = text
        self.error = error
        self.installed = installed
        self.calls = 0
        self.loaded = False

    def check_health(self):
        return self.installed

    def transcribe(self, audio_path, language):
        self.calls += 1
        self.loaded = True
        if self.error:
            raise self.error
        return self.text

    def unload(self):
        was, self.loaded = self.loaded, False
        return was


def service(*engines, **stt):
    config = {"stt": {"engine": engines[0].name, "fallback_engine": engines[-1].name, **stt}}
    return STTService(config, engines={e.name: e for e in engines})


def test_primary_engine_is_used(tmp_path):
    fast, slow = FakeEngine("faster-whisper", "hola"), FakeEngine("whisper", "otro")
    assert service(fast, slow).transcribe(tmp_path / "a.ogg") == "hola"
    assert slow.calls == 0


@pytest.mark.parametrize(
    "primary",
    [
        FakeEngine("faster-whisper", error=RuntimeError("modelo corrupto")),
        FakeEngine("faster-whisper", installed=False),  # No instalado
    ],
)
def test_fallback_engine_takes_over(tmp_path, primary):
    slow = FakeEngine("whisper", "desde el respaldo")
    assert service(primary, slow).transcribe(tmp_path / "a.ogg") == "desde el respaldo"


def test_nothing_works_returns_none(tmp_path):
    a = FakeEngine("faster-whisper", error=RuntimeError("x"))
    b = FakeEngine("whisper", installed=False)
    assert service(a, b).transcribe(tmp_path / "a.ogg") is None


def test_models_are_released_after_use(tmp_path):
    fast = FakeEngine("faster-whisper", "hola")
    stt = service(fast, FakeEngine("whisper"))
    stt.transcribe(tmp_path / "a.ogg")
    stt.release()
    assert fast.loaded is False
    kept = service(
        FakeEngine("faster-whisper", "hola"), FakeEngine("whisper"), unload_after_use=False
    )
    kept.transcribe(tmp_path / "a.ogg")
    kept.release()
    assert kept.engines["faster-whisper"].loaded is True


def test_default_engines_from_config():
    stt = STTService({"stt": {}})
    assert list(stt.engines) == ["faster-whisper", "whisper"]
    assert STTService({"stt": {"engine": "whisper", "fallback_engine": ""}}).engines.keys() == {
        "whisper"
    }


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requiere FFmpeg")
def test_decode_audio_with_ffmpeg(tmp_path):
    audio = tmp_path / "tono.ogg"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-c:a", "libopus", str(audio)],
        check=True,
    )  # fmt: skip
    samples = decode_audio(audio)
    assert samples.dtype.name == "float32"
    assert abs(len(samples) - SAMPLE_RATE) < SAMPLE_RATE * 0.05  # ~1 s a 16 kHz
    assert 0.1 < abs(samples).max() <= 1.0
