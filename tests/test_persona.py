"""Paquetes de personaje (personas/): validación, selección y frases."""

import pytest

from ai.tts import TTSService
from core.persona import (
    DEFAULT_PERSONA,
    REQUIRED_LINES,
    PersonaError,
    active_persona_id,
    available_personas,
    load_active_persona,
    load_persona,
)

PACKS = available_personas()


def test_expected_packs_exist():
    assert {"dva", "marin", "yotsuba"} <= set(PACKS)
    assert DEFAULT_PERSONA in PACKS


@pytest.mark.parametrize("persona_id", PACKS)
def test_every_pack_is_complete(persona_id):
    persona = load_persona(persona_id)
    assert persona.name and len(persona.prompt) > 200
    assert set(persona.lines) >= REQUIRED_LINES
    for key in REQUIRED_LINES:
        assert persona.line(key, user="Neki", count=3)  # todas las frases se formatean
    assert "{user}" not in persona.line("greet", user="Neki")
    assert set(persona.voice) <= {"voice", "rate", "pitch"}


@pytest.mark.parametrize("persona_id", PACKS)
def test_prompts_do_not_claim_to_be_the_official_character(persona_id):
    assert "oficial" in load_persona(persona_id).prompt.lower()


def test_unknown_persona_lists_available(tmp_path):
    with pytest.raises(PersonaError, match=r"Disponibles: .*dva"):
        load_persona("no-existe")


def test_incomplete_pack_is_rejected(tmp_path):
    folder = tmp_path / "rota"
    folder.mkdir()
    (folder / "persona.md").write_text("Personalidad", encoding="utf-8")
    (folder / "persona.yml").write_text("name: Rota\nlines:\n  greet: ['hola']\n", encoding="utf-8")
    with pytest.raises(PersonaError, match="faltan frases"):
        load_persona("rota", root=tmp_path)


def test_missing_placeholders_are_kept(tmp_path):
    persona = load_persona("dva")
    template_line = next(line for line in persona.lines["greet"] if "{user}" in line)
    assert "{user}" in template_line
    assert persona.line("memories_empty")  # sin marcadores no falla


def test_selection_from_config_and_env(monkeypatch):
    monkeypatch.delenv("MEKA_PERSONA", raising=False)
    assert active_persona_id({"persona": "marin"}) == "marin"
    assert active_persona_id({}) == DEFAULT_PERSONA
    monkeypatch.setenv("MEKA_PERSONA", "yotsuba")
    assert active_persona_id({"persona": "marin"}) == "yotsuba"
    assert load_active_persona({}).name == "Yotsuba"


def test_unknown_configured_persona_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("MEKA_PERSONA", raising=False)
    assert load_active_persona({"persona": "no-existe"}).id == DEFAULT_PERSONA


def test_persona_voice_overrides_tts_config(tmp_path):
    config = {
        "tts": {"enabled": True, "voice": "es-ES-ElviraNeural", "rate": "+0%", "pitch": "+0Hz"}
    }
    tts = TTSService(config, voice=load_persona("yotsuba").voice)
    assert (tts.voice, tts.rate, tts.pitch) == ("es-MX-DaliaNeural", "+8%", "+6Hz")
    assert TTSService(config, voice={}).voice == "es-ES-ElviraNeural"
