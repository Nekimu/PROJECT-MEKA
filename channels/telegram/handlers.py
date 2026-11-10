"""Manejadores de Telegram. No cargan modelos: todo pasa por MEKA Core (CoreClient)."""

import asyncio
import io
import random
from dataclasses import dataclass, field
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ReactionEmoji
from telegram.ext import ContextTypes

from ai.text_utils import chunk_text
from channels.client import CoreClient
from core.documents import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS
from core.logger import setup_logger
from core.persona import Persona

logger = setup_logger("Telegram")

# Límite de descarga de la Bot API de Telegram para get_file (lo impone Telegram)
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


@dataclass
class TelegramSettings:
    typing_delay: float = 1.0  # 0 = sin pausas de "escribiendo..."
    stickers: list[str] = field(default_factory=list)
    gifs: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, telegram_config: dict) -> "TelegramSettings":
        return cls(
            typing_delay=float(telegram_config.get("typing_delay", 1.0)),
            stickers=[s for s in telegram_config.get("stickers") or [] if s],
            gifs=[g for g in telegram_config.get("gifs") or [] if g],
        )


def _core(context: ContextTypes.DEFAULT_TYPE) -> CoreClient:
    return context.application.bot_data["core"]


def _persona(context: ContextTypes.DEFAULT_TYPE) -> Persona:
    return context.application.bot_data["persona"]


def _settings(context: ContextTypes.DEFAULT_TYPE) -> TelegramSettings:
    return context.application.bot_data["settings"]


def _ids(update: Update) -> tuple[str, str]:
    """Sesión (chat) y usuario (memoria) en MEKA Core. El usuario es el ID de Telegram."""
    return f"telegram:{update.effective_chat.id}", str(update.effective_user.id)


async def _pause(context: ContextTypes.DEFAULT_TYPE, low: float, high: float):
    scale = _settings(context).typing_delay
    if scale > 0:
        await asyncio.sleep(random.uniform(low, high) * scale)


# ---------------------------------------------------------------------- comandos


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start"""
    user = update.effective_user
    await update.effective_message.reply_text(_persona(context).line("greet", user=user.first_name))


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reset: olvida el contexto reciente de la conversación (no los recuerdos)."""
    session, _ = _ids(update)
    await _core(context).reset(session)
    await update.effective_message.reply_text(_persona(context).line("reset"))


async def memories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/recuerdos: muestra los hechos guardados del usuario."""
    persona = _persona(context)
    facts = await _core(context).memories(_ids(update)[1])
    if not facts:
        text = persona.line("memories_empty")
    else:
        text = persona.line("memories_header") + "\n\n" + "\n".join(f"• {fact}" for fact in facts)
    for chunk in chunk_text(text):
        await update.effective_message.reply_text(chunk)


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/olvidar: borra los recuerdos persistentes del usuario."""
    persona = _persona(context)
    removed = await _core(context).forget(_ids(update)[1])
    text = persona.line("forget_done", count=removed) if removed else persona.line("forget_none")
    await update.effective_message.reply_text(text)


# ---------------------------------------------------------------------- texto y voz


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensajes de texto."""
    session, user = _ids(update)
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        replies = await _core(context).chat(session, user, update.effective_message.text)
    except Exception as e:
        logger.error(f"MEKA Core no pudo responder: {e}")
        await update.effective_message.reply_text(_persona(context).line("error"))
        return
    await _deliver(update, context, replies)


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notas de voz: se envían a MEKA Core, que transcribe y responde."""
    persona = _persona(context)
    message = update.effective_message
    await message.reply_text(persona.line("voice_ack"))
    await _pause(context, 2.5, 4.0)  # Simula que está "escuchando"

    session, user = _ids(update)
    try:
        voice = await message.voice.get_file()
        audio = bytes(await voice.download_as_bytearray())
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.RECORD_VOICE)
        transcription, replies = await _core(context).voice(session, user, audio)
    except Exception as e:
        logger.error(f"Error procesando voz: {e}")
        transcription, replies = None, []

    if not transcription:
        await message.reply_text(persona.line("voice_fail"))
        return
    await _deliver(update, context, replies)


# ---------------------------------------------------------------------- envío


async def _deliver(update: Update, context: ContextTypes.DEFAULT_TYPE, replies: list[dict]):
    for reply in replies:
        await _send_reply(update, context, reply)
        await _pause(context, 0.8, 1.5)


async def _send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, reply: dict):
    message = update.effective_message
    chat_id = update.effective_chat.id
    settings = _settings(context)
    text = reply.get("text") or ""

    audio = None
    if reply.get("audio"):
        try:
            audio = await _core(context).audio(reply["audio"])
        except Exception as e:
            logger.warning(f"No se pudo descargar el audio de MEKA Core: {e}")

    if audio:
        # "Grabando audio..." con una pausa proporcional al texto
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        if settings.typing_delay > 0:
            await asyncio.sleep(
                (min(len(text) * 0.1, 5.0) + random.uniform(1.0, 2.0)) * settings.typing_delay
            )
        await message.reply_voice(voice=io.BytesIO(audio))
    elif text:
        # "Escribiendo..." con una pausa proporcional al mensaje
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        if settings.typing_delay > 0:
            await asyncio.sleep(
                min(len(text) * 0.05 + random.uniform(1.5, 3.0), 6.0) * settings.typing_delay
            )
        for chunk in chunk_text(text):
            await message.reply_text(chunk)

    if reply.get("sticker") and settings.stickers:
        await _pause(context, 0.5, 1.0)
        try:
            await message.reply_sticker(sticker=random.choice(settings.stickers))
        except Exception as e:
            logger.warning(f"No se pudo enviar el sticker: {e}")

    if reply.get("gif") and settings.gifs:
        await _pause(context, 0.5, 1.0)
        try:
            await message.reply_animation(animation=random.choice(settings.gifs))
        except Exception as e:
            logger.warning(f"No se pudo enviar el GIF: {e}")


# ---------------------------------------------------------------------- multimedia


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Imágenes enviadas como foto."""
    await _process_file(update, context, file_name="foto.jpg")


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Documentos (o imágenes enviadas como archivo)."""
    file_name = update.effective_message.document.file_name or ""
    ext = Path(file_name).suffix.lower()
    if ext in IMAGE_EXTENSIONS or ext in DOCUMENT_EXTENSIONS:
        await _process_file(update, context, file_name=file_name)
    else:
        await update.effective_message.reply_text(_persona(context).line("unsupported_file"))


async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde a stickers y registra su file_id para poder añadirlo a `telegram.stickers`."""
    sticker = update.effective_message.sticker
    logger.info(
        f"Sticker recibido. file_id para config.yml -> telegram.stickers: {sticker.file_id}"
    )
    stickers = _settings(context).stickers
    if stickers:
        try:
            await update.effective_message.reply_sticker(sticker=random.choice(stickers))
            return
        except Exception as e:
            logger.warning(f"No se pudo enviar el sticker: {e}")
    await update.effective_message.reply_text(_persona(context).line("sticker_reply"))


async def _process_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str):
    """Descarga el archivo en memoria y lo envía a MEKA Core para analizarlo."""
    message = update.effective_message
    persona = _persona(context)

    # Reaccionar con un corazón al instante para confirmar que se recibió
    try:
        await message.set_reaction(ReactionEmoji.RED_HEART)
    except Exception as e:
        logger.warning(f"No se pudo poner la reacción: {e}")

    attachment = message.photo[-1] if message.photo else message.document
    if attachment.file_size and attachment.file_size > MAX_DOWNLOAD_BYTES:
        await message.reply_text(persona.line("file_too_big"))
        return

    session, user = _ids(update)
    try:
        tg_file = await attachment.get_file()
        content = bytes(await tg_file.download_as_bytearray())
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
        replies = await _core(context).analyze_file(
            session, user, content, file_name, message.caption
        )
    except Exception as e:
        logger.error(f"Error procesando multimedia: {e}")
        await message.reply_text(persona.line("media_error"))
        return
    await _deliver(update, context, replies)


# ---------------------------------------------------------------------- errores y acceso


async def unauthorized_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ignora a usuarios fuera de ALLOWED_USER_IDS, dejando constancia de su ID."""
    user = update.effective_user
    if user:
        logger.warning(
            f"Mensaje ignorado de usuario no autorizado: id={user.id} (@{user.username})"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Loguear errores no controlados (con traza, sin volcar el contenido del mensaje)."""
    logger.error("Error no controlado procesando un update", exc_info=context.error)
