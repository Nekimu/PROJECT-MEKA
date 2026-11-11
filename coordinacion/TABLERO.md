# Tablero de tareas — Project MEKA

> ⚠️ **Archivo generado automáticamente.** No lo edites a mano: usa `python scripts/tareas.py` (ver [README](README.md)). Fuente: `tareas.json`.

_Última actualización: 2026-11-11T10:03:24-06:00_

## Resumen

| Agente | Rol | ⬜ pendiente | 🔄 en_progreso | ⛔ bloqueada | 👀 en_revision | ✅ hecha |
|---|---|---|---|---|---|---|
| **Claude Code** | Backend, IA, agente y canales | 7 | 0 | 0 | 1 | 15 |
| **Antigravity (Gemini)** | Frontend, UI/UX y arte | 2 | 0 | 0 | 1 | 12 |

## Claude Code

| ID | Estado | Prioridad | Tarea | Depende de | Actualizada |
|---|---|---|---|---|---|
| T-002 | 👀 en_revision | alta | Tablero compartido de tareas y protección de áreas (este sistema) | — | 2026-11-09 19:26 |
| T-004 | ⬜ pendiente | alta | Fase 3 · Manos (solo lectura): carpetas autorizadas, listar, leer y buscar | — | 2026-11-09 19:30 |
| T-005 | ⬜ pendiente | media | Fase 3 · Manos (escritura): punto de restauración git + confirmación + deshacer | T-003, T-004 | 2026-11-09 19:30 |
| T-006 | ⬜ pendiente | media | Estado de la mascota en el núcleo: GET/PUT /v1/pet/state persistido en SQLite | — | 2026-11-09 19:30 |
| T-008 | ⬜ pendiente | media | STT más rápido con faster-whisper (motor opcional, respaldo openai-whisper) | T-001 | 2026-11-09 19:30 |
| T-009 | ⬜ pendiente | baja | Configuración tipada y validada al arrancar (pydantic) | — | 2026-11-09 19:30 |
| T-010 | ⬜ pendiente | baja | Presupuesto de API en la nube y evento budget.low | — | 2026-11-09 19:30 |
| T-032 | ⬜ pendiente | baja | Telegram: comando /privado para activar el modo privado de la conversación | — | 2026-11-09 22:13 |
| T-001 | ✅ hecha | alta | Entorno local de backend: Python 3.12, venv, dependencias, lint y tests | — | 2026-11-09 20:57 |
| T-003 | ✅ hecha | alta | Confirmación de acciones: agent.confirm con id y user.confirm en el WebSocket | — | 2026-11-11 09:23 |
| T-015 | ✅ hecha | alta | Modularidad: dividir server/app.py en routers (seguridad, esquemas, rutas por dominio) | — | 2026-11-09 21:03 |
| T-016 | ✅ hecha | alta | Modularidad: motores TTS como paquete con interfaz común (edge, piper, qwen) | — | 2026-11-09 21:04 |
| T-019 | ✅ hecha | alta | Filosofía 5.3: enrutamiento por tarea y privacidad (documentos/sensibles a local) | — | 2026-11-09 22:13 |
| T-020 | ✅ hecha | alta | Filosofía 5.1/8: respuesta normalizada del proveedor (texto, modelo, uso) y registro de ejecución sin contenido | — | 2026-11-09 22:03 |
| T-026 | ✅ hecha | alta | Pruebas del canal MCP con clientes reales (SDK stdio, Claude Code, Gemini CLI) | — | 2026-11-09 21:44 |
| T-028 | ✅ hecha | alta | Bug: emojis en la consola de Windows con salida redirigida daban HTTP 500 en /v1/chat | — | 2026-11-09 22:03 |
| T-031 | ✅ hecha | alta | Privacidad de la memoria larga: recuerdos guardados en una conversación privada no deben ir a prompts en la nube | — | 2026-11-09 22:21 |
| T-007 | ✅ hecha | media | Contrato publicado y versionado: GET /v1/contract (eventos, emociones, versión) | — | 2026-11-11 09:34 |
| T-017 | ✅ hecha | media | Modularidad: extraer almacén de audios del motor e historial de conversación del servicio de IA | — | 2026-11-09 21:09 |
| T-018 | ✅ hecha | media | Guardia de tamaño: test que falla si un módulo del backend supera 300 líneas | T-015, T-016, T-017 | 2026-11-09 21:09 |
| T-021 | ✅ hecha | media | Filosofía 5.2: eventos normalizados para el avatar (error y fin de respuesta) | — | 2026-11-09 22:03 |
| T-029 | ✅ hecha | media | Modularidad: core/engine.py está en 290 líneas (límite 300); separar análisis de archivos y voz | — | 2026-11-09 22:11 |
| T-037 | ✅ hecha | media | Pruebas de la API con Postman CLI (colección generada + entorno local) | — | 2026-11-11 09:42 |

## Antigravity (Gemini)

| ID | Estado | Prioridad | Tarea | Depende de | Actualizada |
|---|---|---|---|---|---|
| T-034 | ⬜ pendiente | alta | Diálogo de permisos: usar timeout del evento, cerrar con agent.confirmed y pedir pendientes al conectar | — | 2026-11-11 09:23 |
| T-011 | 👀 en_revision | media | (Propuesta) UI de confirmación en la mascota para agent.confirm / user.confirm | T-003 | 2026-11-09 19:30 |
| T-036 | ⬜ pendiente | media | App Go/web: leer eventos y emociones de GET /v1/contract y avisar si la versión mayor no coincide | — | 2026-11-11 09:34 |
| T-013 | ✅ hecha | alta | Rediseño visual del escenario de la mascota y HUD Tamagotchi (glassmorphism, animaciones y menú contextual) | — | 2026-11-09 19:30 |
| T-014 | ✅ hecha | alta | Dashboard de control y simulador en navegador (tema oscuro/claro, log de eventos, selector visual de skins y estado Core) | — | 2026-11-09 19:30 |
| T-022 | ✅ hecha | alta | Integración de assets Pixel Art animados (Hana y Clawd), herramienta pixelize.py y GUI minimalista estilo Apple con ventana emergente | — | 2026-11-09 21:14 |
| T-025 | ✅ hecha | alta | Decisión: mascota de escritorio en Go con Wails v2 (reemplaza a Tauri y al prototipo Tkinter) | — | 2026-11-09 21:39 |
| T-033 | ✅ hecha | alta | Corrección de fondo blanco en ventana Win32/DWM, bocadillo de diálogo no intrusivo y animaciones squash & stretch | — | 2026-11-09 22:31 |
| T-035 | ✅ hecha | alta | Notch superior centrado estilo Apple Dynamic Island con negro profundo, retroiluminación morada tenue y despliegue elástico | — | 2026-11-11 09:31 |
| T-038 | ✅ hecha | alta | Dynamic Island: despliegue solo por clic, iluminacion/animacion al hover y auto-evasion de Snipping Tool | — | 2026-11-11 10:03 |
| T-023 | ✅ hecha | media | Lint: RUF002 (signo × ambiguo) en pet/tools/pixelize.py rompe ruff check . del CI | — | 2026-11-09 21:39 |
| T-024 | ✅ hecha | media | App de escritorio nativa en Python (ventana transparente sin bordes + Pixel Art + Drawer) | — | 2026-11-09 21:24 |
| T-027 | ✅ hecha | media | Ventana fija no redimensionable, flotante (Always on Top), fondo transparente nativo en Go y animaciones mejoradas | — | 2026-11-09 21:56 |
| T-030 | ✅ hecha | media | Crear skill de Golang, corregir errores de UI (Drawer, arrastre, capturas) y sincronizar documentacion | — | 2026-11-09 22:09 |
| T-012 | ✅ hecha | baja | (Propuesta) Sincronizar el Tamagotchi con /v1/pet/state | T-006 | 2026-11-09 21:14 |

## Detalle

### T-001 · Entorno local de backend: Python 3.12, venv, dependencias, lint y tests

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Python 3.12 (el proyecto soporta 3.11-3.13), PyTorch CPU (sin GPU NVIDIA), requirements-dev.txt, `ruff check .` y `pytest` en verde. Pendiente fuera de pip: Ollama (+ gemma3:12b y embeddinggemma) y FFmpeg.

**Última nota (claude):** FFmpeg 9.0.2 y Ollama 0.40.15 instalados; modelos gemma3:270m (pruebas) y embeddinggemma. config_local.yml (ignorado por git) soportado en core/config.py. 144 tests OK.

### T-002 · Tablero compartido de tareas y protección de áreas (este sistema)

**Responsable:** Claude Code · **Estado:** 👀 en_revision · **Prioridad:** alta

`coordinacion/` + `scripts/tareas.py`, hooks de git (commit-msg y post-commit) y hooks de Claude Code (SessionStart, PreToolUse, Stop).

**Archivos:** `scripts/tareas.py`, `coordinacion/**`, `.githooks/**`, `.claude/settings.json`

**Última nota (claude):** Listo; hooks de Claude Code activos desde la próxima sesión. Sin commit todavía.

### T-003 · Confirmación de acciones: agent.confirm con id y user.confirm en el WebSocket

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Registro de confirmaciones pendientes en MEKA Core: `agent.confirm` pasa a llevar `{id, action, expires_at}`; el cliente responde `user.confirm {id, approved}` por WebSocket o `POST /v1/confirmations/{id}` (para Telegram/móvil). Caducidad configurable y evento de resultado. Cambio de contrato ADITIVO: se avisa en coordinacion/README.md antes de publicarlo.

**Archivos:** `core/events.py`, `core/engine.py`, `server/app.py`, `tests/test_server.py`

**Última nota (claude):** core/confirmations.py (registro con caducidad: sin respuesta = no), evento agent.confirmed, user.confirm por WebSocket, GET/POST /v1/confirmations, herramienta MCP ask_permission. Probado en real: agente MCP pide permiso y la mascota (WebSocket) aprueba/rechaza. Contrato en coordinacion/README.md.

### T-004 · Fase 3 · Manos (solo lectura): carpetas autorizadas, listar, leer y buscar

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** alta

`hands.folders` en config.yml; nada fuera de ellas (resolución de rutas, sin symlinks que escapen). API `/v1/workspace/...` y herramientas MCP. Emite `agent.working`/`agent.done`/`agent.error` para que la mascota reaccione. Registro de cada acción.

**Archivos:** `core/**`, `server/app.py`, `channels/mcp/**`, `config.yml`, `tests/**`

**Última nota (claude):** creada

### T-005 · Fase 3 · Manos (escritura): punto de restauración git + confirmación + deshacer

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** media

Antes de mover/renombrar/borrar: commit de restauración en la carpeta autorizada, `agent.confirm` (T-003) y operación `undo`.

**Archivos:** `core/**`, `server/app.py`, `tests/**`

**Depende de:** T-003, T-004

**Última nota (claude):** creada

### T-006 · Estado de la mascota en el núcleo: GET/PUT /v1/pet/state persistido en SQLite

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** media

Guardar energía, saciedad, ánimo, afecto y desbloqueos en el Core para que escritorio, móvil y Telegram compartan la misma mascota. Las reglas del Tamagotchi siguen en el frontend; el Core solo almacena y difunde un evento `pet.state` (nuevo, aditivo).

**Archivos:** `core/memory.py`, `server/app.py`, `core/events.py`, `tests/**`

**Última nota (claude):** creada

### T-007 · Contrato publicado y versionado: GET /v1/contract (eventos, emociones, versión)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

El frontend puede leer en tiempo de ejecución los eventos y emociones válidos (`OUTBOUND_EVENTS`, `EMOTIONS`, eventos de entrada) y la versión del contrato, en lugar de duplicarlos a mano. Test que falle si cambia el contrato sin subir la versión.

**Archivos:** `server/app.py`, `core/events.py`, `tests/test_server.py`

**Última nota (claude):** core/contract.py fuente única (versión 1.4, campos y tipos de cada evento, historial); GET /v1/contract público con rutas REST generadas desde los routers; /v1/health incluye contract; POST /v1/events valida campos; test con huella que obliga a subir la versión (probado con mutación) y test de que todo evento emitido cumple el contrato.

### T-008 · STT más rápido con faster-whisper (motor opcional, respaldo openai-whisper)

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** media

Notas de voz 2-4x más rápidas en CPU (punto 3 de la auditoría). `stt.engine` en config.yml.

**Archivos:** `ai/stt.py`, `config.yml`, `tests/**`

**Depende de:** T-001

**Última nota (claude):** creada

### T-009 · Configuración tipada y validada al arrancar (pydantic)

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** baja

Errores de config.yml detectados al iniciar con mensajes claros (punto 6 de la auditoría). pydantic ya llega como dependencia.

**Archivos:** `core/config.py`, `tests/test_config.py`

**Última nota (claude):** creada

### T-010 · Presupuesto de API en la nube y evento budget.low

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** baja

Contar tokens/coste de Claude y Gemini por mes, límite en config.yml y emitir `budget.low` (ya está en el contrato, pero nadie lo publica todavía).

**Archivos:** `ai/**`, `core/engine.py`, `config.yml`, `tests/**`

**Última nota (claude):** creada

### T-011 · (Propuesta) UI de confirmación en la mascota para agent.confirm / user.confirm

**Responsable:** Antigravity (Gemini) · **Estado:** 👀 en_revision · **Prioridad:** media

Propuesta de Claude Code como contraparte de T-003: diálogo Aprobar/Rechazar en la mascota que envía `user.confirm {id, approved}`. Antigravity puede aceptarla, cambiarla o descartarla.

**Archivos:** `pet/web/**`

**Depende de:** T-003

**Última nota (antigravity):** UI de confirmación Aprobar/Rechazar lista en el bocadillo (envía user.confirm {id, approved}); lista para integrarse cuando T-003 esté en Core

### T-012 · (Propuesta) Sincronizar el Tamagotchi con /v1/pet/state

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** baja

Propuesta de Claude Code como contraparte de T-006: la mascota lee/guarda su estado en el Core (con almacenamiento local como respaldo sin conexión).

**Archivos:** `pet/web/**`

**Depende de:** T-006

**Última nota (antigravity):** Se omitió la mecánica de estado vital/hambre por decisión de diseño (enfoque Soul-of-Waifu + FILOSOFIA_HIBRIDA.md: avatares intercambiables sin mecánicas punitivas)

### T-013 · Rediseño visual del escenario de la mascota y HUD Tamagotchi (glassmorphism, animaciones y menú contextual)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Renovación visual completa de la mascota (bocadillo anime con estado, barras HUD con gradientes y glow, menú contextual moderno con iconos, input de chat estilizado y ciclo visual día/noche).

**Archivos:** `pet/web/index.html`, `pet/web/pet.css`, `pet/web/pet.js`

**Última nota (antigravity):** Escenario rediseñado con aura reactiva por estado, cabecera HUD, dock de acciones rápidas y transiciones suaves (@starting-style + allow-discrete)

### T-014 · Dashboard de control y simulador en navegador (tema oscuro/claro, log de eventos, selector visual de skins y estado Core)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Transformar el panel lateral del navegador en un Dashboard moderno con tarjetas de skins desbloqueables, consola de eventos en tiempo real, estado de conexión con /v1/health y /v1/persona, y controles Tamagotchi.

**Archivos:** `pet/web/index.html`, `pet/web/pet.css`, `pet/web/pet.js`

**Última nota (antigravity):** Panel Studio rediseñado con selector visual de skins, tema claro/oscuro, barras de estadísticas, inspector /v1/health y consola de eventos en vivo

### T-015 · Modularidad: dividir server/app.py en routers (seguridad, esquemas, rutas por dominio)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

server/app.py (397 líneas) concentra seguridad, modelos, 15 rutas y el WebSocket en un solo create_app. T-003, T-004, T-006 y T-007 añaden rutas aquí: se divide antes. Sin cambios de contrato.

**Archivos:** `server/**`, `tests/test_server.py`

**Última nota (claude):** server/ dividido en app, security, schemas, deps y routes/ (status, conversation, voice, memory, events). Mismas rutas (comparado el OpenAPI).

### T-016 · Modularidad: motores TTS como paquete con interfaz común (edge, piper, qwen)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

ai/tts.py (315 líneas) mezcla 3 motores, la conversión a OGG y el respaldo. Interfaz TTSEngine (pendiente de la auditoría) y un módulo por motor: añadir uno nuevo no toca los demás.

**Archivos:** `ai/tts.py`, `ai/tts/**`, `tests/test_tts.py`

**Última nota (claude):** ai/tts/ con interfaz TTSEngine (base.py), un módulo por motor (edge, piper, qwen), audio.py (OGG) y service.py (respaldo).

### T-017 · Modularidad: extraer almacén de audios del motor e historial de conversación del servicio de IA

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

MekaEngine y AIService tienen responsabilidades secundarias (audios temporales, historial) que crecerán con T-003/T-005.

**Archivos:** `core/engine.py`, `core/audio_store.py`, `ai/service.py`, `core/history.py`

**Última nota (claude):** core/audio_store.py (AudioStore) y core/history.py (ConversationStore). Además core/memory.py dividido: core/textsearch.py y core/legacy_import.py.

### T-018 · Guardia de tamaño: test que falla si un módulo del backend supera 300 líneas

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `tests/test_modularidad.py`

**Depende de:** T-015, T-016, T-017

**Última nota (claude):** tests/test_modularidad.py: máx. 300 líneas en core, ai, server, channels, scripts y run.py. scripts/tareas.py dividido en scripts/tablero/.

### T-019 · Filosofía 5.3: enrutamiento por tarea y privacidad (documentos/sensibles a local)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Hoy solo hay ai.local_only global. Falta: proveedor por tarea (chat, visión, documentos) y marca 'privado' por petición que obligue a un proveedor local, como pide la tabla de enrutamiento.

**Archivos:** `ai/**`, `core/engine.py`, `config.yml`, `tests/**`

**Última nota (claude):** ai/routing.py (cerebro por tarea; lo privado solo local, nunca de respaldo en la nube), ai/privacy.py (credenciales, llaves, JWT, tarjetas con Luhn, CURP), privacidad persistente por sesión en SQLite hasta el reset, documentos privados por defecto, 'private' en API y WebSocket. 22 tests + prueba real.

### T-020 · Filosofía 5.1/8: respuesta normalizada del proveedor (texto, modelo, uso) y registro de ejecución sin contenido

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Provider.chat devuelve solo texto. Normalizar a ProviderResult(text, provider, model, tokens, latency) y guardar en SQLite proveedor, modelo, hora, tarea y resultado SIN el texto de la conversación. Base de T-010 (budget.low).

**Archivos:** `ai/providers/**`, `ai/service.py`, `core/**`, `tests/**`

**Última nota (claude):** ProviderReply (texto + tokens) en Ollama, Claude y Gemini; Answer con ok/proveedor/modelo/latencia; core/runs.py (tabla runs sin contenido, máx. 5000) y GET /v1/runs. Probado con Ollama real.

### T-021 · Filosofía 5.2: eventos normalizados para el avatar (error y fin de respuesta)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

Si el cerebro falla, la mascota no se entera (solo se publica thinking y message). Publicar emotion=error / agent.error al fallar y volver a idle al terminar. Cambio aditivo del contrato: avisar a Antigravity.

**Archivos:** `core/engine.py`, `core/events.py`, `tests/**`

**Última nota (claude):** message con emotion=error si el cerebro falla; emotion=error si el núcleo revienta; sad si no entiende el audio. Avisado en coordinacion/README.md (contrato).

### T-022 · Integración de assets Pixel Art animados (Hana y Clawd), herramienta pixelize.py y GUI minimalista estilo Apple con ventana emergente

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Migración de animaciones a WebP Pixel Art nativos ultraligeros (3-6 KB) desde Stickers e Imagenes, rediseño minimalista estilo macOS/Apple con lanzamiento en popup transparente y conexión automática con el agente.

**Archivos:** `pet/web/index.html`, `pet/web/pet.css`, `pet/web/pet.js`, `pet/web/skins/manifest.js`, `pet/web/skins/dva_pixel/**`, `pet/web/skins/clawd_pixel/**`, `pet/tools/pixelize.py`

**Última nota (antigravity):** Implementada barra lateral oculta desplegable (Navigation Drawer) estilo Soul-of-Waifu + Apple Minimalist, eliminando barras de estado vital y dejando todos los avatares desbloqueados e intercambiables

### T-023 · Lint: RUF002 (signo × ambiguo) en pet/tools/pixelize.py rompe ruff check . del CI

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

Aviso de Claude Code: ruff marca 4 RUF002 en el docstring (64×64, 256×256, 512×512). Cambiar × por x o añadir # noqa: RUF002. El CI ejecuta ruff check . sobre todo el repo.

**Archivos:** `pet/tools/pixelize.py`

**Última nota (antigravity):** Corregidos caracteres RUF002 en el docstring de pet/tools/pixelize.py (ruff check en verde)

### T-024 · App de escritorio nativa en Python (ventana transparente sin bordes + Pixel Art + Drawer)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `pet/tools/desktop.py`, `pet/README.md`

**Última nota (antigravity):** Implementado pet/tools/desktop.py (Tkinter + Pillow + WebSockets) con ventana sin bordes transparente, Pixel Art 64x64 escalado NEAREST, Dynamic Island, confirmaciones agent.confirm y cajón lateral de personajes

### T-025 · Decisión: mascota de escritorio en Go con Wails v2 (reemplaza a Tauri y al prototipo Tkinter)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

El usuario eligió Go. Entorno listo en este equipo: Go 1.27.3, Wails CLI v2.17.1, WebView2 y Node/npm (wails doctor: OK). Wails reutiliza pet/web tal cual (HTML/CSS/JS) dentro de una ventana Frameless + AlwaysOnTop con transparencia (BackgroundColour RGBA 0,0,0,0 y en Windows WebviewIsTransparent + WindowIsTranslucent). Por definir: carpeta del proyecto Go (p. ej. pet/desktop/) y añadirla al área de Antigravity en coordinacion/tareas.json; qué hacer con pet/src-tauri y pet/tools/desktop.py. El backend no cambia: misma conexión WebSocket a /v1/events.

**Última nota (antigravity):** Implementado cliente de escritorio nativo en Go (pet/desktop/) con WebView2 transparente sin bordes, puente JS (mekaStartDrag, mekaSetDrawerExpanded, mekaCloseWindow), pruebas go test en verde y binario meka-desktop.exe. Eliminados pet/src-tauri y pet/tools/desktop.py

### T-026 · Pruebas del canal MCP con clientes reales (SDK stdio, Claude Code, Gemini CLI)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `run.py`, `tests/test_mcp.py`, `README.md`

**Última nota (claude):** 5 herramientas OK por stdio contra MEKA Core real; la mascota (WebSocket) recibe los eventos. Claude Code 2.x y Gemini CLI 0.62: Connected. Corregido: un log al importar core.config se colaba en stdout y rompía el JSON-RPC (test de regresión).

### T-027 · Ventana fija no redimensionable, flotante (Always on Top), fondo transparente nativo en Go y animaciones mejoradas

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `pet/desktop/window_windows.go`, `pet/desktop/main.go`, `pet/desktop/main_test.go`, `pet/web/pet.css`, `pet/web/pet.js`, `pet/README.md`

**Última nota (antigravity):** Configurada ventana fija 300x390 no redimensionable (HintFixed + WS_POPUP), AlwaysOnTop persistente con reafirmación en drag, fondo 100% transparente en WebView2 con ICoreWebView2Controller2::PutDefaultBackgroundColor y DWM, sombreado dinámico reactivo, squash/stretch y tacto al clic

### T-028 · Bug: emojis en la consola de Windows con salida redirigida daban HTTP 500 en /v1/chat

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `core/logger.py`, `tests/test_text_utils.py`

**Última nota (claude):** UnicodeEncodeError (cp1252) en log_conversation. Consola tolerante (backslashreplace) y log_conversation nunca rompe una respuesta. Test de regresión.

### T-029 · Modularidad: core/engine.py está en 290 líneas (límite 300); separar análisis de archivos y voz

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `core/**`, `tests/**`

**Última nota (claude):** core/engine.py 290 -> 179 líneas: core/media.py (voz, archivos, audios) y core/replies.py (Reply, UnsupportedFileError).

### T-030 · Crear skill de Golang, corregir errores de UI (Drawer, arrastre, capturas) y sincronizar documentacion

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `pet/desktop/window_windows.go`, `pet/desktop/main_test.go`, `pet/web/index.html`, `pet/web/pet.js`, `pet/web/pet.css`, `pet/README.md`, `docs/VISION.md`, `docs/FILOSOFIA_HIBRIDA.md`, `README.md`, `CHANGELOG.md`

**Última nota (antigravity):** Creado skill golang en ~/.gemini/config/skills/golang/SKILL.md. Corregidos bugs de UI: Drawer simplificado con transicion popover sin cierres accidentales de IntersectionObserver, arrastre Dynamic Island con stageTop y liberacion de puntero, tarjetas de avatares en columna unica, DataPath persistente en WebView2, y documentacion sincronizada sin referencias legadas a Tauri

### T-031 · Privacidad de la memoria larga: recuerdos guardados en una conversación privada no deben ir a prompts en la nube

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Hoy la privacidad cubre la petición y el historial, pero un 'recuerda esto' dicho en modo privado se guarda como recuerdo normal y puede añadirse después al prompt de Claude/Gemini. Marcar recuerdos como privados y filtrarlos cuando el proveedor no es local.

**Archivos:** `core/memory.py`, `ai/service.py`, `core/semantic.py`, `tests/**`

**Última nota (claude):** facts.private (migración automática, probada con la base real; respaldo en %TEMP%). Recuerdos privados solo en prompts cuando todos los proveedores (respaldo incluido) son locales; MCP y Telegram nunca los reciben (include_private=false). ai/recall.py separado (service.py 244 líneas) y core/memory_sessions.py (memory.py 264). 7 tests nuevos.

### T-032 · Telegram: comando /privado para activar el modo privado de la conversación

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** baja

**Archivos:** `channels/telegram/**`, `tests/test_telegram.py`

**Última nota (claude):** creada

### T-033 · Corrección de fondo blanco en ventana Win32/DWM, bocadillo de diálogo no intrusivo y animaciones squash & stretch

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `pet/desktop/window_windows.go`, `pet/web/pet.css`, `pet/web/pet.js`

**Última nota (antigravity):** pet(desktop+web): transparencia DWM sin fondo blanco, clamp en bocadillo y animaciones squash & stretch

### T-034 · Diálogo de permisos: usar timeout del evento, cerrar con agent.confirmed y pedir pendientes al conectar

**Responsable:** Antigravity (Gemini) · **Estado:** ⬜ pendiente · **Prioridad:** alta

Aviso de Claude Code: T-003 ya está en el Core. agent.confirm trae {id, action, timeout, expires_at, details?}; hoy pet.js cierra el diálogo a los 25 s fijos aunque el Core espera 'timeout'. Nuevo evento agent.confirmed {id, approved, by} para cerrar el diálogo si se resolvió en otro cliente o caducó (by: timeout). Al conectar: GET /v1/confirmations. user.confirm no cambia. Además: .gitignore actualizado por Claude: *.exe (meka-desktop.exe) y .gemini/ quedan fuera del repo; se quitaron las líneas de pet/src-tauri.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (claude):** creada

### T-035 · Notch superior centrado estilo Apple Dynamic Island con negro profundo, retroiluminación morada tenue y despliegue elástico

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `pet/desktop/main.go`, `pet/desktop/window_windows.go`, `pet/desktop/main_test.go`, `pet/web/index.html`, `pet/web/pet.css`, `pet/web/pet.js`, `pet/README.md`

**Última nota (antigravity):** pet(desktop+web): notch superior estilo Apple Dynamic Island en negro profundo, aura tenue morada y despliegue elástico hacia abajo

### T-036 · App Go/web: leer eventos y emociones de GET /v1/contract y avisar si la versión mayor no coincide

**Responsable:** Antigravity (Gemini) · **Estado:** ⬜ pendiente · **Prioridad:** media

Aviso de Claude Code (T-007): GET /v1/contract es público y devuelve version (1.4), events.outbound/inbound con campos y tipos, emotions y rest. /v1/health trae contract. Sugerencia: al conectar, si la versión mayor difiere, mostrar aviso en vez de fallar en silencio.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (claude):** creada

### T-037 · Pruebas de la API con Postman CLI (colección generada + entorno local)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `tests/postman/**`, `README.md`

**Última nota (claude):** postman-cli 1.87 instalado (npm -g). tests/postman: 24 peticiones / 32 comprobaciones en 6 carpetas, generadas desde generar_coleccion.py. Pasan todas contra el Core real con Ollama.

### T-038 · Dynamic Island: despliegue solo por clic, iluminacion/animacion al hover y auto-evasion de Snipping Tool

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Separar hover y click en Dynamic Island: hover intensifica retroiluminacion morada y anima mini-avatar/chevron sin desplegar; click despliega y repliega. Auto-dodge en Go para Snipping Tool evitando sobreposicion.

**Archivos:** `pet/web/pet.js`, `pet/web/pet.css`, `pet/desktop/window_windows.go`, `pet/desktop/main_test.go`

**Última nota (antigravity):** Completado: hover ya no despliega, intensifica iluminacion morada de fondo y anima mini-avatar/chevron; clic despliega/repliega exclusivamente. Auto-dodge en Go para Snipping Tool (Win+Shift+S) evitando sobreposicion.
