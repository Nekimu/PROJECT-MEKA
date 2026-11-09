import contextlib
import gc
import sys

from telegram import BotCommand, Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from ai.service import ai_service
from ai.stt import stt_service
from ai.tts import tts_service
from bot.handlers import (
    chat_handler,
    document_handler,
    error_handler,
    forget_command,
    memories_command,
    photo_handler,
    reset_command,
    start,
    sticker_handler,
    unauthorized_handler,
    voice_handler,
)
from core.config import is_valid_token, settings
from core.logger import configure_logging, setup_logger
from core.persona import persona

logger = setup_logger("Bot_Main")

BOT_COMMANDS = [
    BotCommand("start", f"Saludar a {persona.name}"),
    BotCommand("reset", "Empezar la conversación de cero"),
    BotCommand("recuerdos", f"Ver lo que {persona.name} recuerda de ti"),
    BotCommand("olvidar", "Borrar tus recuerdos guardados"),
]


def build_access_filter(allowed_user_ids) -> filters.BaseFilter:
    """Restringe el bot a los IDs de ALLOWED_USER_IDS. Sin lista, el bot es público."""
    if not allowed_user_ids:
        logger.warning(
            "ALLOWED_USER_IDS está vacío: el bot responderá a CUALQUIER usuario de Telegram. "
            "Añade tu ID en .env para hacerlo privado."
        )
        return filters.ALL
    return filters.User(user_id=allowed_user_ids)


async def _post_init(application: Application):
    try:
        await application.bot.set_my_commands(BOT_COMMANDS)
    except Exception as e:
        logger.warning(f"No se pudo registrar el menú de comandos: {e}")


def build_application(token: str, config: dict | None = None) -> Application:
    """Crea la aplicación de Telegram con todos los manejadores registrados."""
    config = settings if config is None else config
    telegram_config = config.get("telegram", {})
    timeout = telegram_config.get("request_timeout", 30)

    application = (
        ApplicationBuilder()
        .token(token)
        .read_timeout(timeout)
        .write_timeout(timeout)
        .post_init(_post_init)
        .build()
    )

    # Solo mensajes nuevos: los editados llegan con update.message = None
    allowed = build_access_filter(telegram_config.get("allowed_user_ids"))
    base = filters.UpdateType.MESSAGE & allowed

    # Añadir manejadores
    application.add_handler(CommandHandler("start", start, filters=base))
    application.add_handler(CommandHandler("reset", reset_command, filters=base))
    application.add_handler(CommandHandler("recuerdos", memories_command, filters=base))
    application.add_handler(CommandHandler("olvidar", forget_command, filters=base))
    application.add_handler(MessageHandler(base & filters.TEXT & ~filters.COMMAND, chat_handler))
    application.add_handler(MessageHandler(base & filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(base & filters.PHOTO, photo_handler))
    # filters.Document es un espacio de nombres; el filtro real es filters.Document.ALL
    application.add_handler(MessageHandler(base & filters.Document.ALL, document_handler))
    application.add_handler(MessageHandler(base & filters.Sticker.ALL, sticker_handler))
    application.add_handler(
        MessageHandler(filters.UpdateType.MESSAGE & ~allowed, unauthorized_handler)
    )

    # Manejador de errores
    application.add_error_handler(error_handler)
    return application


def _release_resources():
    """Asegura que todos los modelos se descarguen al cerrar el programa."""
    logger.info("Liberando recursos de IA y TTS...")

    # Resetear torch._dynamo (solo si torch llegó a cargarse) para evitar el error en atexit
    torch = sys.modules.get("torch")
    if torch is not None:
        with contextlib.suppress(Exception):
            torch._dynamo.reset()

    ai_service.unload_model()
    stt_service.unload_model()
    tts_service.unload_qwen()
    gc.collect()


def run_bot():
    """Inicia el bot de Telegram."""
    configure_logging(settings.get("app", {}).get("log_level", "INFO"))

    token = settings.get("telegram", {}).get("token")
    if not is_valid_token(token):
        logger.critical("Error: Token de Telegram no configurado en .env")
        return

    application = build_application(token)

    # Verificación de herramientas al inicio (No bloqueante, solo advertencias)
    logger.info("Verificando integridad de herramientas...")

    if not ai_service.check_health():
        logger.error(
            "ADVERTENCIA: Ollama no respondió al Health Check. "
            "Se intentará conectar durante la ejecución."
        )

    if not tts_service.check_health():
        logger.error(
            "ADVERTENCIA: El motor TTS reportó problemas. Es posible que el audio no funcione."
        )

    if not stt_service.check_health():
        logger.error("ADVERTENCIA: STT (Whisper) no está listo. Los audios de voz podrían fallar.")

    logger.info(f"Diagnóstico completado. Personaje: {persona.name} ({persona.id})")
    logger.info(f"¡{persona.name} está lista y esperando mensajes!")

    try:
        application.run_polling(
            allowed_updates=[Update.MESSAGE],
            drop_pending_updates=settings.get("telegram", {}).get("drop_pending_updates", False),
        )
    except KeyboardInterrupt:
        logger.info("Cerrando el bot por petición del usuario...")
    finally:
        _release_resources()
        logger.info(f"{persona.name} se ha ido a descansar.")


if __name__ == "__main__":
    run_bot()
