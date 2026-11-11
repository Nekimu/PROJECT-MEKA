"""faster-whisper (CTranslate2): mismo modelo Whisper, menos RAM y sin PyTorch. Motor por defecto.

En CPU usa cuantización int8: unas 3 veces menos memoria que openai-whisper con el mismo
resultado (medido en este proyecto con el modelo base).
"""

import gc
import importlib.util
from pathlib import Path

from ai.stt.base import decode_audio
from core.logger import setup_logger

logger = setup_logger("STT_Service")


class FasterWhisperEngine:
    name = "faster-whisper"

    def __init__(self, settings: dict):
        self.model_size = settings.get("model_size", "base")
        self.device = settings.get("device", "cpu")
        self.compute_type = settings.get("compute_type", "int8")
        self.beam_size = int(settings.get("beam_size", 5))
        self.vad = bool(settings.get("vad", True))  # Salta los silencios: más rápido
        self.model = None

    def check_health(self) -> bool:
        if importlib.util.find_spec("faster_whisper") is None:
            logger.critical("Falta faster-whisper (pip install -r requirements.txt)")
            return False
        return True

    def _load(self):
        if self.model is None:
            from faster_whisper import WhisperModel

            logger.info(f"Cargando faster-whisper '{self.model_size}' ({self.compute_type})...")
            self.model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        return self.model

    def transcribe(self, audio_path: Path, language: str) -> str | None:
        segments, _ = self._load().transcribe(
            decode_audio(audio_path),
            language=language,
            beam_size=self.beam_size,
            vad_filter=self.vad,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text or None

    def unload(self) -> bool:
        if self.model is None:
            return False
        self.model = None
        gc.collect()
        return True
