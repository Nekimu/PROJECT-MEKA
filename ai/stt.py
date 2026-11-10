import gc
import importlib.util
import shutil
import sys

from core.config import settings
from core.logger import setup_logger

logger = setup_logger("STT_Service")


class STTService:
    def __init__(self, config: dict | None = None):
        """
        Inicializa el servicio de STT.
        El modelo se cargará la primera vez que se necesite (Lazy Loading).
        Modelos disponibles: tiny, base, small, medium, large, turbo
        """
        stt_config = (settings if config is None else config).get("stt", {})
        self.model_size = stt_config.get("model_size", "base")
        self.language = stt_config.get("language", "es")
        self.unload_after_use = stt_config.get("unload_after_use", True)
        self.model = None
        logger.info(f"Servicio STT inicializado (Lazy Loading: '{self.model_size}')")

    def _load_model(self) -> bool:
        """Carga el modelo de Whisper bajo demanda (el import de torch también es diferido)."""
        if self.model:
            return True
        try:
            import whisper

            logger.info(f"Cargando modelo Whisper '{self.model_size}' en memoria...")
            self.model = whisper.load_model(self.model_size)
            logger.info("Modelo Whisper cargado correctamente.")
            return True
        except Exception as e:
            logger.critical(f"Error fatal cargando Whisper: {e}")
            self.model = None
            return False

    def check_health(self) -> bool:
        """Verifica que Whisper y FFmpeg estén disponibles (sin cargar el modelo)."""
        healthy = True
        if importlib.util.find_spec("whisper") is None:
            logger.critical("Falta el paquete openai-whisper (pip install -r requirements.txt)")
            healthy = False
        if shutil.which("ffmpeg") is None:
            logger.critical("FFmpeg no está en el PATH: Whisper no podrá leer las notas de voz")
            healthy = False
        return healthy

    def transcribe(self, audio_path) -> str | None:
        """Transcribe un archivo de audio a texto. Devuelve None si falla."""
        if not self._load_model():
            return None

        try:
            import torch

            logger.info(f"Transcribiendo audio: {audio_path}")
            result = self.model.transcribe(
                str(audio_path),
                language=self.language,
                fp16=torch.cuda.is_available(),  # En CPU FP16 no está soportado
            )
            text = result.get("text", "").strip()
            logger.info(f"Transcripción completada ({len(text)} caracteres)")
            return text or None
        except Exception as e:
            logger.error(f"Error en la transcripción: {e}")
            return None

    def release(self):
        """Libera el modelo tras usarlo si así está configurado (`stt.unload_after_use`)."""
        if self.unload_after_use:
            self.unload_model()

    def unload_model(self) -> bool:
        """Libera el modelo de Whisper de la RAM."""
        if not self.model:
            return False
        logger.info("Descargando Whisper de la memoria...")
        self.model = None
        gc.collect()
        torch = sys.modules.get("torch")
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
        return True
