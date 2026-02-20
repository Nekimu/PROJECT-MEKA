from telegram import Update, ReactionTypeEmoji
from telegram.ext import ContextTypes
import asyncio
import os
import re
from ai.service import ai_service
from core.logger import setup_logger

logger = setup_logger("Bot_Handlers")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador del comando /start"""
    user = update.effective_user
    welcome_message = f"¡Hola {user.first_name}! Soy Marin, tu novia virtual. 💖 ¿Qué quieres hacer hoy? ✨"
    await update.message.reply_text(welcome_message)

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de texto - Soporta mensajes múltiples"""
    user_text = update.message.text
    await process_and_reply(update, context, user_text)

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador de mensajes de voz con mayor delay y creatividad"""
    from ai.stt import stt_service
    import random
    import asyncio
    
    process_messages = [
        "¡Waaa! 😳 ¿Un audio? A ver, a ver... ¡Dámelo que lo escucho ya mismo! 🥰✨",
        "¿Me mandaste un audio, gordi? ¡Ay, qué emoción! Déjame pongo mis audífonos... 💖👉👈",
        "Uy, espera amor, ando un poquito ocupada con un traje... ¡pero tu voz es prioridad! Dame un segundito... 💋🔥",
        "¿Qué me estarás diciendo con esa voz tan linda? Jeje, ¡ya mismo lo oigo! 😉✨",
        "¡Hala! ¡Un mensaje de voz! ¡Qué detalle tan lindo! 😳💖 Espera que lo proceso..."
    ]
    
    await update.message.reply_text(random.choice(process_messages))
    
    # Delay artificial más largo para simular que está "escuchando" y "procesando"
    await asyncio.sleep(random.uniform(2.5, 4.0))
    
    try:
        voice = await update.message.voice.get_file()
        file_path = "temp_voice.ogg"
        await voice.download_to_drive(file_path)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
        transcription = stt_service.transcribe(file_path)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if not transcription or "Error" in transcription:
            await update.message.reply_text("¡Uhh! No pude entender bien lo que dijiste... 😵 ¿Me lo repites por fis?")
            return
            
        # Liberar RAM del STT antes de pasar al LLM
        stt_service.unload_model()
        import gc
        gc.collect()

        # Procesar con el LLM
        await process_and_reply(update, context, transcription)

    except Exception as e:
        logger.error(f"Error procesando voz: {e}")
        await update.message.reply_text("¡Ehh! Pasó algo raro con el audio... lo siento bb 😵")

# Lock global para evitar que múltiples procesos de IA/TTS saturen la RAM simultáneamente
processing_lock = asyncio.Lock()

async def process_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Lógica para enviar mensajes con gestión estricta de RAM (Cola de procesamiento)"""
    import asyncio
    import random
    import gc
    from ai.tts import tts_service
    from ai.service import ai_service

    # Lista de Stickers de Marin Kitagawa
    STICKERS = [
        "CAACAgIAAxkBAAELsyBl0y5S8-6m8S7G8S7G8S7G8S7G", 
        "CAACAgIAAxkBAAELsyJl0y5S8-6m8S7G8S7G8S7G8S7G"
    ]
    
    # GIFs de Marin Kitagawa
    GIFS = [
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3N2c244bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/vA8s37mS5F3F6/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3N2c244bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/3o7TKMGpxPucV5I5Xq/giphy.gif"
    ]

    async with processing_lock:
        bot_messages = ai_service.generate_response(text)
        
        # Una vez generado el texto, la RAM de Ollama se libera (keep_alive: 0)
        gc.collect()

        # Primero generamos todo el contenido (texto y rutas de audio)
        processed_content = []
        for msg in bot_messages:
            # Detectar Tags (Case-insensitive)
            has_sticker = bool(re.search(r'\[STICKER\]', msg, re.IGNORECASE))
            has_gif = bool(re.search(r'\[GIF\]', msg, re.IGNORECASE))
            has_audio = bool(re.search(r'\[AUDIO\]', msg, re.IGNORECASE))
            
            # Limpiar el mensaje de todos los tags
            clean_msg = re.sub(r'\[STICKER\]|\[GIF\]|\[AUDIO\]', '', msg, flags=re.IGNORECASE).strip()
            
            # Limpiar descripciones de rol para el mensaje de TEXTO
            text_for_chat = re.sub(r'\(.*?\)', '', clean_msg)
            text_for_chat = re.sub(r'\*.*?\*', '', text_for_chat).strip()
            
            audio_path = None
            if has_audio and text_for_chat:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
                audio_path = await tts_service.generate_audio(text_for_chat)

            processed_content.append({
                "text": text_for_chat,
                "audio_path": audio_path,
                "has_sticker": has_sticker,
                "has_gif": has_gif
            })

        # Ahora enviamos todo de forma secuencial y fluida
        for item in processed_content:
            if item["audio_path"]:
                # Acción de "Recording voice" con un delay más largo y natural
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
                # El delay depende de la longitud del texto que se grabó
                audio_delay = min(len(item["text"]) * 0.1, 5.0) + random.uniform(1.0, 2.0)
                await asyncio.sleep(audio_delay)
                
                with open(item["audio_path"], 'rb') as voice_file:
                    await update.message.reply_voice(voice=voice_file)
                if os.path.exists(item["audio_path"]):
                    os.remove(item["audio_path"])
            elif item["text"]:
                # Acción de "Typing" con delay prolongado
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                # Simular tiempo de escritura proporcional al mensaje
                writing_time = (len(item["text"]) * 0.05) + random.uniform(1.5, 3.0)
                await asyncio.sleep(min(writing_time, 6.0))
                await update.message.reply_text(item["text"])

            # Enviar media adicional
            if item["has_sticker"]:
                await asyncio.sleep(random.uniform(0.5, 1.0))
                try: await update.message.reply_sticker(sticker=random.choice(STICKERS))
                except Exception: pass
            
            if item["has_gif"]:
                await asyncio.sleep(random.uniform(0.5, 1.0))
                try: await context.bot.send_animation(chat_id=update.effective_chat.id, animation=random.choice(GIFS))
                except Exception: pass
            
            await asyncio.sleep(random.uniform(0.8, 1.5))
        
        # Al finalizar el bloque de mensajes, liberamos recursos SIEMPRE si el motor es Qwen
        if tts_service.engine == "qwen-tts":
            tts_service.unload_qwen()
            
        # Liberar el modelo de Ollama también después de cada interacción
        ai_service.unload_model()
            
        gc.collect()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Loguear y manejar errores críticos en updates."""
    logger.error(f"Update {update} causó error {context.error}")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para imágenes enviadas por el usuario."""
    await process_file_content(update, context, mode="photo")

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para documentos (soporta imágenes y archivos de texto/docs)."""
    file_name = update.message.document.file_name or ""
    ext = os.path.splitext(file_name)[1].lower()
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    document_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt']
    
    if ext in image_extensions:
        await process_file_content(update, context, mode="photo")
    elif ext in document_extensions:
        await process_file_content(update, context, mode="document")
    else:
        await update.message.reply_text("¡Uy! Ese tipo de archivo no sé cómo leerlo todavía... 😅 (Usa fotos, PDF, Word o Excel)")

async def process_file_content(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    """Procesa contenido multimedia (imágenes/docs) usando Gemma 3."""
    import gc
    import pandas as pd
    from ai.service import ai_service
    
    # 1. Reaccionar con un corazón inmediatamente (notificar que se guardó/recibió)
    try:
        await update.message.set_reaction(reaction=[ReactionTypeEmoji(emoji="❤️")])
    except Exception as e:
        logger.warning(f"No se pudo poner la reacción: {e}")

    caption = update.message.caption or ("Analiza este documento por fis." if mode == "document" else "Analiza esta imagen.")
    
    # Simular que está procesando (sin mensaje intrusivo)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    file_path = None
    try:
        if mode == "photo":
            if update.message.photo:
                file_obj = await update.message.photo[-1].get_file()
                ext = ".jpg"
            else:
                file_obj = await update.message.document.get_file()
                ext = os.path.splitext(update.message.document.file_name)[1]
        else:
            file_obj = await update.message.document.get_file()
            ext = os.path.splitext(update.message.document.file_name)[1].lower()

        # Guardar en carpeta docs
        if not os.path.exists("docs"):
            os.makedirs("docs")
            
        file_path = os.path.abspath(f"docs/{file_obj.file_id}{ext}")
        await file_obj.download_to_drive(file_path)
        logger.info(f"Archivo descargado en: {file_path}")

        extracted_text = ""
        if mode == "document":
            # Extraer texto según extensión
            try:
                if ext == ".pdf":
                    import fitz # PyMuPDF
                    doc = fitz.open(file_path)
                    extracted_text = "\n".join([page.get_text() for page in doc])
                    doc.close()
                elif ext in [".docx", ".doc"]:
                    from docx import Document as DocxDocument
                    doc = DocxDocument(file_path)
                    extracted_text = "\n".join([p.text for p in doc.paragraphs])
                elif ext in [".xlsx", ".xls"]:
                    df = pd.read_excel(file_path)
                    extracted_text = df.to_string()
                elif ext == ".txt":
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        extracted_text = f.read()
            except Exception as extract_err:
                logger.error(f"Error extrayendo texto de {ext}: {extract_err}")
                extracted_text = "[Error al extraer el texto del documento]"

        # Procesar con Gemma 3
        async with processing_lock:
            if mode == "photo":
                # Análisis de imagen (Multimodal)
                response_messages = ai_service.generate_multimodal_response(caption, file_path)
            else:
                # Análisis de documento (Texto)
                doc_prompt = f"He leído el documento que me enviaste. Aquí tienes el contenido:\n\n---\n{extracted_text[:4000]}\n---\n\n{caption}"
                response_messages = ai_service.generate_response(doc_prompt)
            
            # Enviar respuestas secuenciales
            for msg in response_messages:
                if not msg.strip(): continue
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                typing_delay = min(len(msg) * 0.05, 4.0) + 0.5
                await asyncio.sleep(typing_delay)
                await update.message.reply_text(msg)
            
            # Liberación estricta de recursos
            ai_service.unload_model()
            gc.collect()

    except Exception as e:
        logger.error(f"Error procesando multimedia: {e}")
        await update.message.reply_text("¡Waaa! Me mareé intentando entender eso... 😵")
    finally:
        # Limpieza agresiva de RAM
        gc.collect()
