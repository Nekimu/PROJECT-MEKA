from ai.text_utils import (
    MAX_MESSAGE_CHARS,
    chunk_text,
    clean_for_speech,
    parse_message,
    split_into_messages,
    split_paragraphs,
)


def test_parse_message_can_keep_parentheses_for_analysis():
    """Regresión: el análisis de documentos perdía los datos entre paréntesis."""
    raw = "El total es 200 € (IVA incluido) [AUDIO]"
    assert parse_message(raw, remove_roleplay=False).text == "El total es 200 € (IVA incluido)"
    assert parse_message(raw).text == "El total es 200 €"


def test_chunk_text_respects_telegram_limit():
    """Regresión: Telegram rechaza mensajes de más de 4096 caracteres."""
    facts = "\n".join(f"• recuerdo número {i} con algo de texto" for i in range(400))
    chunks = chunk_text(facts)
    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_MESSAGE_CHARS for chunk in chunks)
    assert "\n".join(chunks) == facts  # se corta por saltos de línea sin perder nada


def test_chunk_text_without_spaces_and_short_text():
    assert [len(c) for c in chunk_text("x" * 9000)] == [4000, 4000, 1000]
    assert chunk_text("hola") == ["hola"]
    assert chunk_text("") == []


def test_parse_message_detects_tags_case_insensitive():
    parsed = parse_message("¡Hola cielo! 💖 [audio] [Sticker]")
    assert parsed.text == "¡Hola cielo! 💖"
    assert parsed.wants_audio and parsed.wants_sticker and not parsed.wants_gif


def test_parse_message_removes_roleplay_and_extra_spaces():
    parsed = parse_message("Hola (se sonroja) amor *sonríe* ✨")
    assert parsed.text == "Hola amor ✨"


def test_parse_message_keeps_line_breaks():
    assert parse_message("Línea 1\nLínea 2").text == "Línea 1\nLínea 2"


def test_parse_message_tag_only():
    parsed = parse_message("[GIF]")
    assert parsed.text == "" and parsed.wants_gif


def test_clean_for_speech_strips_emojis_tags_and_roleplay():
    text = "¡Hola, bb! 😳💖 (nerviosa) ¿Me escuchas? [AUDIO]"
    assert clean_for_speech(text) == "¡Hola, bb! ¿Me escuchas?"


def test_clean_for_speech_keeps_accents():
    assert clean_for_speech("Canción pequeña ñandú") == "Canción pequeña ñandú"


def test_split_by_delimiter():
    assert split_into_messages("Hola --- ¿Qué tal? ---  ") == ["Hola", "¿Qué tal?"]


def test_split_short_message_is_untouched():
    assert split_into_messages("Hola. Adiós.") == ["Hola. Adiós."]


def test_split_long_message_by_lines_then_sentences():
    first = "Primera línea, bastante larga para que el texto completo supere el umbral de cien caracteres."
    by_lines = f"{first}\nSegunda línea."
    assert split_into_messages(by_lines) == [first, "Segunda línea."]
    by_sentences = "Esta es una oración larga para pasar el umbral. " * 3
    assert len(split_into_messages(by_sentences)) == 3


def test_split_paragraphs():
    assert split_paragraphs("A\n\nB\n\n") == ["A", "B"]
    assert split_paragraphs("   ") == []
