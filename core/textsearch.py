"""Utilidades de búsqueda: normalización de texto, palabras clave y vectores."""

import math
import re
import unicodedata
from array import array

# Palabras a ignorar en la búsqueda (conectores y disparadores), ya normalizadas sin tildes.
STOPWORDS = {
    "recuerdas", "recuerda", "acuerdas", "sabes", "dijiste", "sobre", "esto", "esta", "este",
    "donde", "cual", "cuales", "como", "cuando", "porque", "para", "algo", "nada", "todo",
    "tengo", "tienes", "mucho", "cosas", "dime", "eres", "estas", "quien",
}  # fmt: skip


def normalize_text(text: str) -> str:
    """Minúsculas, sin tildes y sin signos de puntuación (¿recuérdas? -> recuerdas)."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^\w\s]", " ", text)


def extract_keywords(text: str) -> list[str]:
    return [w for w in normalize_text(text).split() if len(w) > 3 and w not in STOPWORDS]


def pack(vector: list[float]) -> bytes:
    """Vector normalizado en float32: el mismo formato que usa sqlite-vec."""
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return array("f", (x / norm for x in vector)).tobytes()


def unpack(blob: bytes) -> array:
    return array("f", blob)


def stem(word: str) -> str:
    """Quita el plural para buscar por prefijo: juegos -> juego*, canciones -> cancion*."""
    if len(word) > 5 and word.endswith("es"):
        return word[:-2]
    if len(word) > 4 and word.endswith("s"):
        return word[:-1]
    return word
