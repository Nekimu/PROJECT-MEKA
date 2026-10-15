# Auditoría técnica — Project MEKA

**Fecha:** 15 de octubre de 2026 · **Versión auditada:** `64901f9` (1.0.0) · **Resultado:** versión 1.1.0

## Resumen

La auditoría encontró **tres errores críticos** que impedían usar el bot tal como lo describe el README:

1. **El bot no arrancaba en una instalación limpia.** El `requirements.txt` hacía que pip instalara `python-telegram-bot` 20.7 y `ollama` 0.1.7, y el bot fallaba al iniciar con `ImportError`.
2. **Los documentos nunca se procesaban.** Un filtro mal escrito lanzaba una excepción con cada documento, sticker o vídeo.
3. **El chat dejaba de responder tras enviar una foto**, hasta reiniciar el bot.

También había **fugas de privacidad entre usuarios**: el historial y la memoria eran globales y el bot no tenía control de acceso. A esto se suman bloqueos del *event loop*, código duplicado y configuración que se ignoraba.

Todos los hallazgos marcados con ✅ están corregidos en esta versión, con 53 tests automatizados y CI en GitHub Actions. Las secciones 3 y 4 evalúan versiones nuevas y alternativas. La sección 5 propone una hoja de ruta.

---

## 1. Errores encontrados

**Severidad:** 🔴 crítica (rompe una funcionalidad principal) · 🟠 alta (seguridad o privacidad, o fallo frecuente) · 🟡 media · ⚪ baja.

### 🔴 Críticos

| # | Problema | Dónde | Impacto | Verificación | Estado |
|---|---|---|---|---|---|
| 1 | `python-telegram-bot==20.*` exige `httpx~=0.25/0.26` y el `ollama` actual exige `httpx>=0.27`. pip resuelve el conflicto bajando a **PTB 20.7**, que no tiene `ReactionTypeEmoji`, y a **ollama 0.1.7** (de 2024). | `requirements.txt` | `ImportError` al ejecutar `python run.py` | `pip install --dry-run -r requirements.txt` y `from telegram import ReactionTypeEmoji` | ✅ PTB 22.x y ollama 0.6.x |
| 2 | Se usaba `filters.Document`, que es un *espacio de nombres* y no un filtro. El filtro real es `filters.Document.ALL`. | `bot/main.py` | Con cada documento, sticker, vídeo, etc. saltaba `AttributeError: type object 'Document' has no attribute 'check_update'`. **Los documentos nunca funcionaron.** | Probado con PTB 22.8 | ✅ + test de regresión |
| 3 | El análisis de imágenes guardaba en el historial compartido `{"images": [ruta]}`, y el archivo se borraba justo después. Desde ese momento, cada llamada a Ollama fallaba con `ValueError: File … does not exist`. El historial además solo se recortaba cuando la llamada tenía éxito, así que **nunca se recuperaba**. | `ai/service.py` | El chat quedaba roto hasta reiniciar el bot | Reproducido con ollama 0.6.3 | ✅ El historial guarda solo texto + test de regresión |

### 🟠 Altos

| # | Problema | Dónde | Estado |
|---|---|---|---|
| 4 | El historial de conversación era **global**: los mensajes de todos los usuarios y chats se mezclaban en el mismo contexto del LLM. | `ai/service.py` | ✅ `ConversationStore` por `chat_id` |
| 5 | La memoria persistente era **global**: cualquier usuario podía preguntar *"¿recuerdas…?"* y recibir los datos que otro había guardado. | `core/memory.py` | ✅ Memoria por `user_id`, con migración del formato antiguo |
| 6 | **Sin control de acceso**: cualquiera que encontrara el bot podía usar la CPU y la GPU del equipo. | `bot/main.py` | ✅ `ALLOWED_USER_IDS` + registro de intentos no autorizados |
| 7 | Los **mensajes editados** llegaban a los manejadores con `update.message = None` y provocaban `AttributeError`. Pasaba también con los comandos editados. | `bot/handlers.py` | ✅ `filters.UpdateType.MESSAGE`, `effective_message` y `allowed_updates` |
| 8 | Las llamadas a Ollama, Whisper, la carga de Qwen-TTS y la extracción de documentos eran **síncronas dentro de corutinas**. Bloqueaban el *event loop* durante toda la inferencia, y el indicador "escribiendo…" y el resto de updates quedaban congelados. | `ai/*.py`, `bot/handlers.py` | ✅ `asyncio.to_thread` |

### 🟡 Medios

| # | Problema | Estado |
|---|---|---|
| 9 | `ai.temperature` de `config.yml` se ignoraba: estaba fija a `0.8` en el código. | ✅ Opciones desde `config.yml` |
| 10 | La reacción usaba `"❤️"` (U+2764 U+FE0F). Telegram solo acepta `"❤"` (sin selector de variación), y el `try/except` ocultaba el fallo. | ✅ `ReactionEmoji.RED_HEART` |
| 11 | Whisper se ejecutaba **fuera** del lock de RAM y podía coincidir en memoria con Ollama o Qwen de otra petición. | ✅ STT y LLM en el mismo bloque del lock |
| 12 | Si fallaba el envío, los audios TTS no se borraban y los modelos no se liberaban: no había `finally`. | ✅ Limpieza garantizada |
| 13 | Se enviaban al usuario textos de excepción (`str(e)`) y `error_handler` volcaba el `Update` completo, con el texto del mensaje, al log. | ✅ Mensajes genéricos, trazas solo en el log |
| 14 | El fallo de STT se detectaba con `"Error" in transcription`: si el usuario decía *"Error…"*, se descartaba su audio. En CPU, además, salía el aviso de FP16. | ✅ Devuelve `None` y usa `fp16` solo con CUDA |
| 15 | Qwen y Piper generan WAV y se enviaba con `sendVoice`. Telegram solo garantiza mostrarlo como nota de voz si es OGG/Opus (o MP3/M4A). | ✅ Conversión a OGG/Opus con FFmpeg |
| 16 | Los `file_id` de stickers y las URLs de GIF eran **inventados** (patrones repetidos como `8S7G8S7G…`) y fallaban siempre en silencio. | ✅ Movidos a `media.*` en `config.yml`, vacíos por defecto |
| 17 | `.doc` y `.xls` se anunciaban como soportados, pero python-docx no lee `.doc` y pandas necesita `xlrd` (no instalado) para `.xls`. | ✅ Retirados; se añaden `.md`, `.csv` y las tablas de DOCX |
| 18 | `config.yml`, `memory.json` y `ref_audio` se resolvían respecto al **directorio de ejecución**, así que fallaban al lanzar el bot desde otra carpeta. | ✅ Rutas relativas a la raíz del proyecto |
| 19 | `import whisper` en la cabecera de `stt.py` y `import torch` en el *health check* de Qwen cargaban PyTorch al arrancar, aunque el diseño era de carga diferida. | ✅ Imports diferidos y `importlib.util.find_spec` |

### ⚪ Bajos

| # | Problema | Estado |
|---|---|---|
| 20 | Texto con *mojibake* (`crÃ­ticas`), imports sin usar, `_check_model()` muerto y claves de configuración sin efecto (`system_prompt_file`, `log_level`, `request_timeout`). | ✅ |
| 21 | En un camino de error, `generate_multimodal_response` devolvía `str` en lugar de `list`, y el handler habría enviado cada carácter como un mensaje. | ✅ |
| 22 | Las respuestas a documentos se enviaban sin quitar etiquetas como `[AUDIO]`. | ✅ |
| 23 | `tests/` contenía scripts manuales, no tests. `test_tts.py` habría cargado Qwen-TTS al ejecutar `pytest`. | ✅ Movidos a `scripts/` + tests reales |
| 24 | `verify_ollama.py` ignoraba `ai.base_url`. | ✅ |
| 25 | La búsqueda en memoria no normalizaba tildes ni puntuación (`¿recuerdas`, `favorito?`). | ✅ Normalización y ranking por coincidencias |
| 26 | Después de cada mensaje se llamaba a `unload_model()`, aunque `keep_alive=0` ya descarga el modelo: una petición HTTP extra en cada interacción. | ✅ `keep_alive` configurable |
| 27 | README con imágenes rotas (capturas inexistentes) y licencia MIT declarada sin archivo `LICENSE`. | ✅ |

---

## 2. Mejoras de modularidad aplicadas

| Antes | Después |
|---|---|
| La limpieza de etiquetas y acotaciones estaba duplicada en `tts.py` y `handlers.py`. | `ai/text_utils.py`: funciones puras (`parse_message`, `clean_for_speech`, `split_into_messages`) testeadas por separado. |
| La extracción de documentos vivía dentro del handler de Telegram e importaba pandas en cada foto. | `core/documents.py`: extractores por extensión, sin pandas y con corte temprano. |
| `process_and_reply` (≈100 líneas) mezclaba IA, TTS, envío y limpieza. | `_respond` → `_deliver` → `_send_reply`, con responsabilidades separadas y limpieza en `finally`. |
| `AIService`, `TTSService` y `STTService` leían la configuración global y creaban su cliente dentro. | **Inyección de dependencias** opcional (`config`, `client`, `memory`), lo que permite testearlos con dobles. |
| Los motores TTS se elegían con una cadena de `if/elif`. | Tabla de despacho por motor + **motor de respaldo** (`fallback_engine`). |
| `run_bot()` creaba la aplicación, registraba los handlers y la ejecutaba. | `build_application()` separado y testeable; `run_bot()` solo diagnostica y arranca. |
| Valores fijos en el código (opciones de Ollama, tamaño de Whisper, límite de documentos, stickers...). | Todo en `config.yml`, con valores por defecto compatibles. |
| Los prompts de visión y de documentos estaban dentro de los métodos. | Centralizados en `ai/prompts.py`. La personalidad se puede cambiar con un archivo. |

**Pendiente, para cuando el proyecto crezca:**

- **Configuración tipada** con [pydantic-settings](https://pypi.org/project/pydantic-settings/) 2.16. `pydantic` ya llega como dependencia de `ollama`, así que los errores de configuración se detectarían al arrancar.
- **Eliminar los singletons globales** (`ai_service`, `tts_service`...) y crearlos en `run_bot()`, guardándolos en `application.bot_data`.
- **Un `Protocol` `TTSEngine`** con una clase por motor si se añaden más de los tres actuales.

---

## 3. Nuevas versiones y viabilidad

Versiones consultadas en PyPI y en las páginas de releases de GitHub el 15/10/2026.

| Tecnología | En el proyecto | Última versión | Viabilidad | Decisión |
|---|---|---|---|---|
| **Python** | "3.10+" | 3.14 estable; 3.15.0 programada para el 9-oct-2026 | 3.10 llega a fin de soporte este mes. `numpy` 2.5 ya exige ≥ 3.12. | ✅ Se exige **3.11+** (recomendado 3.12). CI en 3.11–3.13. Conviene esperar a que PyTorch y Qwen-TTS publiquen ruedas para 3.14/3.15. |
| **python-telegram-bot** | `20.*` (resolvía 20.7) | **22.8** (12-jun-2026) | Alta: la API que usa el bot no cambia. | ✅ Aplicado (`>=22,<23`) y verificado con tests. |
| **ollama** (librería) | sin fijar (resolvía 0.1.7) | **0.6.3** (29-sep-2026) | Alta: respuestas tipadas (`response.message.content`). | ✅ Aplicado (`>=0.6,<1`). |
| **Ollama** (servidor) | — | **v0.40.5** (14-oct-2026) | Alta: no requiere cambios de código. | 🔼 Actualizar el instalador local. Las versiones recientes son necesarias para Gemma 4. |
| **Modelo LLM** | `gemma3:12b` | **Gemma 4** (`e2b`, `e4b`, `26b`, `31b`; Apache 2.0) | Alta: también es multimodal, basta con cambiar `ai.model`. | 🧪 Probar `gemma4:e4b-it-qat` (~6 GB de descarga, según fuentes secundarias) frente a `gemma3:12b`. No se cambia por defecto porque altera el tono de la personalidad. |
| **openai-whisper** | sin fijar | 20250625 (sin cambios desde jun-2025) | — | Se mantiene. Ver alternativa *faster-whisper* en la sección 4. |
| **edge-tts** | sin fijar | **7.3.1** (13-oct-2026) | Alta | ✅ `>=7.0`. |
| **qwen-tts** | no listado | **0.1.1** (feb-2026) | Media: fija `transformers==4.57.3` y `accelerate==1.12.0`, e instala `gradio`. | ✅ Separado en `requirements-qwen.txt`. Se usa su API `create_voice_clone_prompt` para cachear la voz. |
| **Piper** | binario de Windows por subprocess | `piper-tts` **1.8.0** (sep-2026, GPL-3.0) | Media: el repositorio original `rhasspy/piper` se archivó y continúa como `OHF-Voice/piper1-gpl`, con paquete pip y API de Python. | 🔼 Opcional: sustituir el subprocess por el paquete pip. Se mantiene el motor actual. |
| **PyMuPDF** | sin fijar | **1.28.2** (ago-2026, **AGPL-3.0**) | Alta (`import pymupdf` desde 1.24.3) | ✅ `>=1.24.3`, con `import pymupdf` y *fallback* a `fitz`. |
| **pandas** | sin fijar | 3.0.6 (exige Python ≥ 3.11) | No hace falta: solo se usaba `read_excel().to_string()`. | ✅ **Eliminado.** Ahora se usa openpyxl directamente (≈ 60 MB menos). |
| **pydub** | sin fijar | 0.25.1 (2021, sin mantenimiento; en Python 3.13 necesita `audioop-lts`) | No se usaba. | ✅ **Eliminado.** La conversión de audio usa FFmpeg directamente. |
| **PyTorch** | transitiva (Whisper) | **2.14.1** | La rueda por defecto en Linux arrastra varios GB de librerías CUDA 13. | 📄 README: instalar la versión CPU si no hay GPU NVIDIA. |
| python-docx / openpyxl / PyYAML / python-dotenv / colorama | sin fijar | 1.2.0 / 3.1.5 / 6.0.3 / 1.2.4 / 0.4.6 | Alta | ✅ Con versiones mínimas. |
| GitHub Actions | — | `actions/checkout@v7`, `actions/setup-python@v7` | — | ✅ Usadas en el CI. Dependabot las mantiene al día. |

---

## 4. Alternativas evaluadas

### 4.1 Motor de LLM

| Opción | Ventajas | Inconvenientes | Veredicto |
|---|---|---|---|
| **Ollama** (actual) | Instalación trivial, gestión de modelos, API multimodal, `keep_alive` | Menos control fino que llama.cpp | ✅ **Mantener** |
| llama.cpp (`llama-server`) | Máximo control (cuantización, offload por capas) y API compatible con OpenAI | Gestión manual de modelos GGUF | Solo si se necesita exprimir una GPU de 2 GB |
| LM Studio | Interfaz gráfica, API compatible con OpenAI | No es software libre; pensado para escritorio | No aporta frente a Ollama |
| vLLM | Máximo rendimiento con muchos usuarios | Requiere GPU potente; excesivo para un bot personal | ❌ |

### 4.2 Reconocimiento de voz (STT)

| Opción | Ventajas | Inconvenientes | Veredicto |
|---|---|---|---|
| **openai-whisper** (actual) | Implementación de referencia, sencilla | Lenta en CPU; arrastra PyTorch completo | Válida |
| **faster-whisper** 1.2.1 | 2–4× más rápida y con menos memoria, **mismos pesos** (CTranslate2); cuantización `int8` en CPU; MIT | Otra dependencia nativa | ⭐ **Recomendada**: es un cambio local en `ai/stt.py`. Con `small` en `int8` se gana precisión sin perder velocidad. |
| whisper.cpp | Muy ligera, sin Python ni PyTorch | Hay que gestionar un binario externo | Alternativa para equipos muy modestos |

### 4.3 Síntesis y clonación de voz (TTS)

| Opción | Clonación | Español | Licencia | Comentario |
|---|---|---|---|---|
| **Qwen3-TTS 0.6B** (actual) | ✅ (3 s de referencia) | ✅ | Apache-2.0 | Buena calidad; dependencias pesadas y lento en CPU. **Mantener** como motor principal. |
| **Chatterbox Multilingual** (Resemble AI) | ✅ *zero-shot* | ✅ (23 idiomas) | MIT | ⭐ La mejor alternativa con clonación y licencia permisiva. Añade marca de agua (PerTh). |
| F5-TTS | ✅ | Parcial | Código MIT; **pesos CC-BY-NC** | ⚠️ Solo para uso no comercial. |
| XTTS-v2 (Coqui) | ✅ | ✅ | **CPML (no comercial)** | ⚠️ Coqui cerró en 2024; sin mantenimiento oficial. |
| Piper (`piper-tts` 1.8) | ❌ | ✅ voces es_ES/es_MX | GPL-3.0 | Muy rápido en CPU. Buen **respaldo local** en lugar de edge-tts. |
| Edge-TTS (actual, respaldo) | ❌ | ✅ | Servicio de Microsoft | Gratis y de calidad, pero **envía el texto a la nube** y no es una API oficial. |

**Recomendación:** mantener Qwen3-TTS y cambiar el respaldo a **Piper** si la privacidad total es prioritaria. Si Qwen resulta demasiado lento en CPU, evaluar **Chatterbox Multilingual**.

### 4.4 Framework de Telegram

| Opción | Veredicto |
|---|---|
| **python-telegram-bot 22** (actual, LGPL-3.0) | ✅ **Mantener.** Madura, bien documentada y con soporte de la Bot API al día. |
| aiogram 3.31 (MIT) | Muy buena (routers, FSM, middlewares), pero migrar no aporta funcionalidad nueva al bot. |

### 4.5 Memoria

| Opción | Ventajas | Veredicto |
|---|---|---|
| JSON por usuario (actual) | Simple, sin dependencias | Suficiente para uso personal |
| **SQLite** (`sqlite3` de la biblioteca estándar) | Transacciones, consultas, sin dependencias nuevas | ⭐ Siguiente paso natural |
| **Memoria semántica**: embeddings de Ollama (`/api/embed`) + `sqlite-vec` | Recupera recuerdos por **significado**, no por palabras clave (*"¿qué comida me gusta?"* encuentra *"me encanta el ramen"*) | ⭐ Mayor salto de calidad percibida |
| *Tool calling* de Ollama para "recordar" | El modelo decide qué guardar, sin depender de la frase exacta *"recuerda esto:"* | Interesante en combinación con lo anterior |

### 4.6 Empaquetado y despliegue

| Opción | Veredicto |
|---|---|
| pip + `requirements*.txt` (actual) | ✅ Suficiente y conocido. |
| **uv** + `pyproject.toml` + `uv.lock` | ⭐ Instalaciones mucho más rápidas y entornos **reproducibles** con *lockfile*. Habría evitado el error crítico n.º 1. |
| Docker Compose (bot + Ollama) | Útil para un servidor 24/7. En Windows con GPU añade complejidad. Opcional. |
| Servicio del sistema (systemd / NSSM en Windows) | Recomendado si el bot debe estar siempre encendido. |

---

## 5. Hoja de ruta recomendada

| Prioridad | Tarea | Esfuerzo | Beneficio |
|---|---|---|---|
| 1 | Actualizar Ollama (≥ 0.40) y probar `gemma4:e4b-it-qat` frente a `gemma3:12b` | Bajo | Mejores respuestas y visión con menos RAM |
| 2 | Retirar del repositorio los audios de voces de terceros (`audio/*.wav`) y documentar cómo aportar una voz propia | Bajo | Riesgo legal (derechos de imagen y propiedad intelectual de actores de doblaje) |
| 3 | Migrar STT a **faster-whisper** | Bajo-medio | Notas de voz 2–4× más rápidas |
| 4 | Memoria en **SQLite + embeddings** | Medio | Recuerdos por significado |
| 5 | **uv** + *lockfile* | Bajo | Instalaciones reproducibles |
| 6 | Configuración tipada con **pydantic-settings** | Medio | Errores de configuración detectados al arrancar |
| 7 | Respaldo TTS local con **Piper** (`piper-tts`) | Bajo | Privacidad total, sin edge-tts |

---

## 6. Presentación en GitHub

**Hecho en esta versión:** README rediseñado (badges, índice, diagrama de arquitectura, referencia de configuración y solución de problemas), `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, plantillas de issues y PR, CI con badge y Dependabot.

**Pendiente (solo el propietario puede hacerlo desde la web de GitHub):**

- **Descripción** del repositorio: *"💖 Compañera virtual para Telegram con IA local (Ollama): voz clonada, visión, documentos y memoria."*
- **Topics:** `telegram-bot` `python` `ollama` `local-llm` `llm` `whisper` `text-to-speech` `voice-cloning` `qwen-tts` `gemma` `multimodal` `chatbot` `python-telegram-bot`.
- **Imagen social** (*Settings → Social preview*, 1280×640).
- **Release `v1.1.0`** con las notas del CHANGELOG.
- **Capturas o un GIF de demostración** en `docs/screenshots/` (la galería ya está preparada en el README).
- **Protección de la rama `main`** exigiendo que pase el CI.

---

## 7. Verificación realizada

| Comprobación | Resultado |
|---|---|
| `pytest` (53 tests: texto, memoria, documentos, configuración, servicio de IA, TTS y registro de handlers) | ✅ 53 pasan |
| `ruff check .` y `ruff format --check .` | ✅ Sin errores |
| `pip install --dry-run -r requirements-dev.txt` | ✅ Resuelve PTB 22.8, ollama 0.6.3 y httpx 0.28.1, sin conflictos |
| Simulación de los handlers con Telegram y Ollama falsos: texto con `[AUDIO]`/`[STICKER]`, foto seguida de chat, DOCX, nota de voz con *"recuerda esto"* y formato no soportado | ✅ Mensajes correctos, audio convertido a OGG/Opus y ningún archivo temporal restante |

**No verificado en este entorno** (sin acceso a Telegram real, a un servidor de Ollama ni al modelo Qwen-TTS): la conversación real con el bot y la generación de voz con el modelo Qwen descargado. El uso de `create_voice_clone_prompt` se comprobó leyendo el código fuente de `qwen-tts` 0.1.1 y con un modelo simulado. Conviene una prueba manual con `python -m scripts.tts_smoke_test`.

## Fuentes

- PyPI (JSON API) para todas las versiones de paquetes: [python-telegram-bot](https://pypi.org/project/python-telegram-bot/), [ollama](https://pypi.org/project/ollama/), [qwen-tts](https://pypi.org/project/qwen-tts/), [faster-whisper](https://pypi.org/project/faster-whisper/), [piper-tts](https://pypi.org/project/piper-tts/), [pandas](https://pypi.org/project/pandas/), [pymupdf](https://pypi.org/project/PyMuPDF/).
- [Releases de Ollama](https://github.com/ollama/ollama/releases) · [Releases de python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot/releases) · [actions/checkout](https://github.com/actions/checkout/releases) · [actions/setup-python](https://github.com/actions/setup-python/releases).
- [Gemma con Ollama (Google AI)](https://ai.google.dev/gemma/docs/integrations/ollama) · [Biblioteca de Ollama: gemma4](https://ollama.com/library/gemma4).
- [Calendario de Python 3.15](https://www.python.org/downloads/release/python-3150rc3/).
- [Chatterbox (Resemble AI)](https://resemble.ai/chatterbox) · [Comparativa de TTS locales: Piper, Coqui XTTS](https://www.promptquorum.com/power-local-llm/local-tts-voice-cloning-piper-coqui-xtts) · [Revisión de Piper TTS](https://www.promptquorum.com/power-local-llm/piper-tts-review).
- [Comparativa faster-whisper / whisper.cpp / Whisper](https://codersera.com/blog/faster-whisper-vs-whisper-cpp-speech-to-text-2026/amp/).
- [Bot API de Telegram — sendVoice](https://core.telegram.org/bots/api#sendvoice).
