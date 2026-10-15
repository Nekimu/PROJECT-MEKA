# Changelog

Todos los cambios relevantes del proyecto. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [1.1.0] — 2026-10-15

Auditoría completa del proyecto. Detalle en [`docs/AUDITORIA.md`](docs/AUDITORIA.md).

### Corregido
- **El bot no arrancaba en una instalación limpia**: `python-telegram-bot==20.*` y `ollama` sin fijar entraban en conflicto por `httpx`; pip resolvía PTB 20.7 (sin `ReactionTypeEmoji`) y `ollama` 0.1.7 → `ImportError` al iniciar.
- **Los documentos nunca se procesaban**: se usaba `filters.Document` (un espacio de nombres) en lugar de `filters.Document.ALL`, lo que lanzaba `AttributeError` con cada documento, sticker o vídeo.
- **El chat dejaba de funcionar tras enviar una foto**: la ruta de la imagen (ya borrada) quedaba en el historial y todas las respuestas siguientes fallaban hasta reiniciar.
- Los mensajes **editados** provocaban `AttributeError` (`update.message` es `None`).
- La reacción ❤️ usaba un emoji con selector de variación que Telegram no acepta.
- La **temperatura** de `config.yml` se ignoraba (estaba fija a 0.8).
- Las llamadas a Ollama, Whisper, Qwen-TTS y la lectura de documentos **bloqueaban el event loop**.
- Whisper se ejecutaba fuera del lock de RAM y podía coincidir en memoria con Ollama/Qwen.
- Audios TTS que quedaban en disco si fallaba el envío; mojibake en `ai/tts.py`.
- Stickers y GIFs con IDs inventados que siempre fallaban en silencio.
- Rutas relativas al directorio de ejecución (fallaba al lanzar el bot desde otra carpeta).
- `.doc` y `.xls` se anunciaban como soportados pero no podían leerse.

### Seguridad y privacidad
- Lista blanca de usuarios con `ALLOWED_USER_IDS` (antes cualquiera podía usar el bot).
- Historial de conversación **por chat** y memoria persistente **por usuario** (antes era global y compartido entre todos los usuarios). Migración automática del formato antiguo de `memory.json`.
- Los errores internos ya no se muestran al usuario ni se vuelca el contenido de los mensajes en los logs.
- Escritura atómica de `memory.json` y copia de seguridad si está corrupto.

### Añadido
- Comandos `/reset`, `/recuerdos` y `/olvidar`, y menú de comandos en Telegram.
- Conversión de audio a OGG/Opus (nota de voz nativa de Telegram) y motor TTS de respaldo.
- Caché del *voice prompt* de Qwen-TTS: la voz de referencia se procesa una vez por carga.
- Personalidad configurable desde un `.txt`/`.md` (`ai.system_prompt_file`).
- Opciones nuevas en `config.yml`: `keep_alive`, `history_size`, `options`, `stt.*`, `documents.max_chars`, `media.*`...
- Lectura de tablas en DOCX, de `.md` y `.csv`; corte temprano en PDFs largos.
- 53 tests automatizados, ruff, GitHub Actions, Dependabot y plantillas de issues/PR.

### Cambiado
- Dependencias actualizadas: `python-telegram-bot` 22.x, `ollama` 0.6.x. Eliminadas `pandas` y `pydub` (no necesarias). Qwen-TTS pasa a `requirements-qwen.txt`.
- Los scripts manuales (`verify_ollama`, prueba de TTS, listado de voces) pasan de `tests/` a `scripts/`.
- Código común extraído a `ai/text_utils.py` y `core/documents.py`.

## [1.0.0] — 2026-06-25

- Versión inicial: bot de Telegram con Ollama, Whisper, Qwen-TTS/Edge-TTS, análisis de imágenes y documentos y memoria persistente.
