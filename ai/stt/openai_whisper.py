"""openai-whisper: el motor original (PyTorch). Queda como respaldo de faster-whisper."""

import gc
import importlib.util
import sys
from pathlib import Path

from core.logger import setup_logger

logger = setup_logger("STT_Service")


class OpenAIWhisperEngine:
    name = "whisper"

    def __init__(self, settings: dict):
        self.model_size = settings.get("model_size", "base")
        self.model = None

    def check_health(self) -> bool:
        if importlib.util.find_spec("whisper") is None:
            logger.critical("Falta openai-whisper (pip install -r requirements.txt)")
            return False
        return True

    def _load(self):
        if self.model is None:
            import whisper

            logger.info(f"Cargando Whisper '{self.model_size}' en memoria...")
            self.model = whisper.load_model(self.model_size)
        return self.model

    def transcribe(self, audio_path: Path, language: str) -> str | None:
        import torch

        result = self._load().transcribe(
            str(audio_path),
            language=language,
            fp16=torch.cuda.is_available(),  # En CPU FP16 no está soportado
        )
        return result.get("text", "").strip() or None

    def unload(self) -> bool:
        if self.model is None:
            return False
        self.model = None
        gc.collect()
        torch = sys.modules.get("torch")
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
        return True
