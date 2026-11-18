"""Contrato común de los motores de voz (TTS).

Cada motor vive en su propio módulo y solo sabe convertir texto en un archivo de audio.
El respaldo entre motores, la limpieza del texto y la conversión a OGG son del servicio
(`ai/tts/service.py`), así que añadir un motor nuevo no toca los demás.
"""

import uuid
from pathlib import Path
from typing import Protocol


class TTSEngine(Protocol):
    name: str

    def check_health(self) -> bool:
        """¿Está listo? Sin cargar modelos (solo comprobaciones baratas)."""
        ...

    async def synthesize(self, text: str, output_dir: Path) -> Path | None:
        """Genera el audio en `output_dir`. Devuelve None si falla (el servicio prueba otro)."""
        ...

    def release(self) -> None:
        """Tras cada tanda de audios: libera lo que el motor no deba mantener en RAM."""
        ...

    def unload(self) -> None:
        """Al apagar: libera todo."""
        ...


def new_output_path(output_dir: Path, prefix: str, suffix: str) -> Path:
    return output_dir / f"{prefix}_{uuid.uuid4().hex}{suffix}"
