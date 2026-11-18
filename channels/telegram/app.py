"""Canal de Telegram: un cliente más de MEKA Core."""

import asyncio

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from channels.client import CoreClient
from channels.telegram.alerts import forward_alerts, task_button, tasks_command
from channels.telegram.handlers import (
    TelegramSettings,
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
from core.config import is_valid_token
from core.logger import setup_logger
from core.persona import Persona

logger = setup_logger("Telegram")


def bot_commands(persona_name: str) -> list[BotCommand]:
    return [
        BotCommand("start", f"Saludar a {persona_name}"),
        BotCommand("reset", "Empezar la conversación de cero"),
        BotCommand("recuerdos", f"Ver lo que {persona_name} recuerda de ti"),
        BotCommand("olvidar", "Borrar tus recuerdos guardados"),
        BotCommand("tareas", "Ver tus tareas pendientes"),
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
    persona: Persona | None = application.bot_data.get("persona")
    if persona is None:
        return
    try:
        await application.bot.set_my_commands(bot_commands(persona.name))
    except Exception as e:
        logger.warning(f"No se pudo registrar el menú de comandos: {e}")


def build_application(
    token: str,
    config: dict,
    *,
    core: CoreClient | None = None,
    persona: Persona | None = None,
) -> Application:
    """Crea la aplicación de Telegram con todos los manejadores registrados."""
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
    application.bot_data.update(
        core=core, persona=persona, settings=TelegramSettings.from_config(telegram_config)
    )

    # Solo mensajes nuevos: los editados llegan con update.message = None
    allowed = build_access_filter(telegram_config.get("allowed_user_ids"))
    base = filters.UpdateType.MESSAGE & allowed

    application.add_handler(CommandHandler("start", start, filters=base))
    application.add_handler(CommandHandler("reset", reset_command, filters=base))
    application.add_handler(CommandHandler("recuerdos", memories_command, filters=base))
    application.add_handler(CommandHandler("olvidar", forget_command, filters=base))
    application.add_handler(CommandHandler("tareas", tasks_command, filters=base))
    # Botones de los avisos («Hecho», «Posponer»). Los filtros no aplican a los botones:
    # task_button comprueba ALLOWED_USER_IDS por su cuenta
    application.bot_data["allowed_ids"] = {
        int(i) for i in telegram_config.get("allowed_user_ids") or []
    }
    application.add_handler(CallbackQueryHandler(task_button, pattern=r"^task:"))
    application.add_handler(MessageHandler(base & filters.TEXT & ~filters.COMMAND, chat_handler))
    application.add_handler(MessageHandler(base & filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(base & filters.PHOTO, photo_handler))
    # filters.Document es un espacio de nombres; el filtro real es filters.Document.ALL
    application.add_handler(MessageHandler(base & filters.Document.ALL, document_handler))
    application.add_handler(MessageHandler(base & filters.Sticker.ALL, sticker_handler))
    application.add_handler(
        MessageHandler(filters.UpdateType.MESSAGE & ~allowed, unauthorized_handler)
    )
    application.add_error_handler(error_handler)
    return application


def _start_alerts(application: Application, core: CoreClient, telegram_config: dict):
    """Los avisos de Hanna al dueño del bot (el primer ID de ALLOWED_USER_IDS)."""
    owners = telegram_config.get("allowed_user_ids") or []
    if not owners:
        logger.warning("Sin ALLOWED_USER_IDS no hay dueño: los avisos no llegarán a Telegram")
        return None
    if not telegram_config.get("alerts", True):
        return None
    return asyncio.create_task(forward_alerts(application.bot, core, int(owners[0])))


async def run_telegram(config: dict, *, retry: float = 10.0):
    """Conecta con MEKA Core y atiende Telegram hasta que se cancele la tarea. Si algo falla
    (sin red al arrancar, el núcleo tardó, Telegram caído), se reintenta en vez de morir."""
    telegram_config = config.get("telegram", {})
    token = telegram_config.get("token")
    if not is_valid_token(token):
        logger.critical("Token de Telegram no configurado: añade TELEGRAM_TOKEN en .env")
        return
    delay = retry
    while True:
        started = asyncio.get_running_loop().time()
        try:
            await _serve_telegram(config, token, telegram_config)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                f"Telegram se detuvo ({type(e).__name__}: {e}); reintento en {delay:.0f} s"
            )
        if asyncio.get_running_loop().time() - started > 300:
            delay = retry  # Funcionó un buen rato: el fallo es nuevo
        await asyncio.sleep(delay)
        delay = min(delay * 2, 300)


async def _serve_telegram(config: dict, token: str, telegram_config: dict):
    core = CoreClient.from_config(config)
    try:
        persona = await core.wait_ready()
        application = build_application(token, config, core=core, persona=persona)
        async with application:
            await application.start()
            await application.updater.start_polling(
                allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
                drop_pending_updates=telegram_config.get("drop_pending_updates", False),
            )
            logger.info(f"¡{persona.name} está lista y esperando mensajes en Telegram!")
            alerts = _start_alerts(application, core, telegram_config)
            try:
                await asyncio.Event().wait()  # Hasta que se apague el proceso
            finally:
                if alerts is not None:
                    alerts.cancel()
                await application.updater.stop()
                await application.stop()
    finally:
        await core.close()
