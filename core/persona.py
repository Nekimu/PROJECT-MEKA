"""Paquetes de personaje: identidad de MEKA independiente del proveedor de IA.

Cada personaje vive en `personas/<id>/`:
- `persona.md`: la personalidad (prompt base), en texto plano.
- `persona.yml`: nombre, inspiración, voz y frases fijas del bot.

El personaje activo se elige con `persona:` en config.yml o con la variable de
entorno `MEKA_PERSONA`, sin tocar código.
"""

import os
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.config import BASE_DIR, settings
from core.logger import setup_logger

logger = setup_logger("Persona")

PERSONAS_DIR = BASE_DIR / "personas"
DEFAULT_PERSONA = "dva"

# Frases que el bot necesita de todo personaje (ver personas/*/persona.yml)
REQUIRED_LINES = frozenset({
    "greet", "reset", "memories_empty", "memories_header", "forget_done", "forget_none",
    "voice_ack", "voice_fail", "media_error", "unsupported_file", "file_too_big",
    "sticker_reply", "error", "vision_error", "empty_reply", "analyze_document", "analyze_image",
})  # fmt: skip
VOICE_KEYS = frozenset({"voice", "rate", "pitch"})


class PersonaError(ValueError):
    """El paquete de personaje no existe o está incompleto."""


class _KeepMissing(dict):
    """Deja intactos los marcadores sin valor ({user} sin usuario no rompe la frase)."""

    def __missing__(self, key):
        return "{" + key + "}"


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    prompt: str
    lines: dict[str, list[str]]
    inspiration: str = ""
    description: str = ""
    avatar: str | None = None
    voice: dict[str, str] = field(default_factory=dict)

    def line(self, key: str, **values) -> str:
        """Una frase al azar del tipo `key`, con sus marcadores rellenados."""
        template = random.choice(self.lines[key])
        return template.format_map(_KeepMissing(name=self.name, **values))


def available_personas(root: Path = PERSONAS_DIR) -> list[str]:
    return (
        sorted(p.name for p in root.iterdir() if (p / "persona.yml").is_file())
        if root.is_dir()
        else []
    )


def load_persona(persona_id: str, root: Path = PERSONAS_DIR) -> Persona:
    folder = root / persona_id
    meta_path, prompt_path = folder / "persona.yml", folder / "persona.md"
    if not meta_path.is_file() or not prompt_path.is_file():
        options = ", ".join(available_personas(root)) or "ninguno"
        raise PersonaError(f"No existe el personaje '{persona_id}'. Disponibles: {options}")

    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise PersonaError(f"{prompt_path} está vacío")
    if not meta.get("name"):
        raise PersonaError(f"{meta_path} no define 'name'")

    lines = {key: [str(v) for v in value] if isinstance(value, list) else [str(value)]
             for key, value in (meta.get("lines") or {}).items()}  # fmt: skip
    missing = sorted(key for key in REQUIRED_LINES if not lines.get(key))
    if missing:
        raise PersonaError(f"{meta_path}: faltan frases {missing}")

    voice = {k: str(v) for k, v in (meta.get("voice") or {}).items() if k in VOICE_KEYS}
    return Persona(
        id=persona_id,
        name=str(meta["name"]),
        prompt=prompt,
        lines=lines,
        inspiration=str(meta.get("inspiration", "")),
        description=str(meta.get("description", "")),
        avatar=meta.get("avatar"),
        voice=voice,
    )


def active_persona_id(config: dict | None = None) -> str:
    config = settings if config is None else config
    return (os.getenv("MEKA_PERSONA") or config.get("persona") or DEFAULT_PERSONA).strip()


def load_active_persona(config: dict | None = None) -> Persona:
    persona_id = active_persona_id(config)
    try:
        persona = load_persona(persona_id)
    except PersonaError as e:
        if persona_id == DEFAULT_PERSONA:
            raise
        logger.error(f"{e}. Se usa '{DEFAULT_PERSONA}'.")
        persona = load_persona(DEFAULT_PERSONA)
    logger.info(f"Personaje activo: {persona.name} ({persona.id})")
    return persona


# Instancia global
persona = load_active_persona()
