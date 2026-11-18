"""Voz a texto (STT): un servicio y un módulo por motor (faster-whisper, whisper).

El modelo se carga la primera vez que hace falta y, con `stt.unload_after_use`, se libera
tras cada nota de voz para no ocupar RAM mientras no se usa.
"""

import shutil
from pathlib import Path

from ai.stt.base import STTEngine
from ai.stt.faster import FasterWhisperEngine
from ai.stt.openai_whisper import OpenAIWhisperEngine
from core.config import settings
from core.logger import setup_logger

__all__ = ["ENGINES", "STTService"]

logger = setup_logger("STT_Service")

# Motores disponibles. Uno nuevo: un módulo en ai/stt/ que cumpla STTEngine y una línea aquí.
ENGINES: dict[str, type[STTEngine]] = {
    FasterWhisperEngine.name: FasterWhisperEngine,
    OpenAIWhisperEngine.name: OpenAIWhisperEngine,
}


class STTService:
    def __init__(self, config: dict | None = None, engines: dict[str, STTEngine] | None = None):
        stt = (settings if config is None else config).get("stt", {})
        self.engine = stt.get("engine", "faster-whisper")
        self.fallback_engine = stt.get("fallback_engine", "whisper")
        self.language = stt.get("language", "es")
        self.unload_after_use = stt.get("unload_after_use", True)
        self.engines: dict[str, STTEngine] = engines or {
            name: ENGINES[name](stt) for name in self._order() if name in ENGINES
        }
        logger.info(f"Servicio STT: {' → '.join(self._order())} (carga diferida)")

    def _order(self) -> list[str]:
        names = [self.engine]
        if self.fallback_engine and self.fallback_engine != self.engine:
            names.append(self.fallback_engine)
        return names

    def check_health(self) -> bool:
        """Algún motor disponible y FFmpeg en el PATH (sin cargar modelos)."""
        if shutil.which("ffmpeg") is None:
            logger.critical("FFmpeg no está en el PATH: no se podrán leer las notas de voz")
            return False
        for name in self._order():
            engine = self.engines.get(name)
            if engine is None:
                logger.critical(f"Motor STT desconocido: {name!r}. Opciones: {', '.join(ENGINES)}")
            elif engine.check_health():
                return True
        return False

    def transcribe(self, audio_path) -> str | None:
        """Texto de una nota de voz. Prueba el motor principal y, si falla, el de respaldo."""
        for name in self._order():
            engine = self.engines.get(name)
            if engine is None or not engine.check_health():
                continue
            try:
                text = engine.transcribe(Path(audio_path), self.language)
            except Exception as e:
                logger.error(f"Error en la transcripción con {name}: {e}")
                continue
            logger.info(f"Transcripción con {name}: {len(text or '')} caracteres")
            return text
        return None

    def release(self):
        """Tras cada nota de voz (si `stt.unload_after_use`)."""
        if self.unload_after_use:
            self.unload_model()

    def unload_model(self) -> bool:
        """Libera los modelos cargados. True si había alguno."""
        return any([engine.unload() for engine in self.engines.values()])
