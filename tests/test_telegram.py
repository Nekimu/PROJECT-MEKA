"""Canal de Telegram: registro de manejadores con objetos construidos en memoria."""

import datetime

import pytest
from telegram import Chat, Document, Message, Sticker, Update, User

from channels.telegram.app import bot_commands, build_application
from channels.telegram.handlers import (
    TelegramSettings,
    chat_handler,
    document_handler,
    sticker_handler,
    unauthorized_handler,
)

OWNER = User(1, "Owner", False)
STRANGER = User(2, "Stranger", False)
CHAT = Chat(1, Chat.PRIVATE)


def message(user=OWNER, **kwargs):
    return Message(1, datetime.datetime.now(datetime.UTC), CHAT, from_user=user, **kwargs)


def matching_callback(app, update):
    for handler in app.handlers[0]:
        check = handler.check_update(update)
        if check is not None and check is not False:
            return handler.callback
    return None


@pytest.fixture
def private_app():
    return build_application("123456:TEST", {"telegram": {"allowed_user_ids": [OWNER.id]}})


@pytest.fixture
def public_app():
    return build_application("123456:TEST", {"telegram": {}})


def test_document_is_routed_to_document_handler(private_app):
    """Regresión: `filters.Document` (sin .ALL) lanzaba AttributeError en cada update."""
    doc = Document("file-id", "unique-id", file_name="apuntes.pdf")
    update = Update(1, message=message(document=doc))
    assert matching_callback(private_app, update) is document_handler


def test_sticker_is_routed(private_app):
    sticker = Sticker("file-id", "unique-id", 512, 512, False, False, Sticker.REGULAR)
    update = Update(1, message=message(sticker=sticker))
    assert matching_callback(private_app, update) is sticker_handler


def test_text_is_routed_to_chat(private_app):
    assert matching_callback(private_app, Update(1, message=message(text="hola"))) is chat_handler


def test_edited_messages_are_ignored(private_app):
    """Regresión: un mensaje editado llegaba a chat_handler con update.message = None."""
    assert matching_callback(private_app, Update(1, edited_message=message(text="hola"))) is None


def test_strangers_are_rejected_when_whitelist_is_set(private_app):
    update = Update(1, message=message(user=STRANGER, text="hola"))
    assert matching_callback(private_app, update) is unauthorized_handler


def test_public_bot_accepts_anyone(public_app):
    update = Update(1, message=message(user=STRANGER, text="hola"))
    assert matching_callback(public_app, update) is chat_handler


def test_settings_come_from_config():
    settings = TelegramSettings.from_config(
        {"typing_delay": 0, "stickers": ["a", ""], "gifs": None}
    )
    assert settings == TelegramSettings(typing_delay=0.0, stickers=["a"], gifs=[])


def test_commands_use_persona_name():
    assert "Hanna" in bot_commands("Hanna")[0].description


# ---------------------------------------------------------------------- manejadores


class FakeCore:
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    async def chat(self, session, user, text):
        self.calls.append((session, user, text))
        return self.replies

    async def audio(self, audio_id):
        return b"OggS" + audio_id.encode()


class FakeTelegramMessage:
    def __init__(self, text):
        self.text = text
        self.sent = []

    async def reply_text(self, text):
        self.sent.append(("text", text))

    async def reply_voice(self, voice):
        self.sent.append(("voice", voice.read()))

    async def reply_sticker(self, sticker):
        self.sent.append(("sticker", sticker))


def run_handler(handler, text, replies, **settings):
    import asyncio
    from types import SimpleNamespace

    from core.persona import load_persona

    message = FakeTelegramMessage(text)
    core = FakeCore(replies)

    async def send_chat_action(*args, **kwargs):
        pass

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=10),
        effective_user=SimpleNamespace(id=20, first_name="Nekimu"),
        effective_message=message,
    )
    context = SimpleNamespace(
        bot=SimpleNamespace(send_chat_action=send_chat_action),
        application=SimpleNamespace(
            bot_data={
                "core": core,
                "persona": load_persona("dva"),
                "settings": TelegramSettings(typing_delay=0, **settings),
            }
        ),
    )
    asyncio.run(handler(update, context))
    return core, message


def test_chat_handler_goes_through_meka_core():
    replies = [
        {"text": "¡Hola!", "audio": None, "sticker": True, "gif": False},
        {"text": "Te mando un audio", "audio": "abc", "sticker": False, "gif": False},
    ]
    core, message = run_handler(chat_handler, "hola", replies, stickers=["sticker-id"])
    assert core.calls == [("telegram:10", "20", "hola")]
    assert message.sent == [
        ("text", "¡Hola!"),
        ("sticker", "sticker-id"),
        ("voice", b"OggSabc"),
    ]
