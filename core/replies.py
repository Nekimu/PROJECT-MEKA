"""Respuestas del núcleo, iguales para cualquier canal (Telegram, mascota, MCP, app)."""

from dataclasses import asdict, dataclass

from ai.text_utils import ParsedMessage


class UnsupportedFileError(ValueError):
    """El tipo de archivo no se puede analizar."""


@dataclass
class Reply:
    """Un mensaje de respuesta listo para cualquier canal."""

    text: str
    audio: str | None = None  # Identificador del audio en GET /v1/audio/{id}
    sticker: bool = False
    gif: bool = False
    private: bool = False  # La atendió solo un proveedor local (el canal puede mostrar un 🔒)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_message(
        cls, message: ParsedMessage, audio_id: str | None = None, *, private: bool = False
    ) -> "Reply":
        return cls(
            text=message.text,
            audio=audio_id,
            sticker=message.wants_sticker,
            gif=message.wants_gif,
            private=private,
        )
