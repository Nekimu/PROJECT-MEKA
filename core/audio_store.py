"""Audios generados que esperan a que un canal los descargue (GET /v1/audio/{id})."""

import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class _Audio:
    path: Path
    created: float


class AudioStore:
    """Cada audio se entrega una sola vez; los que nadie pide caducan tras `ttl` segundos."""

    def __init__(self, ttl: float = 300):
        self.ttl = ttl
        self._audio: dict[str, _Audio] = {}

    def __len__(self) -> int:
        return len(self._audio)

    def store(self, path: Path | None) -> str | None:
        self.purge()
        if path is None:
            return None
        audio_id = uuid.uuid4().hex
        self._audio[audio_id] = _Audio(Path(path), time.monotonic())
        return audio_id

    def take(self, audio_id: str) -> Path | None:
        """El canal lo descarga y el núcleo lo olvida (el servidor borra el archivo al enviarlo)."""
        audio = self._audio.pop(audio_id, None)
        return audio.path if audio and audio.path.is_file() else None

    def drop(self, audio_id: str):
        audio = self._audio.pop(audio_id, None)
        if audio:
            audio.path.unlink(missing_ok=True)

    def purge(self):
        """Borra los audios que ningún canal pidió a tiempo (`server.audio_ttl_seconds`)."""
        limit = time.monotonic() - self.ttl
        for audio_id, audio in list(self._audio.items()):
            if audio.created < limit:
                self.drop(audio_id)

    def clear(self):
        for audio_id in list(self._audio):
            self.drop(audio_id)
