"""Contrato común de los motores de voz a texto (STT) y decodificación de audio.

Cada motor vive en su propio módulo y solo sabe transcribir. La elección del motor y el
respaldo entre ellos son del servicio (ai/stt/__init__.py).
"""

import shutil
import subprocess
from pathlib import Path
from typing import Protocol

SAMPLE_RATE = 16_000  # Lo que esperan los modelos Whisper


class STTEngine(Protocol):
    name: str

    def check_health(self) -> bool:
        """¿Está listo? Sin cargar modelos."""
        ...

    def transcribe(self, audio_path: Path, language: str) -> str | None:
        """Texto del audio, o None si falla (el servicio prueba el de respaldo)."""
        ...

    def unload(self) -> bool:
        """Libera el modelo de la RAM. True si había uno cargado."""
        ...


def to_wav(src: str | Path, dst: str | Path) -> Path:
    """Convierte cualquier audio (p. ej. OGG/Opus de Telegram) a WAV mono de 16 kHz: el formato
    que aceptan todos los cerebros con audio nativo (Gemini, llama.cpp)."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg no está en el PATH")
    subprocess.run(
        [ffmpeg, "-nostdin", "-y", "-loglevel", "error", "-i", str(src),
         "-ac", "1", "-ar", str(SAMPLE_RATE), str(dst)],
        capture_output=True, check=True,
    )  # fmt: skip
    return Path(dst)


def decode_audio(path: str | Path):
    """Audio → muestras float32 mono a 16 kHz, con FFmpeg (ya es requisito del proyecto).

    Así faster-whisper no depende de PyAV, cuyas versiones cambian la API.
    """
    import numpy as np

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("FFmpeg no está en el PATH")
    raw = subprocess.run(
        [ffmpeg, "-nostdin", "-loglevel", "error", "-i", str(path),
         "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"],
        capture_output=True, check=True,
    ).stdout  # fmt: skip
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
