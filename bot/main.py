from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from core.config import settings
from core.logger import setup_logger
from bot.handlers import start, chat_handler, voice_handler, photo_handler, document_handler, error_handler
from ai.service import ai_service
from ai.tts import tts_service
from ai.stt import stt_service

logger = setup_logger("Bot_Main")

def run_bot():
    """Inicia el bot de Telegram."""
    token = settings.get("telegram", {}).get("token")
    
    placeholder_tokens = {"tu_token_aqui", "tu_token_aqui_sin_comillas"}
    if not token or token in placeholder_tokens:
        logger.critical("Error: Token de Telegram no configurado en .env")
        return

    application = ApplicationBuilder().token(token).build()

    # Añadir manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.Document, document_handler))
    
    # Manejador de errores
    application.add_error_handler(error_handler)

    # Verificación de herramientas al inicio (No bloqueante, solo advertencias)
    logger.info("Verificando integridad de herramientas...")
    
    if not ai_service.check_health():
        logger.error("ADVERTENCIA: Ollama no respondió al Health Check. Se intentará conectar durante la ejecución.")

    if not tts_service.check_health():
        logger.error("ADVERTENCIA: El motor TTS reportó problemas. Es posible que el audio no funcione.")

    if not stt_service.check_health():
        logger.error("ADVERTENCIA: STT (Whisper) no está listo. Los audios de voz podrían fallar.")
        
    logger.info("Diagnóstico completado. Iniciando Marin Kitagawa...")
    logger.info("¡Marin Kitagawa está lista y esperando mensajes! 💖")
    
    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Cerrando el bot por petición del usuario...")
    finally:
        # Asegurar que todos los modelos se descarguen al cerrar el programa
        logger.info("Liberando recursos de IA y TTS...")
        
        # Intentar resetear torch._dynamo para evitar el error en atexit
        try:
            import torch
            if hasattr(torch, "_dynamo"):
                torch._dynamo.reset()
        except Exception:
            pass

        ai_service.unload_model()
        stt_service.unload_model()
        if tts_service.engine == "qwen-tts":
            tts_service.unload_qwen()
            
        # Limpieza forzada de memoria
        import gc
        gc.collect()
        
        logger.info("¡Marin se ha ido a descansar! 💖")

if __name__ == "__main__":
    run_bot()
