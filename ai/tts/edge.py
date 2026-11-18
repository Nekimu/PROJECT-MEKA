"""Edge-TTS: voces neuronales de Microsoft (en la nube, ligero). Motor por defecto."""

import importlib.util
from pathlib import Path

from ai.tts.base import new_output_path
from core.logger import setup_logger

logger = setup_logger("TTS_Service")


class EdgeEngine:
    name = "edge-tts"

    def __init__(self, settings: dict):
        # La voz la define el personaje activo (persona.yml) y tiene prioridad sobre config.yml
        self.voice = settings.get("voice", "es-MX-DaliaNeural")
        self.rate = settings.get("rate", "+0%")
        self.pitch = settings.get("pitch", "+0Hz")

    def check_health(self) -> bool:
        if importlib.util.find_spec("edge_tts") is None:
            logger.critical("Librería edge-tts faltante")
            return False
        return True

    async def synthesize(self, text: str, output_dir: Path) -> Path | None:
        output_path = new_output_path(output_dir, "meka", ".mp3")
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
            await communicate.save(str(output_path))
            logger.info(f"Audio generado con Edge-TTS: {output_path.name}")
            return output_path
        except Exception as e:
            logger.error(f"Error en Edge-TTS: {e}")
            output_path.unlink(missing_ok=True)
            return None

    def release(self):
        pass

    def unload(self):
        pass
