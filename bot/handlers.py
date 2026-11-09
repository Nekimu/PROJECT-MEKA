import asyncio
import gc
import random
import uuid
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ReactionEmoji
from telegram.ext import ContextTypes

from ai.prompts import build_document_prompt
from ai.service import ai_service
from ai.stt import stt_service
from ai.text_utils import ParsedMessage, chunk_text, parse_message
from ai.tts import tts_service
from core.config import resolve_path, settings
from core.documents import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, extract_text
from core.logger import setup_logger
from core.memory import memory_system
from core.persona import persona

logger = setup_logger("Bot_Handlers")

# Carpetas temporales ignoradas por git (NUNCA en docs/, que es pública)
TEMP_AUDIO_DIR = resolve_path("temp_audio")
TEMP_MEDIA_DIR = resolve_path("temp_media")
# Límite de descarga de la Bot API de Telegram para get_file
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


# Lock global para evitar que múltiples procesos de IA/TTS/STT saturen la RAM simultáneamente
processing_lock = asyncio.Lock()


def _media_list(key: str) -> list[str]:
    """Stickers/GIFs configurados en `media` (config.yml). Vacío = no se envían."""
    return [item for item in (settings.get("media", {}).get(key) or []) if item]


def _safe_remove(path: Path | None):
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"No se pudo eliminar el archivo temporal {path.name}: {e}")


# ---------------------------------------------------------------------- comandos


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del comando /start"""
    user = update.effective_user
    await update.effective_message.reply_text(persona.line("greet", user=user.first_name))


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reset: olvida el contexto reciente de la conversación (no los recuerdos)."""
    ai_service.reset_conversation(update.effective_chat.id)
    await update.effective_message.reply_text(persona.line("reset"))


async def memories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/recuerdos: muestra los hechos guardados del usuario."""
    facts = memory_system.get_facts(update.effective_user.id)
    if not facts:
        text = persona.line("memories_empty")
    else:
        text = persona.line("memories_header") + "\n\n" + "\n".join(f"• {fact}" for fact in facts)
    for chunk in chunk_text(text):
        await update.effective_message.reply_text(chunk)


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/olvidar: borra los recuerdos persistentes del usuario."""
    removed = memory_system.clear(update.effective_user.id)
    text = persona.line("forget_done", count=removed) if removed else persona.line("forget_none")
    await update.effective_message.reply_text(text)


# ---------------------------------------------------------------------- texto y voz


async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de texto - Soporta mensajes múltiples"""
    async with processing_lock:
        await _respond(update, context, update.effective_message.text)


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de voz con mayor delay y creatividad"""
    await update.effective_message.reply_text(persona.line("voice_ack"))
    # Delay artificial más largo para simular que está "escuchando" y "procesando"
    await asyncio.sleep(random.uniform(2.5, 4.0))

    # STT y LLM dentro del mismo lock: Whisper nunca coincide en RAM con Ollama/Qwen
    async with processing_lock:
        transcription = await _transcribe_voice(update, context)
        if not transcription:
            await update.effective_message.reply_text(persona.line("voice_fail"))
            return
        await _respond(update, context, transcription)


async def _transcribe_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TEMP_AUDIO_DIR / f"voice_{uuid.uuid4().hex}.ogg"
    try:
        voice = await update.effective_message.voice.get_file()
        await voice.download_to_drive(file_path)
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.RECORD_VOICE
        )
        return await asyncio.to_thread(stt_service.transcribe, file_path)
    except Exception as e:
        logger.error(f"Error procesando voz: {e}")
        return None
    finally:
        _safe_remove(file_path)
        # Liberar RAM del STT antes de pasar al LLM
        stt_service.release()
        gc.collect()


async def _respond(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Genera la respuesta y la envía (texto, voz y media). Requiere tener `processing_lock`."""
    bot_messages = await ai_service.generate_response(
        update.effective_chat.id, update.effective_user.id, text
    )
    await _deliver(update, context, [parse_message(m) for m in bot_messages], allow_audio=True)


# ---------------------------------------------------------------------- envío


async def _deliver(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    replies: list[ParsedMessage],
    *,
    allow_audio: bool,
):
    """Envía las respuestas con gestión estricta de RAM y limpieza garantizada de audios."""
    chat_id = update.effective_chat.id
    audio_paths: dict[int, Path] = {}
    try:
        # Primero generamos todo el audio para después enviar de forma fluida
        if allow_audio:
            for index, reply in enumerate(replies):
                if reply.wants_audio and reply.text:
                    await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
                    audio_path = await tts_service.generate_audio(reply.text)
                    if audio_path:
                        audio_paths[index] = audio_path

        for index, reply in enumerate(replies):
            await _send_reply(update, context, reply, audio_paths.get(index))
            await asyncio.sleep(random.uniform(0.8, 1.5))
    finally:
        for audio_path in audio_paths.values():
            _safe_remove(audio_path)
        # Al finalizar el bloque de mensajes liberamos los modelos que estén configurados así
        tts_service.release()
        gc.collect()


async def _send_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    reply: ParsedMessage,
    audio_path: Path | None,
):
    message = update.effective_message
    chat_id = update.effective_chat.id

    if audio_path:
        # Acción de "Recording voice" con un delay proporcional al texto grabado
        await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
        await asyncio.sleep(min(len(reply.text) * 0.1, 5.0) + random.uniform(1.0, 2.0))
        with audio_path.open("rb") as voice_file:
            await message.reply_voice(voice=voice_file)
    elif reply.text:
        # Acción de "Typing" con tiempo de escritura proporcional al mensaje
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        await asyncio.sleep(min(len(reply.text) * 0.05 + random.uniform(1.5, 3.0), 6.0))
        for chunk in chunk_text(reply.text):
            await message.reply_text(chunk)

    # Enviar media adicional
    stickers = _media_list("stickers")
    if reply.wants_sticker and stickers:
        await asyncio.sleep(random.uniform(0.5, 1.0))
        try:
            await message.reply_sticker(sticker=random.choice(stickers))
        except Exception as e:
            logger.warning(f"No se pudo enviar el sticker: {e}")

    gifs = _media_list("gifs")
    if reply.wants_gif and gifs:
        await asyncio.sleep(random.uniform(0.5, 1.0))
        try:
            await message.reply_animation(animation=random.choice(gifs))
        except Exception as e:
            logger.warning(f"No se pudo enviar el GIF: {e}")


# ---------------------------------------------------------------------- multimedia


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para imágenes enviadas por el usuario."""
    await _process_file(update, context, kind="image", ext=".jpg")


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para documentos (soporta imágenes y archivos de texto/docs)."""
    file_name = update.effective_message.document.file_name or ""
    ext = Path(file_name).suffix.lower()

    if ext in IMAGE_EXTENSIONS:
        await _process_file(update, context, kind="image", ext=ext)
    elif ext in DOCUMENT_EXTENSIONS:
        await _process_file(update, context, kind="document", ext=ext)
    else:
        await update.effective_message.reply_text(persona.line("unsupported_file"))


async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde a stickers y registra su file_id para poder añadirlo a `media.stickers`."""
    sticker = update.effective_message.sticker
    logger.info(f"Sticker recibido. file_id para config.yml -> media.stickers: {sticker.file_id}")
    stickers = _media_list("stickers")
    if stickers:
        try:
            await update.effective_message.reply_sticker(sticker=random.choice(stickers))
            return
        except Exception as e:
            logger.warning(f"No se pudo enviar el sticker: {e}")
    await update.effective_message.reply_text(persona.line("sticker_reply"))


async def _process_file(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str, ext: str):
    """Procesa contenido multimedia (imágenes/docs) con el modelo multimodal."""
    message = update.effective_message

    # 1. Reaccionar con un corazón inmediatamente (notificar que se recibió)
    try:
        await message.set_reaction(ReactionEmoji.RED_HEART)
    except Exception as e:
        logger.warning(f"No se pudo poner la reacción: {e}")

    attachment = message.photo[-1] if message.photo else message.document
    if attachment.file_size and attachment.file_size > MAX_DOWNLOAD_BYTES:
        await message.reply_text(persona.line("file_too_big"))
        return

    request = message.caption or persona.line(
        "analyze_document" if kind == "document" else "analyze_image"
    )

    TEMP_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TEMP_MEDIA_DIR / f"{uuid.uuid4().hex}{ext}"
    try:
        tg_file = await attachment.get_file()
        await tg_file.download_to_drive(file_path)
        logger.info(f"Archivo descargado en: {file_path.name}")

        async with processing_lock:
            # Simular que está procesando (sin mensaje intrusivo)
            await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
            if kind == "image":
                bot_messages = await ai_service.generate_multimodal_response(
                    update.effective_chat.id, request, file_path
                )
            else:
                max_chars = settings.get("documents", {}).get("max_chars", 4000)
                extracted = await asyncio.to_thread(extract_text, file_path, max_chars)
                prompt = build_document_prompt(
                    message.document.file_name, extracted.text, request, extracted.truncated
                )
                bot_messages = await ai_service.generate_response(
                    update.effective_chat.id, update.effective_user.id, prompt, use_memory=False
                )
            replies = [parse_message(m, remove_roleplay=False) for m in bot_messages]
            await _deliver(update, context, replies, allow_audio=False)
    except Exception as e:
        logger.error(f"Error procesando multimedia: {e}")
        await message.reply_text(persona.line("media_error"))
    finally:
        # Eliminar el archivo temporal del usuario tras procesarlo
        _safe_remove(file_path)
        gc.collect()


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
