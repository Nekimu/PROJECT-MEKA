"""Comprueba el registro de manejadores con objetos de Telegram construidos en memoria."""

import datetime

import pytest
from telegram import Chat, Document, Message, Sticker, Update, User

from bot.handlers import chat_handler, document_handler, sticker_handler, unauthorized_handler
from bot.main import build_application

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
