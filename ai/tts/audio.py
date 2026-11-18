"""Conversión de audio con FFmpeg."""

import asyncio
import shutil
from pathlib import Path

from core.logger import setup_logger

logger = setup_logger("TTS_Service")


async def to_ogg_opus(path: Path) -> Path:
    """Convierte a OGG/Opus mono (lo que Telegram muestra como nota de voz).

    Si no hay FFmpeg o la conversión falla, devuelve el archivo original.
    """
    if path.suffix == ".ogg":
        return path
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return path

    ogg_path = path.with_suffix(".ogg")
    try:
        process = await asyncio.create_subprocess_exec(
            ffmpeg, "-y", "-loglevel", "error", "-i", str(path),
            "-ac", "1", "-c:a", "libopus", "-b:a", "48k", str(ogg_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )  # fmt: skip
        _, stderr = await process.communicate()
    except Exception as e:
        logger.warning(f"No se pudo convertir el audio a OGG/Opus: {e}")
        return path

    if process.returncode != 0:
        logger.warning(f"FFmpeg no pudo convertir el audio: {stderr.decode(errors='ignore')}")
        ogg_path.unlink(missing_ok=True)
        return path
    path.unlink(missing_ok=True)
    return ogg_path
