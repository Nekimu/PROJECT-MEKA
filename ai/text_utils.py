"""Utilidades puras de texto: etiquetas multimedia, limpieza y división de respuestas."""

import re
from dataclasses import dataclass

MESSAGE_DELIMITER = "---"
TAG_PATTERN = re.compile(r"\[(STICKER|GIF|AUDIO)\]", re.IGNORECASE)
# Descripciones de rol como "(se sonroja)" o "*sonríe*"
ROLEPLAY_PATTERN = re.compile(r"\([^()\n]*\)|\*[^*\n]*\*")
# Emojis y símbolos que el TTS no debe leer (se conserva la puntuación expresiva)
NON_SPEECH_PATTERN = re.compile(r"[^\w\s.,!¡?¿:;\-\"']")


@dataclass(frozen=True)
class ParsedMessage:
    """Un mensaje del modelo ya separado en texto limpio y peticiones multimedia."""

    text: str
    wants_audio: bool = False
    wants_sticker: bool = False
    wants_gif: bool = False


def strip_tags(text: str) -> str:
    return TAG_PATTERN.sub("", text)


def strip_roleplay(text: str) -> str:
    return ROLEPLAY_PATTERN.sub("", text)


def _tidy(text: str) -> str:
    """Colapsa espacios repetidos sin perder los saltos de línea."""
    lines = (re.sub(r"[ \t]{2,}", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line).strip()


def parse_message(raw: str) -> ParsedMessage:
    """Detecta [AUDIO]/[STICKER]/[GIF] y devuelve el texto listo para enviarse al chat."""
    tags = {tag.upper() for tag in TAG_PATTERN.findall(raw)}
    return ParsedMessage(
        text=_tidy(strip_roleplay(strip_tags(raw))),
        wants_audio="AUDIO" in tags,
        wants_sticker="STICKER" in tags,
        wants_gif="GIF" in tags,
    )


def clean_for_speech(text: str) -> str:
    """Texto apto para TTS: sin etiquetas, acotaciones, emojis ni espacios sobrantes."""
    text = strip_roleplay(strip_tags(text))
    text = NON_SPEECH_PATTERN.sub("", text)
    return " ".join(text.split())


def split_into_messages(raw_text: str, long_message: int = 100) -> list[str]:
    """
    Divide la respuesta del modelo en "burbujas" de chat: primero por el delimitador
    `---`; si no lo usó y el texto es largo, por saltos de línea y, como último
    recurso, por oraciones.
    """
    messages = [part.strip() for part in raw_text.split(MESSAGE_DELIMITER) if part.strip()]
    if len(messages) == 1 and len(raw_text) > long_message:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if len(lines) > 1:
            return lines
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_text) if s.strip()]
    return messages


def split_paragraphs(raw_text: str) -> list[str]:
    """Divide en párrafos (doble salto de línea); útil para análisis de imágenes."""
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    return paragraphs or ([raw_text.strip()] if raw_text.strip() else [])
