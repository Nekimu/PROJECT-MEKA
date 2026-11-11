"""Piper: voz local por línea de comandos (privacidad total, sin internet)."""

import asyncio
import shutil
from pathlib import Path

from ai.tts.base import new_output_path
from core.config import resolve_path
from core.logger import setup_logger

logger = setup_logger("TTS_Service")


class PiperEngine:
    name = "piper"

    def __init__(self, settings: dict):
        piper = settings.get("piper") or {}
        self.path = piper.get("path", "piper")
        model_path = piper.get("model_path")
        self.model_path = str(resolve_path(model_path)) if model_path else ""
        self.length_scale = piper.get("length_scale", 1.0)
        self.noise_scale = piper.get("noise_scale", 0.667)
        self.noise_w = piper.get("noise_w", 0.8)

    def check_health(self) -> bool:
        if shutil.which(self.path) is None and not Path(self.path).exists():
            logger.critical(f"No se encontró el ejecutable de Piper en {self.path}")
            return False
        if not self.model_path or not Path(self.model_path).is_file():
            logger.critical(f"No se encontró el modelo de Piper en {self.model_path}")
            return False
        return True

    async def synthesize(self, text: str, output_dir: Path) -> Path | None:
        output_path = new_output_path(output_dir, "meka", ".wav")
        command = [
            self.path,
            "--model", self.model_path,
            "--output_file", str(output_path),
            "--length_scale", str(self.length_scale),
            "--noise_scale", str(self.noise_scale),
            "--noise_w", str(self.noise_w),
        ]  # fmt: skip
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate(input=text.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error en Piper: {e}")
            return None

        if process.returncode != 0:
            logger.error(f"Error en Piper: {stderr.decode(errors='ignore')}")
            output_path.unlink(missing_ok=True)
            return None
        return output_path

    def release(self):
        pass

    def unload(self):
        pass
