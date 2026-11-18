"""Servicio de voz: elige el motor, prueba el de respaldo y entrega OGG/Opus."""

import shutil

from ai.text_utils import clean_for_speech
from ai.tts.audio import to_ogg_opus
from ai.tts.base import TTSEngine
from ai.tts.edge import EdgeEngine
from ai.tts.piper import PiperEngine
from ai.tts.qwen import QwenEngine
from core.config import resolve_path, settings
from core.logger import setup_logger

logger = setup_logger("TTS_Service")

# Motores disponibles. Uno nuevo: un módulo en ai/tts/ que cumpla TTSEngine y una línea aquí.
ENGINES: dict[str, type[TTSEngine]] = {
    EdgeEngine.name: EdgeEngine,
    QwenEngine.name: QwenEngine,
    PiperEngine.name: PiperEngine,
}


class TTSService:
    def __init__(self, config: dict | None = None, voice: dict | None = None):
        config = settings if config is None else config
        # La voz del personaje activo tiene prioridad sobre config.yml
        tts_config = {**config.get("tts", {}), **(voice or {})}
        self.enabled = tts_config.get("enabled", False)
        self.engine = tts_config.get("engine", "edge-tts")
        self.fallback_engine = tts_config.get("fallback_engine")
        # Telegram solo muestra como nota de voz OGG/Opus (y MP3/M4A); el WAV llega como archivo
        self.convert_to_ogg = tts_config.get("convert_to_ogg", True)
        temp_dir = resolve_path(config.get("paths", {}).get("temp_dir", "temp"))
        self.output_dir = temp_dir / "audio"

        # Solo se crean los motores que se van a usar (los pesados cargan su modelo al hablar)
        self.engines: dict[str, TTSEngine] = {
            name: ENGINES[name](tts_config) for name in self._order() if name in ENGINES
        }
        if self.enabled:
            logger.info(f"TTS Service cargado con el motor: {self.engine}")

    def _order(self) -> list[str]:
        """Motor principal y, si es otro, el de respaldo."""
        names = [self.engine]
        if self.fallback_engine and self.fallback_engine != self.engine:
            names.append(self.fallback_engine)
        return names

    def check_health(self) -> bool:
        """Verifica el motor principal (o el de respaldo) sin cargar modelos."""
        if not self.enabled:
            return True
        healthy = False
        for index, name in enumerate(self._order()):
            engine = self.engines.get(name)
            if engine is None:
                logger.critical(f"Motor TTS desconocido: {name!r}. Opciones: {', '.join(ENGINES)}")
            elif engine.check_health():
                healthy = True
                break
            if index + 1 < len(self._order()):
                logger.warning(f"Se usará el motor de respaldo '{self._order()[index + 1]}'")
        if self.convert_to_ogg and shutil.which("ffmpeg") is None:
            logger.warning("FFmpeg no está en el PATH: los audios no se convertirán a OGG/Opus")
        return healthy

    async def generate_audio(self, text: str):
        """Genera un archivo de audio (OGG/Opus si hay FFmpeg) a partir de un texto."""
        if not self.enabled:
            return None
        clean_text = clean_for_speech(text)
        if not clean_text:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = None
        for name in self._order():
            engine = self.engines.get(name)
            if engine is None:
                logger.error(f"Motor TTS desconocido: {name!r}")
                continue
            output_path = await engine.synthesize(clean_text, self.output_dir)
            if output_path is not None:
                break
            logger.warning(f"Fallo en '{name}'; se prueba el siguiente motor si lo hay")

        if output_path and self.convert_to_ogg:
            output_path = await to_ogg_opus(output_path)
        return output_path

    def release(self):
        """Tras cada tanda de audios (p. ej. Qwen se descarga para liberar RAM)."""
        for engine in self.engines.values():
            engine.release()

    def unload(self):
        """Al apagar MEKA Core."""
        for engine in self.engines.values():
            engine.unload()
