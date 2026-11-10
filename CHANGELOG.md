# Changelog

Todos los cambios relevantes del proyecto. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Cerebro intercambiable
- **Adaptadores de IA** (`ai/providers/`): Ollama (local), **Claude** (SDK oficial de Anthropic, `claude-opus-5-5` con `effort: low`, reintento automático si un filtro lo rechaza) y **Gemini** (`google-genai`, `gemini-flash-latest`). Los tres reciben el mismo prompt del personaje.
- **Enrutamiento** en `config.yml`: `ai.provider` (conversación), `ai.vision_provider` (imágenes), `ai.fallback_provider` (si el principal falla o se niega) y `ai.local_only` (nada sale del equipo).
- Las opciones de Ollama pasan a `ai.providers.ollama.*`. SDKs de la nube opcionales en `requirements-cloud.txt`; claves `ANTHROPIC_API_KEY` y `GEMINI_API_KEY` en `.env`.
- `/v1/health` indica qué cerebro usa cada tarea.

### Memoria en SQLite
- `memory.json` se sustituye por **SQLite** (`data/meka.db`): escrituras transaccionales, búsqueda **FTS5** que ignora tildes y plurales y ordena por relevancia, e **historial de chat persistente** (`memory.persist_history`). Evaluación frente a JSON y PostgreSQL en [`docs/MEMORIA.md`](docs/MEMORIA.md).
- **Migración automática**: el `memory.json` existente se importa al arrancar y se renombra a `memory.json.migrated`.

### MEKA Core: servidor local con canales como clientes
- **MEKA Core** (`server/app.py`, `core/engine.py`): servidor FastAPI en `127.0.0.1:8765` con API REST (chat, voz, archivos, síntesis de voz, memoria, eventos) y WebSocket `/v1/events` con el contrato de la mascota. Documentación interactiva en `/docs`.
- **Seguridad del servidor**: solo escucha en este equipo por defecto; fuera de `127.0.0.1` exige `MEKA_API_TOKEN` (si no, se niega a arrancar). Rechaza peticiones de webs ajenas (`Origin`) para que una página cualquiera no pueda usar MEKA desde el navegador. Límite de subida configurable.
- **Bus de eventos** (`core/events.py`): la mascota piensa (`emotion: thinking`) y dice lo que MEKA responde por cualquier canal (`server.broadcast_messages`). Los agentes externos publican `agent.working`, `agent.done`... con `POST /v1/events`.
- **Canal de Telegram** (`channels/telegram/`, antes `bot/`): ya no carga modelos ni toca la memoria; habla con MEKA Core por HTTP (`channels/client.py`), así que puede ir en otro equipo. Las fotos, documentos y notas de voz se descargan en memoria, sin archivos temporales.
- **Canal MCP** (`channels/mcp/`, `requirements-mcp.txt`): MEKA como herramienta de Claude Desktop, Claude Code, Gemini CLI o Cursor, con `pet_status`, `pet_emotion`, `chat`, `remember` y `memories`.
- `run.py` con modos: `all` (por defecto: núcleo + Telegram), `core`, `telegram` y `mcp`.
- La mascota se conecta a `ws://127.0.0.1:8765/v1/events` (antes `/events`) y acepta `?token=`.

### Todo configurable
- Nuevas secciones en `config.yml`: `server` (host, puerto, URL, orígenes, límite de subida, difusión, caducidad de audios), `paths` (memoria y temporales), `memory` (frase para recordar, disparadores y límite de búsqueda) y `mcp`.
- `telegram.typing_delay` controla las pausas de "escribiendo…" (antes fijas); `0` las desactiva.
- Variables nuevas en `.env`: `MEKA_API_TOKEN` y `MEKA_CORE_URL`.
- Rutas de Piper relativas al proyecto (`models/piper/...`) en lugar de `C:/ProjectMEKA/...`.

### Eliminado (código que ya no encaja con la nueva arquitectura)
- `bot/`: sustituido por `channels/telegram/`.
- Instancias globales creadas al importar (`ai_service`, `stt_service`, `tts_service`, `memory_system`, `persona`): ahora las crea MEKA Core una sola vez.
- `ai.system_prompt_file` y `read_prompt_override`: la personalidad vive en `personas/`.
- Claves antiguas de Piper en la raíz de `tts` y `tts.output_dir`; `media.*` pasa a `telegram.stickers` / `telegram.gifs` (son `file_id` de Telegram).
- Carpetas `temp_audio/` y `temp_media/`: todo lo temporal va a `temp/`.

### Filosofía híbrida
- **Personajes intercambiables** (`personas/`): cada paquete define personalidad (`persona.md`), nombre, voz y frases del bot (`persona.yml`). Se elige con `persona:` en `config.yml` o `MEKA_PERSONA`. Incluye MEKA (inspirado en D.Va, por defecto), Marin y Yotsuba.
- Ya no hay texto de ningún personaje fijo en el código: saludos, acuses de voz, errores, comandos y registros salen del paquete activo.
- Las reglas de formato (`---`, `[AUDIO]`, `[STICKER]`, `[GIF]`) son comunes y se añaden a cualquier personalidad.
- `docs/FILOSOFIA_HIBRIDA.md`: nueva dirección del proyecto, con el estado real del repositorio.
- README, visión y banner actualizados.

### Eliminado
- Audios de referencia de voces de terceros (`audio/`). Qwen3-TTS solo debe clonar tu propia voz o una con permiso, guardada en `voices/` (ignorada por git). El motor por defecto pasa a ser Edge-TTS, con la voz definida por cada personaje.

### Añadido
- **Prototipo de mascota de escritorio** (`pet/`): máquina de estados con 9 estados animados, Tamagotchi no punitivo (energía, saciedad, ánimo, afecto) con progreso offline, menú contextual, chat, personajes desbloqueables, vista previa en pixel art y cliente WebSocket del contrato de eventos de MEKA Core.
- Envoltorio de escritorio con **Tauri 2**: ventana transparente, sin bordes y siempre visible.
- 4 personajes a partir de arte original: MEKA, Nekimu, Espadachina y Kitsune.
- `pet/tools/stickerize.py`: recorta el fondo de stickers y los convierte a WebP con transparencia.
- `docs/VISION.md`: visión, arquitectura, contrato de eventos, guía de arte y mecánicas.
- Test que valida el manifiesto de personajes.
- Tests de los paquetes de personaje y de la selección por configuración.
- Tests del servidor, del cliente, del WebSocket, del canal MCP y de los manejadores de Telegram contra MEKA Core (104 tests en total).

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
- El análisis de documentos e imágenes borraba el texto entre paréntesis ("200 € (IVA incluido)" llegaba como "200 €").
- Los mensajes de más de 4096 caracteres (p. ej. `/recuerdos` con muchos recuerdos) eran rechazados por Telegram; ahora se trocean.

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
- README renovado con banner, ejemplo de conversación, inicio rápido por sistema operativo y hoja de ruta.
- Lectura de tablas en DOCX, de `.md` y `.csv`; corte temprano en PDFs largos.
- 56 tests automatizados, ruff, GitHub Actions, Dependabot y plantillas de issues/PR.

### Cambiado
- Dependencias actualizadas: `python-telegram-bot` 22.x, `ollama` 0.6.x. Eliminadas `pandas` y `pydub` (no necesarias). Qwen-TTS pasa a `requirements-qwen.txt`.
- Los scripts manuales (`verify_ollama`, prueba de TTS, listado de voces) pasan de `tests/` a `scripts/`.
- Código común extraído a `ai/text_utils.py` y `core/documents.py`.

## [1.0.0] — 2026-06-25

- Versión inicial: bot de Telegram con Ollama, Whisper, Qwen-TTS/Edge-TTS, análisis de imágenes y documentos y memoria persistente.
