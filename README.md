<div align="center">

<img src="docs/assets/banner.svg" alt="Project MEKA — Asistente personal híbrido con personalidad anime" width="100%">

### Tu asistente personal con alma de personaje anime.<br>Conversa, escucha, ve y recuerda. Cambia de modelo de IA sin cambiar de asistente.

[![CI](https://img.shields.io/github/actions/workflow/status/Nekimu/PROJECT-MEKA/ci.yml?branch=main&style=flat-square&label=CI&logo=githubactions&logoColor=white)](https://github.com/Nekimu/PROJECT-MEKA/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11_|_3.12_|_3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/python--telegram--bot-22.x-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://python-telegram-bot.org/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-000000?style=flat-square&logo=ollama&logoColor=white)](https://ollama.com)
[![Ruff](https://img.shields.io/badge/estilo-Ruff-D7FF64?style=flat-square&logo=ruff&logoColor=black)](https://github.com/astral-sh/ruff)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-22C55E?style=flat-square)](LICENSE)
[![Último commit](https://img.shields.io/github/last-commit/Nekimu/PROJECT-MEKA?style=flat-square&label=último%20commit)](https://github.com/Nekimu/PROJECT-MEKA/commits)

[**Inicio rápido**](#-inicio-rápido) ·
[**Personajes**](#-personajes) ·
[**Filosofía**](#-filosofía-híbrida) ·
[**Configuración**](#️-configuración) ·
[**Cómo funciona**](#-cómo-funciona) ·
[**Hoja de ruta**](#️-hoja-de-ruta) ·
[**Problemas frecuentes**](#-problemas-frecuentes)

</div>

---

**Project MEKA** es un asistente personal al estilo de Alexa o Google Home, pero con identidad propia: un personaje anime que conversa contigo, escucha tus notas de voz, comenta tus fotos y documentos y recuerda lo que le cuentas. El objetivo final es darle vida a una figura Funko del Meka de D.Va con voz, luces y un avatar en pantalla.

La personalidad, la memoria y la voz pertenecen a MEKA, no al modelo de IA. Piensa con [Ollama](https://ollama.com) en tu equipo, con Claude o con Gemini: cambias de cerebro con una línea de configuración y el personaje sigue siendo el mismo.

> [!TIP]
> **Una mascota que vive en tu escritorio.** Prueba el [prototipo](pet/README.md) (abre `pet/web/index.html`) y lee la [visión del proyecto](docs/VISION.md).

> [!NOTE]
> Proyecto personal con fines educativos y de entretenimiento. No está afiliado a los autores ni a los titulares de la obra original.

## 🎭 Personajes

MEKA tiene un solo "cerebro" técnico y **varios personajes intercambiables**. Cada uno es un paquete en [`personas/`](personas/README.md) con su personalidad, su nombre, su voz y sus frases:

| Personaje | Inspirado en | Estilo |
|---|---|---|
| **MEKA** (`dva`, por defecto) | D.Va / Hanna Song, *Overwatch* | Gamer, segura y competitiva; rigurosa en lo serio |
| **Marin** (`marin`) | Marin Kitagawa, *Sono Bisque Doll wa Koi wo Suru* | Gyaru, otaku del cosplay, cariñosa |
| **Yotsuba** (`yotsuba`) | Yotsuba Nakano, *Go-Tōbun no Hanayome* | Optimista, servicial y deportista |

Para cambiar de personaje basta con `persona: "yotsuba"` en `config.yml` o `MEKA_PERSONA=yotsuba` en `.env`. Crear uno nuevo es copiar una carpeta y editar dos archivos.

## 🧭 Filosofía híbrida

> **Cambiar de motor no debe significar cambiar de asistente.**

- **Identidad propia.** La personalidad, la memoria y la voz viven en el proyecto, no en el proveedor de IA.
- **Híbrido hoy, local como destino.** Se pueden usar servicios en la nube para avanzar, pero lo privado se queda en tu equipo y el objetivo es funcionar en local.
- **Proveedores reemplazables.** Ollama, Gemini, Claude u otros son motores intercambiables, elegidos por tarea, costo y privacidad.
- **Sin voces protegidas.** Los personajes se inspiran en obras existentes pero no imitan grabaciones de sus actrices.

El documento completo, con las iteraciones previstas (Google Home, Home Assistant, adaptadores de proveedor y migración a local), está en [`docs/FILOSOFIA_HIBRIDA.md`](docs/FILOSOFIA_HIBRIDA.md).

## 💬 Así es una conversación

<table>
<tr><td>

> **Tú:** recuerda esto: mi cosplay favorito es Shizuku-tan
>
> **MEKA:** ¡Guardado! Shizuku-tan, buena elección 💾
>
> **Tú:** 🎙️ *nota de voz* — «¿te acuerdas de mi cosplay favorito? Cuéntamelo en un audio»
>
> **MEKA:** 🔊 *nota de voz* — «¡Claro! Shizuku-tan. Eso no se me olvida ni con lag.»
>
> **Tú:** 📄 *presupuesto.pdf* — «¿me ayudas a revisarlo?»
>
> **MEKA:** A ver... El total es de 200 € (IVA incluido) y la tela se lleva la mitad del presupuesto.

</td></tr>
</table>

<sub>Ejemplo ilustrativo con el personaje por defecto (MEKA, inspirado en D.Va). Las respuestas reales dependen del modelo y del personaje.</sub>

## ✨ Características

| | Función | Detalle |
|:---:|---|---|
| 🎭 | **Personajes intercambiables** | D.Va, Marin o Yotsuba, o el tuyo propio: [paquetes en `personas/`](personas/README.md) que se eligen con una línea de configuración. |
| 🧠 | **Cerebro a elegir** | Ollama en local (por defecto `gemma3:12b`), Claude o Gemini, con un cerebro distinto para imágenes, uno de respaldo y un modo `local_only` que no deja salir nada del equipo. |
| 🎙️ | **Escucha tus audios** | Transcribe las notas de voz con faster-whisper (3 veces menos RAM que Whisper, sin PyTorch) y responde como a un mensaje escrito. |
| 🔊 | **Habla** | Cada personaje tiene su voz (Edge-TTS por defecto; Qwen3-TTS y Piper opcionales). Llega como nota de voz nativa (OGG/Opus). |
| 🖼️ | **Ve tus fotos** | Comenta las imágenes con un modelo multimodal. |
| 📄 | **Lee documentos** | PDF, DOCX (con tablas), XLSX, TXT, MD y CSV. |
| ⏰ | **Agenda y avisos** | *«Recuérdame pagar la luz antes del 15»*, *«¿qué tareas me quedan?»*, *«ya pagué la luz»*. Entiende fechas en español sin depender del modelo y te avisa a su hora. De vez en cuando revisa tus pendientes y notificaciones y te lo recuerda, **sin interrumpir**: nunca en horas de silencio, en modo concentración ni mientras hablas con ella. |
| 💭 | **Recuerda** | Recuerdos por usuario (*«recuerda esto: …»*) e historial de cada chat en SQLite. Busca **por significado** con embeddings locales: *«¿qué te conté de mi mascota?»* encuentra *«mi perro se llama Toby»*. |
| 🔒 | **Privada** | Lista blanca de usuarios, historial aislado y archivos temporales que se borran al procesarse. |
| 🪶 | **Ligera** | Descarga los modelos tras cada respuesta para funcionar con 16 GB de RAM (configurable). |
| 🔌 | **Un núcleo, muchos canales** | MEKA Core es un servidor local (REST + WebSocket): Telegram, la mascota de escritorio y los agentes MCP (Claude, Gemini CLI, Cursor) se conectan a él. |

## 🚀 Inicio rápido

**Necesitas:** [Python 3.11+](https://www.python.org/downloads/) (recomendado 3.12) · [Ollama](https://ollama.com/download) · [FFmpeg](https://ffmpeg.org/download.html) en el `PATH` · un token de [@BotFather](https://t.me/BotFather).

```bash
git clone https://github.com/Nekimu/PROJECT-MEKA.git
cd PROJECT-MEKA
python -m venv venv
```

<details open>
<summary><b>🐧 Linux / 🍎 macOS</b></summary>

```bash
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

> [!TIP]
> La instalación base **no incluye PyTorch**: la voz usa faster-whisper. Solo hace falta para el respaldo
> `openai-whisper` (`pip install -r requirements-whisper.txt`) o para Qwen3-TTS. En Linux sin GPU NVIDIA,
> instala antes PyTorch para CPU y te ahorrarás varios GB de librerías CUDA:
> `pip install torch --index-url https://download.pytorch.org/whl/cpu`

</details>

<details>
<summary><b>🪟 Windows (PowerShell)</b></summary>

```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
winget install ffmpeg   # si aún no tienes FFmpeg
```

</details>

Después:

```bash
ollama pull gemma3:12b                  # 1. Descarga el modelo
ollama pull embeddinggemma              #    y el de la memoria semántica (~600 MB)
pip install -r requirements-qwen.txt    # 2. Opcional: Qwen3-TTS (clonar tu propia voz)
pip install -r requirements-cloud.txt   #    Opcional: Claude y Gemini como cerebro
pip install -r requirements-whisper.txt #    Opcional: respaldo openai-whisper (instala PyTorch)
python run.py                           # 3. ¡A charlar! (MEKA Core + Telegram)
```

| Comando | Qué arranca |
|---|---|
| `python run.py` | MEKA Core y los canales activados (Telegram) en un solo proceso |
| `python run.py core` | Solo MEKA Core en `http://127.0.0.1:8765` (API interactiva en `/docs`) |
| `python run.py telegram` | Solo el bot; se conecta a un MEKA Core ya en marcha, incluso en otro equipo |
| `python run.py mcp` | Servidor MCP por stdio para agentes ([ver abajo](#-canales-y-api)) |
| `scripts\iniciar_meka.cmd` | En Windows, con doble clic: arranca Ollama si hace falta y luego MEKA Core con Telegram, en su propia ventana. La isla necesita que el Core esté en marcha: sin él no hay música, notificaciones ni avisos. Para que arranque al iniciar sesión, pon un acceso directo a este archivo en `shell:startup` (Win+R); bórralo de ahí para quitarlo. |

Antes de arrancar, edita `.env` con tu token y tu ID de Telegram (puedes obtenerlo con [@userinfobot](https://t.me/userinfobot)):

```dotenv
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ALLOWED_USER_IDS=123456789
```

> [!IMPORTANT]
> Sin `ALLOWED_USER_IDS`, **cualquiera** que encuentre tu bot podrá usarlo y consumir los recursos de tu equipo. Los intentos de usuarios no autorizados aparecen en la consola con su ID.

<details>
<summary><b>💻 ¿Qué equipo necesito?</b></summary>

| | Mínimo | Recomendado |
|---|---|---|
| **RAM** | 8 GB (`gemma3:4b` + `edge-tts`) | 16 GB (`gemma3:12b` + Qwen3-TTS en CPU) |
| **GPU** | No necesaria | ≥ 8 GB de VRAM para respuestas fluidas |
| **Disco** | ~4 GB | ~15 GB (modelos de Ollama, Whisper y Qwen) |

</details>

## 🎮 Uso

| Quieres... | Haz esto |
|---|---|
| Empezar | `/start` |
| Charlar | Escríbele cualquier cosa |
| Que te hable | *«Mándame un audio contándome tu día»* |
| Hablarle | Envía una nota de voz |
| Enseñarle algo | Envía una foto; el pie de foto sirve de pregunta |
| Que lea un archivo | Envía un PDF, DOCX, XLSX, TXT, MD o CSV |
| Que recuerde algo | *«recuerda esto: mi color favorito es el azul»* |
| Preguntarle | *«¿te acuerdas de mi color favorito?»* |
| Ver sus recuerdos | `/recuerdos` |
| Borrar tus recuerdos | `/olvidar` |
| Empezar de cero | `/reset` (olvida la conversación, no los recuerdos) |

## 🔌 Canales y API

Todo pasa por **MEKA Core**, un servidor local que guarda el personaje, la memoria, la IA y la voz. Los canales solo son clientes, así que añadir uno nuevo (Discord, una app móvil, la figura física) no toca el núcleo.

| Canal | Cómo se conecta | Estado |
|---|---|---|
| Telegram | `channels/telegram/` → REST | ✅ |
| Mascota de escritorio | `pet/` → WebSocket `/v1/events` | ✅ |
| Agentes por MCP | `channels/mcp/` → REST (stdio hacia el agente) | ✅ |
| App móvil, figura del Meka | Tailscale + token → REST y WebSocket | Pendiente |

<details>
<summary><b>Conectar MEKA a Claude Desktop, Claude Code, Gemini CLI o Cursor (MCP)</b></summary>

Instala el SDK (`pip install -r requirements-mcp.txt`) y, con MEKA Core en marcha, añade el servidor a la configuración MCP de tu agente:

```json
{
  "mcpServers": {
    "meka": { "command": "python", "args": ["/ruta/a/PROJECT-MEKA/run.py", "mcp"] }
  }
}
```

O desde la terminal (usa siempre el **Python del entorno virtual**: `venv/Scripts/python.exe` en Windows, `venv/bin/python` en Linux/macOS):

```bash
claude mcp add meka -s local -- /ruta/a/PROJECT-MEKA/venv/Scripts/python.exe /ruta/a/PROJECT-MEKA/run.py mcp
gemini mcp add -s project meka /ruta/a/PROJECT-MEKA/venv/Scripts/python.exe /ruta/a/PROJECT-MEKA/run.py mcp
```

Comprueba la conexión con `claude mcp list` o `gemini mcp list` (debe decir *Connected*). Las herramientas que tocan la mascota o la memoria necesitan MEKA Core en marcha; si está apagado, responden con un error claro en lugar de romper la conexión.

| Herramienta | Qué hace |
|---|---|
| `pet_status` | Avisa a la mascota de que el agente empieza (`working`), termina (`done`) o falla (`error`) una tarea |
| `pet_emotion` | Cambia la expresión de la mascota |
| `chat` | Habla con el personaje (conversación propia, separada de Telegram) |
| `remember` · `memories` | Guarda y consulta la memoria del usuario (`memories` acepta un tema y busca por significado; nunca devuelve recuerdos privados) |
| `ask_permission` | Pide permiso antes de algo irreversible: la mascota muestra el diálogo y el agente espera tu respuesta (sin respuesta = no) |
| `list_folders` · `list_files` · `read_file` · `search_files` | Leen las carpetas que autorizaste en `hands.folders` (solo lectura; nunca las marcadas `private`) |

</details>

<details>
<summary><b>API REST de MEKA Core</b></summary>

Documentación interactiva en `http://127.0.0.1:8765/docs`. Si defines `MEKA_API_TOKEN`, todas las rutas salvo `/v1/health` piden `Authorization: Bearer <token>` (en el WebSocket, `?token=`).

| Ruta | Uso |
|---|---|
| `GET /v1/health` | Estado y personaje activo |
| `GET /v1/persona` | Nombre, frases y avatar del personaje (sin su prompt) |
| `POST /v1/chat` | Mensaje de texto → respuestas (con audio si llevan `[AUDIO]`) |
| `POST /v1/voice` | Nota de voz → transcripción y respuestas |
| `POST /v1/files` | Imagen o documento → análisis |
| `POST /v1/speech` · `GET /v1/audio/{id}` | Sintetizar un texto y descargar el audio (una sola vez) |
| `POST /v1/sessions/{id}/reset` | Olvidar la conversación reciente |
| `GET` · `POST` · `DELETE /v1/users/{id}/memories` | Ver (`?q=` busca por significado), añadir o borrar recuerdos |
| `POST /v1/events` · `WS /v1/events` | Publicar y recibir eventos de la mascota ([contrato](docs/VISION.md#contrato-de-eventos)) |

```bash
curl -s http://127.0.0.1:8765/v1/chat -H "Content-Type: application/json" \
  -d '{"session": "prueba", "user": "local", "text": "¡Hola!", "audio": false}'
```

</details>

## ⚙️ Configuración

Los secretos van en `.env` y todo lo demás en [`config.yml`](config.yml).

<details>
<summary><b>Referencia completa de <code>config.yml</code></b></summary>

| Clave | Por defecto | Descripción |
|---|---|---|
| `persona` | `dva` | Personaje activo: una carpeta de [`personas/`](personas/README.md). También con `MEKA_PERSONA` en `.env`. |
| `app.log_level` | `INFO` | `DEBUG`, `INFO`, `WARNING` o `ERROR`. |
| `app.log_conversations` | `true` | Muestra la conversación en la consola. |
| `server.host` / `server.port` | `127.0.0.1` / `8765` | Dónde escucha MEKA Core. Fuera de `127.0.0.1` exige `MEKA_API_TOKEN`. |
| `server.url` | `""` | Cómo encuentran los canales al núcleo si está en otro equipo (o `MEKA_CORE_URL`). |
| `server.allowed_origins` | `[]` | Webs extra que pueden conectarse; la mascota y `localhost` ya están permitidas. |
| `server.max_upload_mb` | `20` | Tamaño máximo de las notas de voz, imágenes y documentos. |
| `server.broadcast_messages` | `true` | La mascota también dice lo que MEKA responde por otros canales. |
| `paths.memory_db` / `paths.temp_dir` | `data/meka.db` / `temp` | Base de datos SQLite (recuerdos e historial) y archivos temporales. |
| `memory.remember_pattern` / `recall_triggers` | — | Frases que guardan y recuperan recuerdos. |
| `memory.persist_history` | `true` | El historial de cada chat sobrevive a los reinicios. |
| `memory.semantic.enabled` / `model` | `true` / `embeddinggemma` | Memoria por significado con embeddings de Ollama. Sin el modelo, busca solo por palabras. |
| `memory.semantic.min_similarity` / `auto_recall_similarity` | `0.35` / `0.6` | Similitud mínima al preguntar y para recordar sin que preguntes (`0` lo desactiva). Calíbralos con `python -m scripts.semantic_check`. |
| `ai.provider` | `ollama` | Cerebro de la conversación: `ollama`, `claude` o `gemini`. |
| `ai.vision_provider` / `ai.fallback_provider` | `""` | Cerebro para imágenes y cerebro de respaldo si el principal falla o se niega. |
| `ai.local_only` | `false` | `true` ignora los proveedores en la nube: nada sale del equipo. |
| `ai.routing.chat` / `vision` / `document` | `""` | Cerebro por tarea (vacío = `ai.provider`). |
| `ai.privacy.provider` | `ollama` | Cerebro local para lo privado. Lo privado **nunca** va a la nube, ni como respaldo; si no hay proveedor local, no se envía. |
| `ai.privacy.documents` / `detect_sensitive` | `true` / `true` | Documentos siempre privados; contraseñas, llaves de API, tokens, tarjetas o CURP vuelven privada la conversación hasta reiniciarla. Lo que pidas recordar en privado solo vuelve a prompts de proveedores locales y nunca sale por MCP ni Telegram. |
| `system.notifications.apps` / `blocked` / `hide_codes` | `["*"]` / `[]` / `true` | Notificaciones de Windows que ve la isla. Son privadas: nunca van a la nube ni al MCP, y los códigos de verificación se ocultan. |
| `tasks.morning_hour` | `9` | Las tareas de un día sin hora (*«el viernes»*) se avisan a esta hora; *«antes del 15»*, la mañana anterior. |
| `proactive.enabled` | `true` | **Hanna proactiva**: cada `check_seconds` (60) mira si toca un aviso (una consulta a SQLite, sin IA ni red). Los avisos que pediste llegan a su hora, también en modo concentración. |
| `proactive.digest_minutes` / `max_per_day` / `repeat_hours` | `120` / `6` / `4` | El resumen por su cuenta (vencidas, lo de hoy, cuántas notificaciones nuevas) sale como mucho cada 2 h, 6 al día, sin repetir lo mismo, y solo si hay algo que contar. |
| `proactive.remote` / `away_minutes` | `away` / `10` | **Avisos en el móvil (Telegram)**: con `away`, solo si no estás frente al equipo (la isla cerrada o 10 min sin tocar teclado ni ratón); `always` o `never`. Al móvil nunca van las tareas privadas ni las notificaciones de Windows. Llegan al primer ID de `ALLOWED_USER_IDS`, con botones *Hecho* y *Posponer*; `/tareas` lista lo pendiente. |
| `proactive.quiet_hours` / `idle_minutes` | `22:00–08:00` / `5` | Sin resúmenes de noche, en modo concentración, con el núcleo ocupado o si le hablaste hace menos de 5 min. De las notificaciones solo dice cuántas y de qué apps, nunca su texto. |
| `proactive.welcome_minutes` | `20` | **«Mientras no estabas…»**: al volver al equipo tras este tiempo sin tocarlo, Hanna te resume en una frase los avisos que sonaron, lo vencido y cuántas notificaciones llegaron (solo en la isla). `0` lo desactiva. |
| `system.media` | `true` | Lo que suena en cualquier reproductor de Windows, **con su carátula** (`GET /v1/system/media/artwork`, solo se lee al cambiar de canción y nunca sale del equipo). |
| Telegram en la isla | — | La isla muestra las notificaciones de **Telegram Desktop** si en Telegram activas *Ajustes → Notificaciones y sonidos → Usar notificaciones de Windows*. Con sus ventanas propias, Windows no las ve. |
| `focus.default_minutes` / `allow_apps` / `battery_alert` | `25` / `[]` / `15` | **Modo concentración**: retiene notificaciones, música y avisos de agentes; los permisos, los errores, las apps de `allow_apps` y la batería crítica pasan igual. Al terminar, resumen de lo que esperó. |
| `hands.folders` | `{}` | Carpetas que MEKA puede **leer** (nombre: ruta, o `{path, private}`). Fuera de ellas nada; `.env`, llaves, `.git` y similares nunca, aunque estén dentro. La escritura (`writable: true`, con permiso y deshacer) existe pero está **pospuesta** hasta aislar el sistema: no la actives todavía. |
| `ai.history_size` | `20` | Mensajes recientes que recuerda por chat. |
| `ai.providers.ollama.model` | `gemma3:12b` | Modelo de Ollama. Debe ser **multimodal** para ver fotos. |
| `ai.providers.ollama.keep_alive` | `0` | `0` descarga el modelo tras responder (ahorra RAM); `"5m"` lo mantiene cargado (más rápido). |
| `ai.providers.ollama.*` | — | `base_url`, `temperature`, `options` y `vision_options` de Ollama. |
| `ai.providers.claude.model` / `effort` | `claude-opus-5-5` / `low` | Modelo de Claude y cuánto piensa (`low` a `max`). Requiere `ANTHROPIC_API_KEY`. |
| `ai.providers.gemini.model` | `gemini-flash-latest` | Modelo de Gemini. Requiere `GEMINI_API_KEY`. |
| `stt.mode` | `auto` | `auto`: si el cerebro entiende audio, la nota de voz va tal cual y se omite la transcripción; `always`: transcribir siempre. |
| `ai.providers.<cerebro>.capabilities` | por cerebro | Lo que entiende de forma nativa: `text`, `vision`, `audio`, `pdf` (Ollama: texto e imagen · Claude: + PDF · Gemini: + audio y PDF). Corrígelo por modelo. MEKA usa la ruta nativa si existe y, si no o si falla, la clásica (transcribir, extraer texto). |
| `ai.providers.openai_compat` | — | Cualquier servidor compatible con OpenAI: **llama.cpp**, LM Studio, vLLM u Ollama (`/v1`). Solo cuenta como local si `base_url` es de este equipo. Úsalo como `ai.provider: openai_compat`. |
| `ai.privacy.audio_to_cloud` | `false` | Las notas de voz sin transcribir no pasan por el detector de datos sensibles: por defecto solo van a cerebros locales. |
| `stt.engine` / `fallback_engine` | `faster-whisper` / `whisper` | Motor de voz a texto y su respaldo. faster-whisper usa ~3 veces menos RAM con el mismo resultado. |
| `stt.model_size` | `base` | Whisper: `tiny`, `base`, `small`, `medium`, `large-v3`, `turbo`. |
| `stt.unload_after_use` | `true` | Libera Whisper de la RAM tras cada nota de voz. |
| `tts.engine` | `edge-tts` | `edge-tts`, `qwen-tts` o `piper`. La voz de edge-tts la pone cada personaje. |
| `tts.fallback_engine` | `""` | Motor de respaldo si falla el principal. |
| `tts.convert_to_ogg` | `true` | Convierte a OGG/Opus para que llegue como nota de voz. |
| `tts.qwen.ref_audio` / `ref_text` | — | Solo con Qwen3-TTS: tu propia voz (en `voices/`, ignorada por git) y su transcripción exacta. |
| `tts.qwen.device` | `cpu` | `cpu` o `cuda`. |
| `documents.max_chars` | `4000` | Caracteres de cada documento que se envían al modelo. |
| `telegram.enabled` | `true` | Arranca el bot con `python run.py`. |
| `telegram.typing_delay` | `1.0` | Multiplica las pausas de "escribiendo…"; `0` responde sin pausas. |
| `telegram.stickers` / `telegram.gifs` | `[]` | Stickers (`file_id`) y GIFs que el personaje puede enviar. Envíale un sticker y su `file_id` aparecerá en la consola. |
| `telegram.drop_pending_updates` | `false` | Ignora los mensajes recibidos con el bot apagado. |
| `mcp.session` / `mcp.user` | `mcp` / `""` | Conversación y memoria del canal MCP (vacío = el primer ID de `ALLOWED_USER_IDS`). |

</details>

<details>
<summary><b>¿Qué cerebro elijo?</b></summary>

| Cerebro | Privacidad | Costo | Para qué |
|---|---|---|---|
| **Ollama** (local) | Nada sale del equipo | Gratis; usa tu RAM/GPU | Por defecto. Conversación diaria y todo lo privado |
| **Claude** | El texto va a Anthropic | Por uso (`effort: low` lo abarata) | Respuestas de más calidad, documentos largos, visión |
| **Gemini** | El texto va a Google; en el nivel gratuito puede usarse para mejorar sus productos | Nivel gratuito disponible | Probar sin GPU, o como respaldo |

Ejemplos de `config.yml`:

```yaml
ai:
  provider: "claude"            # Charla con Claude...
  fallback_provider: "ollama"   # ...y si no hay internet o se niega, responde Ollama
```

```yaml
ai:
  provider: "ollama"            # Todo en local...
  vision_provider: "gemini"     # ...salvo las fotos, que analiza Gemini
```

Modelos de Ollama recomendados:

| Modelo | Descarga aprox. | Visión | Para quién |
|---|---|:---:|---|
| `gemma3:4b` | 3,3 GB | ✅ | Equipos modestos |
| `gemma3:12b` | 8,1 GB | ✅ | **Por defecto.** Buen equilibrio entre calidad y recursos |
| `gemma4:e4b-it-qat` | ~6 GB | ✅ | La generación más reciente de Gemma; [merece la pena probarla](docs/AUDITORIA.md#3-nuevas-versiones-y-viabilidad) |

La RAM necesaria es algo mayor que el tamaño de descarga. Consulta los tamaños actuales en [ollama.com/library](https://ollama.com/library).

</details>

<details>
<summary><b>🎙️ Gemma 4 con audio nativo (llama.cpp)</b></summary>

Gemma 4 (E2B, E4B, 12B) entiende audio de forma nativa, así que MEKA puede saltarse la transcripción
(`stt.mode: auto`). Ollama aún no le pasa el audio de forma fiable; **llama.cpp** sí, con su proyector
multimodal (`mmproj`, que `-hf` descarga solo). Probado con el build 12282 en Windows:

```bash
winget install ggml.llamacpp
llama-server -hf ggml-org/gemma-4-E2B-it-GGUF:Q4_0 --port 8080 -c 8192 --jinja
```

La primera vez descarga unos 3,5 GB. En el registro debe aparecer `init_audio` (el audio aún es
*experimental* en llama.cpp). Ese repositorio trae `Q4_0`, `Q8_0` y `BF16`, no `Q4_K_M`.

```yaml
ai:
  provider: "openai_compat"
  providers:
    openai_compat:
      base_url: "http://127.0.0.1:8080"
      model: "gemma-4-e2b"
      capabilities: [text, vision, audio]
      thinking: false      # Sin esto, Gemma 4 gasta los tokens razonando y la respuesta llega vacía
```

Medido en un equipo con 16 GB de RAM y solo CPU, con una nota de voz de 6 s: ~30 s la llamada
directa y ~70 s dentro de MEKA (el prompt del personaje y la memoria pesan). Sin GPU, E2B es la
opción más holgada; con GPU, prueba E4B.

> La ruta nativa responde a lo que oye, pero no hay texto que analizar: *«recuerda esto: …»* no se
> guarda como recuerdo ni se buscan recuerdos por palabras. Si los necesitas por voz, `stt.mode: always`.

</details>

## 🧠 Cómo funciona

```mermaid
flowchart LR
    U([Telegram]) <--> TG[channels/telegram]
    A([Claude · Gemini CLI · Cursor]) <-->|MCP stdio| MCP[channels/mcp]
    TG <-->|REST| API
    MCP <-->|REST| API
    PET([Mascota pet/]) <-->|WebSocket /v1/events| API
    subgraph CORE[MEKA Core · 127.0.0.1:8765]
        API[server/<br/>FastAPI · routes/ · token · origen] --> ENG[core/engine.py]
        ENG --> STT[ai/stt/<br/>faster-whisper · Whisper]
        ENG --> DOC[core/documents.py]
        ENG --> AI[ai/service.py]
        ENG --> TTS[ai/tts/<br/>Edge-TTS · Qwen3-TTS · Piper]
        ENG --> BUS((core/events.py))
        P[[personas/&lt;id&gt;]] -.-> ENG
        AI <-->|ai/providers| OL[(Ollama · Claude · Gemini)]
        AI <--> MEM[(core/memory.py<br/>SQLite data/meka.db)]
    end
    BUS -.->|emotion · message · agent.*| PET
```

- **Los canales no cargan modelos.** Telegram y MCP solo hablan con MEKA Core por HTTP; pueden ir en otro equipo.
- **Un modelo pesado a la vez.** Un `asyncio.Lock` en el núcleo impide que Whisper, el LLM y el TTS coincidan en memoria, venga la petición del canal que venga.
- **Sin bloqueos.** La inferencia corre en hilos aparte, así que el servidor sigue atendiendo mientras piensa.
- **Etiquetas de intención.** El modelo marca sus respuestas con `[AUDIO]`, `[STICKER]` o `[GIF]` y el bot decide cómo entregarlas.

<details>
<summary><b>🧰 Stack tecnológico</b></summary>

| Capa | Tecnología |
|---|---|
| Núcleo | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) (REST y WebSocket) · [httpx](https://www.python-httpx.org/) |
| Canales | [python-telegram-bot](https://python-telegram-bot.org/) 22 · [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) 2 |
| LLM y visión | [Ollama](https://ollama.com) + Gemma 3 · [Claude](https://platform.claude.com/docs) ([SDK](https://github.com/anthropics/anthropic-sdk-python)) · [Gemini](https://ai.google.dev/gemini-api/docs) ([google-genai](https://github.com/googleapis/python-genai)) |
| Memoria | SQLite + FTS5 + [sqlite-vec](https://github.com/asg017/sqlite-vec) · embeddings con `embeddinggemma` ([evaluación](docs/MEMORIA.md)) |
| Voz → texto | [openai-whisper](https://github.com/openai/whisper) |
| Texto → voz | [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) · [edge-tts](https://github.com/rany2/edge-tts) · [Piper](https://github.com/OHF-Voice/piper1-gpl) |
| Documentos | [PyMuPDF](https://pymupdf.readthedocs.io/) · [python-docx](https://python-docx.readthedocs.io/) · [openpyxl](https://openpyxl.readthedocs.io/) |
| Calidad | [pytest](https://pytest.org) · [Ruff](https://docs.astral.sh/ruff/) · GitHub Actions · Dependabot |

</details>

<details>
<summary><b>🗂️ Estructura del proyecto</b></summary>

```
PROJECT-MEKA/
├── run.py                  # Punto de entrada: all | core | telegram | mcp
├── server/                 # MEKA Core: app.py compone; routes/ (una por dominio), security.py
├── core/                   # Motor, eventos, configuración, memoria, documentos y personajes
├── ai/                     # Proveedores de IA (ai/providers), STT, TTS (ai/tts/), prompts y texto
├── channels/               # Clientes del núcleo: Telegram, MCP y el cliente HTTP común
├── personas/               # Paquetes de personaje (D.Va, Marin, Yotsuba...)
├── pet/                    # Mascota de escritorio (web + Go WebView2), prototipo
├── scripts/                # Diagnóstico y tablero de tareas (tareas.py + tablero/)
├── coordinacion/           # Tablero compartido Claude Code ↔ Antigravity
├── tests/                  # Tests automatizados (pytest)
├── docs/                   # Filosofía híbrida, visión, auditoría e imágenes
├── config.yml              # Configuración general
├── .env.example            # Plantilla de secretos
└── requirements*.txt       # Dependencias: base, nube, MCP, Whisper, Qwen3-TTS y desarrollo
```

Se generan al ejecutar o son personales (ignorados por git): `data/` (la base de datos), `temp/`, `logs/`, `models/` y `voices/`.

</details>

## 🔒 Privacidad y seguridad

- 🔑 Los **tokens** viven en `.env`, excluido de git. Nunca los subas al repositorio.
- 🏠 **MEKA Core solo escucha en este equipo** (`127.0.0.1`). Para abrirlo a tu red o a Tailscale hace falta `MEKA_API_TOKEN`; sin él, el servidor se niega a arrancar.
- 🌐 El servidor **rechaza webs ajenas**: una página cualquiera no puede usar tu MEKA desde el navegador. Solo la mascota, `localhost` y los orígenes de `server.allowed_origins`.
- 👤 **`ALLOWED_USER_IDS`** decide quién puede hablar con el bot.
- 🧱 El **historial** se separa por chat y los **recuerdos** por usuario: nadie puede leer lo que otra persona le contó al asistente.
- 🗑️ Las **fotos, documentos y notas de voz** se borran justo después de procesarse.
- 🏠 Con Ollama la inferencia es **local**. Si eliges Claude o Gemini, el texto (y las fotos) de la conversación va a su API; `ai.local_only: true` lo impide del todo, y `"private": true` (o un dato sensible detectado) lo impide para una conversación. `edge-tts` sintetiza la voz en los servidores de Microsoft.
- 🤐 Los errores internos no se muestran al usuario y los logs no incluyen el contenido de los mensajes (salvo con `app.log_conversations`).

> [!WARNING]
> **Clonación de voz:** usa como referencia tu propia voz o una para la que tengas permiso. Clonar la voz de actores o actrices reales puede vulnerar sus derechos.

## 🩺 Problemas frecuentes

<details>
<summary><b>«No se pudo conectar con Ollama»</b></summary>

Ejecuta `ollama serve` (o abre la app de Ollama) y comprueba que `ai.providers.ollama.base_url` apunta a él. Para diagnosticarlo: `python -m scripts.verify_ollama`.
</details>

<details>
<summary><b>«Ollama no tiene el modelo»</b></summary>

Descárgalo con `ollama pull <modelo>`, usando el mismo nombre que en `ai.providers.ollama.model`.
</details>

<details>
<summary><b>No entiende mis notas de voz o sus audios llegan como archivo</b></summary>

Falta FFmpeg en el `PATH`. Instálalo (`winget install ffmpeg`, `brew install ffmpeg` o `sudo apt install ffmpeg`) y reinicia la terminal.
</details>

<details>
<summary><b>«Dependencias de Qwen-TTS faltantes»</b></summary>

Instálalas con `pip install -r requirements-qwen.txt` o cambia `tts.engine` a `edge-tts`. Mientras tanto, el bot usa el motor de respaldo (`tts.fallback_engine`).
</details>

<details>
<summary><b>Mi equipo se queda sin memoria</b></summary>

Usa un modelo más pequeño (`gemma3:4b`), `stt.model_size: tiny` y `tts.engine: edge-tts`. Mantén `ai.providers.ollama.keep_alive: 0` y las opciones `unload_after_use: true`.
</details>

<details>
<summary><b>«MEKA Core no responde en http://127.0.0.1:8765»</b></summary>

El canal no encuentra el núcleo. Arráncalo con `python run.py core` (o usa `python run.py`, que lanza los dos). Si está en otro equipo, pon su dirección en `server.url` o en `MEKA_CORE_URL`, y el mismo `MEKA_API_TOKEN` en ambos.
</details>

<details>
<summary><b>Herramientas de diagnóstico</b></summary>

```bash
python -m scripts.verify_ollama            # Conexión con Ollama y prueba de respuesta
python -m scripts.tts_smoke_test "Hola"    # Genera un audio con el motor de voz configurado
python -m scripts.list_edge_voices es-MX   # Voces disponibles en edge-tts
python -m scripts.semantic_check "¿qué te conté de mi mascota?"   # Similitudes de la memoria semántica
```

</details>

## 🗺️ Hoja de ruta

- [x] IA local con Ollama, voz (STT/TTS), visión y documentos
- [x] Memoria persistente por usuario y control de acceso
- [x] Tests automatizados, CI y auditoría técnica ([v1.1.0](CHANGELOG.md))
- [x] Prototipo de **mascota de escritorio** tipo Tamagotchi ([`pet/`](pet/README.md))
- [x] **Personajes intercambiables** independientes del modelo de IA ([`personas/`](personas/README.md))
- [x] **Cerebro intercambiable**: Ollama, Claude y Gemini, con enrutamiento por tarea, respaldo y modo `local_only`
- [x] **Memoria en SQLite** con búsqueda de texto completo e historial persistente ([evaluación](docs/MEMORIA.md))
- [x] **Memoria semántica**: recordar por significado con embeddings locales y `sqlite-vec`
- [x] **MEKA Core como servicio**: servidor local REST + WebSocket con Telegram, MCP y la mascota como clientes
- [ ] Probar la personalidad con Gemini para Home y con Home Assistant (iteraciones 0 y 1)
- [ ] Base del Funko del Meka (ESP32-S3, luces, sensor táctil) y caja de holograma ([planos](https://claude.ai/artifact/TVgmmCCLpmyd2KxQCpEEki))
- [ ] Google Drive como memoria documental compartida con otros agentes
- [ ] Gestionar carpetas autorizadas desde el móvil, con confirmación y git
- [ ] Compañera de productividad: tarjetas tipo Brief, modo concentración y resumen del día (sin mecánicas de cuidado: MEKA ayuda, no distrae)
- [ ] App móvil: Android con burbuja flotante, iOS con widget
- [x] Transcripción más ligera con [faster-whisper](https://github.com/SYSTRAN/faster-whisper)

La dirección del proyecto está en la [filosofía híbrida](docs/FILOSOFIA_HIBRIDA.md) y la [visión](docs/VISION.md); las alternativas técnicas evaluadas, en la [auditoría](docs/AUDITORIA.md).

## 🧪 Desarrollo

```bash
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest
```

Pruebas de la API real con Postman (con MEKA Core en marcha): ver [`tests/postman/`](tests/postman/README.md).

¿Quieres contribuir? Lee [CONTRIBUTING.md](CONTRIBUTING.md) y abre un [issue](https://github.com/Nekimu/PROJECT-MEKA/issues/new/choose). Los cambios de cada versión están en el [CHANGELOG](CHANGELOG.md).

## 📸 Capturas

La Dynamic Island en Windows (ventana de 380×480, datos de demostración):

| Recogida | Con música | Hana |
|:---:|:---:|:---:|
| ![Isla recogida](docs/screenshots/isla-recogida.jpg) | ![Isla con música](docs/screenshots/isla-musica.jpg) | ![Hana en el hero](docs/screenshots/hero.jpg) |

| Música con carátula | Notificaciones y tareas | Aviso de Hanna |
|:---:|:---:|:---:|
| ![Tarjeta de música](docs/screenshots/tarjeta-musica.jpg) | ![Notificaciones](docs/screenshots/notificaciones.jpg) | ![Aviso proactivo](docs/screenshots/aviso-proactivo.jpg) |

## 📄 Licencia y créditos

Código distribuido bajo la licencia [MIT](LICENSE). Las dependencias conservan sus propias licencias; ten en cuenta que **PyMuPDF** es AGPL-3.0 y **python-telegram-bot** es LGPL-3.0.

Los personajes son interpretaciones originales inspiradas en obras de terceros: D.Va y *Overwatch* pertenecen a Blizzard Entertainment; Marin Kitagawa y *Sono Bisque Doll wa Koi wo Suru*, a Shinichi Fukuda y SQUARE ENIX; Yotsuba Nakano y *Go-Tōbun no Hanayome*, a Negi Haruba y Kodansha. Gracias a los equipos de [Ollama](https://ollama.com), [Whisper](https://github.com/openai/whisper), [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) y [python-telegram-bot](https://python-telegram-bot.org/).

<div align="center">
<sub>Hecho con 💖 por <a href="https://github.com/Nekimu">Nekimu</a></sub>
</div>
