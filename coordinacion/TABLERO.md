# Tablero de tareas — Project MEKA

> ⚠️ **Archivo generado automáticamente.** No lo edites a mano: usa `python scripts/tareas.py` (ver [README](README.md)). Fuente: `tareas.json`.

_Última actualización: 2026-11-15T17:12:04-06:00_

## Resumen

| Agente | Rol | ⬜ pendiente | 🔄 en_progreso | ⛔ bloqueada | 👀 en_revision | ✅ hecha | 🚫 descartada |
|---|---|---|---|---|---|---|---|
| **Claude Code** | Backend, IA, agente y canales | 4 | 0 | 0 | 0 | 29 | 1 |
| **Antigravity (Gemini)** | Frontend, UI/UX y arte | 2 | 0 | 0 | 0 | 26 | 0 |

## Claude Code

| ID | Estado | Prioridad | Tarea | Depende de | Actualizada |
|---|---|---|---|---|---|
| T-042 | ⬜ pendiente | media | Aislamiento de las manos antes de activar la escritura: usuario restringido de Windows (NTFS) vs Docker/WSL2 | — | 2026-11-11 10:52 |
| T-009 | ⬜ pendiente | baja | Configuración tipada y validada al arrancar (pydantic) | — | 2026-11-09 19:30 |
| T-010 | ⬜ pendiente | baja | Presupuesto de API en la nube y evento budget.low | — | 2026-11-09 19:30 |
| T-032 | ⬜ pendiente | baja | Telegram: comando /privado para activar el modo privado de la conversación | — | 2026-11-09 22:13 |
| T-001 | ✅ hecha | alta | Entorno local de backend: Python 3.12, venv, dependencias, lint y tests | — | 2026-11-11 10:07 |
| T-002 | ✅ hecha | alta | Tablero compartido de tareas y protección de áreas (este sistema) | — | 2026-11-11 10:07 |
| T-003 | ✅ hecha | alta | Confirmación de acciones: agent.confirm con id y user.confirm en el WebSocket | — | 2026-11-11 10:07 |
| T-004 | ✅ hecha | alta | Fase 3 · Manos (solo lectura): carpetas autorizadas, listar, leer y buscar | — | 2026-11-11 12:00 |
| T-015 | ✅ hecha | alta | Modularidad: dividir server/app.py en routers (seguridad, esquemas, rutas por dominio) | — | 2026-11-11 10:07 |
| T-016 | ✅ hecha | alta | Modularidad: motores TTS como paquete con interfaz común (edge, piper, qwen) | — | 2026-11-11 10:07 |
| T-019 | ✅ hecha | alta | Filosofía 5.3: enrutamiento por tarea y privacidad (documentos/sensibles a local) | — | 2026-11-11 10:07 |
| T-020 | ✅ hecha | alta | Filosofía 5.1/8: respuesta normalizada del proveedor (texto, modelo, uso) y registro de ejecución sin contenido | — | 2026-11-11 10:07 |
| T-026 | ✅ hecha | alta | Pruebas del canal MCP con clientes reales (SDK stdio, Claude Code, Gemini CLI) | — | 2026-11-11 10:07 |
| T-028 | ✅ hecha | alta | Bug: emojis en la consola de Windows con salida redirigida daban HTTP 500 en /v1/chat | — | 2026-11-11 10:07 |
| T-031 | ✅ hecha | alta | Privacidad de la memoria larga: recuerdos guardados en una conversación privada no deben ir a prompts en la nube | — | 2026-11-11 10:07 |
| T-046 | ✅ hecha | alta | Notificaciones de Windows para la isla: system.notification privado, apps permitidas, códigos ocultos, descartar y abrir | — | 2026-11-11 12:00 |
| T-050 | ✅ hecha | alta | Modo concentración: retener lo que distrae, dejar pasar permisos y lo importante, resumen al terminar | — | 2026-11-11 12:15 |
| T-053 | ✅ hecha | alta | Enrutamiento por capacidades: cada cerebro declara qué entiende (texto, imagen, audio, PDF) y MEKA usa la ruta óptima | — | 2026-11-11 15:30 |
| T-055 | ✅ hecha | alta | Isla sin Spotify ni notificaciones al arrancar: CORS para la mascota, primera lectura y estado inicial por WebSocket | — | 2026-11-14 20:35 |
| T-056 | ✅ hecha | alta | Agenda y Hanna proactiva: tareas y recordatorios hablando, avisos a su hora y resumen no invasivo | — | 2026-11-14 20:35 |
| T-058 | ✅ hecha | alta | Avisos de Hanna en Telegram cuando no estás al equipo (botones Hecho/Posponer, /tareas) | — | 2026-11-14 21:42 |
| T-005 | ✅ hecha | media | Fase 3 · Manos (escritura): punto de restauración git + confirmación + deshacer | T-003, T-004 | 2026-11-11 12:00 |
| T-006 | 🚫 descartada | media | Estado de la mascota en el núcleo: GET/PUT /v1/pet/state persistido en SQLite | — | 2026-11-11 11:59 |
| T-007 | ✅ hecha | media | Contrato publicado y versionado: GET /v1/contract (eventos, emociones, versión) | — | 2026-11-11 10:07 |
| T-008 | ✅ hecha | media | STT más rápido con faster-whisper (motor opcional, respaldo openai-whisper) | T-001 | 2026-11-11 15:30 |
| T-017 | ✅ hecha | media | Modularidad: extraer almacén de audios del motor e historial de conversación del servicio de IA | — | 2026-11-11 10:07 |
| T-018 | ✅ hecha | media | Guardia de tamaño: test que falla si un módulo del backend supera 300 líneas | T-015, T-016, T-017 | 2026-11-11 10:07 |
| T-021 | ✅ hecha | media | Filosofía 5.2: eventos normalizados para el avatar (error y fin de respuesta) | — | 2026-11-11 10:07 |
| T-029 | ✅ hecha | media | Modularidad: core/engine.py está en 290 líneas (límite 300); separar análisis de archivos y voz | — | 2026-11-11 10:07 |
| T-037 | ✅ hecha | media | Pruebas de la API con Postman CLI (colección generada + entorno local) | — | 2026-11-11 10:07 |
| T-044 | ✅ hecha | media | Datos del sistema para la Dynamic Island: system.media, system.battery y user.media (contrato 1.7) | — | 2026-11-11 12:00 |
| T-052 | ✅ hecha | media | Instalación más ligera: PyTorch opcional (openai-whisper a requirements aparte) | — | 2026-11-11 15:30 |
| T-054 | ✅ hecha | media | Adaptador OpenAI-compatible (llama.cpp, LM Studio, vLLM): Gemma 4 local con audio nativo | — | 2026-11-11 15:30 |
| T-060 | ✅ hecha | media | Carátulas de lo que suena y «Mientras no estabas» al volver al equipo | — | 2026-11-14 21:43 |

## Antigravity (Gemini)

| ID | Estado | Prioridad | Tarea | Depende de | Actualizada |
|---|---|---|---|---|---|
| T-061 | ⬜ pendiente | alta | Isla recogida: foco momentáneo en el hero al llegar una notificación o cambiar de canción | — | 2026-11-15 17:00 |
| T-062 | ⬜ pendiente | media | Isla: arreglos menores que vio Claude (doble POST /v1/focus, errores de fetch silenciados, aviso de formato) | — | 2026-11-15 17:12 |
| T-013 | ✅ hecha | alta | Rediseño visual del escenario de la mascota y HUD Tamagotchi (glassmorphism, animaciones y menú contextual) | — | 2026-11-09 19:30 |
| T-014 | ✅ hecha | alta | Dashboard de control y simulador en navegador (tema oscuro/claro, log de eventos, selector visual de skins y estado Core) | — | 2026-11-09 19:30 |
| T-022 | ✅ hecha | alta | Integración de assets Pixel Art animados (Hana y Clawd), herramienta pixelize.py y GUI minimalista estilo Apple con ventana emergente | — | 2026-11-09 21:14 |
| T-025 | ✅ hecha | alta | Decisión: mascota de escritorio en Go con Wails v2 (reemplaza a Tauri y al prototipo Tkinter) | — | 2026-11-09 21:39 |
| T-033 | ✅ hecha | alta | Corrección de fondo blanco en ventana Win32/DWM, bocadillo de diálogo no intrusivo y animaciones squash & stretch | — | 2026-11-09 22:31 |
| T-034 | ✅ hecha | alta | Diálogo de permisos: usar timeout del evento, cerrar con agent.confirmed y pedir pendientes al conectar | — | 2026-11-11 10:57 |
| T-035 | ✅ hecha | alta | Notch superior centrado estilo Apple Dynamic Island con negro profundo, retroiluminación morada tenue y despliegue elástico | — | 2026-11-11 09:31 |
| T-038 | ✅ hecha | alta | Dynamic Island: despliegue solo por clic, iluminacion/animacion al hover y auto-evasion de Snipping Tool | — | 2026-11-11 10:03 |
| T-039 | ✅ hecha | alta | Dynamic Island: arranque centrado con hook CBT, pildora flotante y diseno Apple autentico | — | 2026-11-11 10:17 |
| T-040 | ✅ hecha | alta | Dynamic Island: inicio estrictamente colapsado en pildora y eliminacion de auto-despliegue | — | 2026-11-11 10:28 |
| T-041 | ✅ hecha | alta | Dynamic Island: eliminacion de halo cuadrado, auto-colapso por mouseleave y diseno Samsung Brief | — | 2026-11-11 10:46 |
| T-043 | ✅ hecha | alta | Dynamic Island fluida en Go: ventana fija + resorte en JS, click-through, DPI y foco (ver propuesta) | — | 2026-11-11 11:32 |
| T-047 | ✅ hecha | alta | Pila de tarjetas tipo Brief en la isla con animaciones (música, batería, notificaciones, agentes, permisos, mensajes de MEKA) | — | 2026-11-11 13:11 |
| T-049 | ✅ hecha | alta | Quitar las mecánicas de cuidado del prototipo: alimentar, energía, saciedad, ánimo, afecto y desbloqueos | — | 2026-11-11 12:31 |
| T-057 | ✅ hecha | alta | Isla: agenda de Hanna (tarjeta de aviso con Hecho/Posponer, resumen proactivo, lista de tareas y botón ¿Qué tengo pendiente?) | T-056 | 2026-11-14 20:53 |
| T-011 | ✅ hecha | media | (Propuesta) UI de confirmación en la mascota para agent.confirm / user.confirm | T-003 | 2026-11-11 10:58 |
| T-023 | ✅ hecha | media | Lint: RUF002 (signo × ambiguo) en pet/tools/pixelize.py rompe ruff check . del CI | — | 2026-11-09 21:39 |
| T-024 | ✅ hecha | media | App de escritorio nativa en Python (ventana transparente sin bordes + Pixel Art + Drawer) | — | 2026-11-09 21:24 |
| T-027 | ✅ hecha | media | Ventana fija no redimensionable, flotante (Always on Top), fondo transparente nativo en Go y animaciones mejoradas | — | 2026-11-09 21:56 |
| T-030 | ✅ hecha | media | Crear skill de Golang, corregir errores de UI (Drawer, arrastre, capturas) y sincronizar documentacion | — | 2026-11-09 22:09 |
| T-036 | ✅ hecha | media | App Go/web: leer eventos y emociones de GET /v1/contract y avisar si la versión mayor no coincide | — | 2026-11-11 10:57 |
| T-045 | ✅ hecha | media | Isla: mostrar la música en reproducción y la batería (eventos system.* del Core) | — | 2026-11-11 11:45 |
| T-048 | ✅ hecha | media | Modo compañero al desplegar la isla: avatar flotante y chat con MEKA | — | 2026-11-11 12:31 |
| T-051 | ✅ hecha | media | Modo concentración en la isla: botón empezar/terminar, cuenta atrás y tarjeta de resumen | — | 2026-11-14 20:02 |
| T-059 | ✅ hecha | media | Settings en menú 3 puntos, reply dock inferior, Liquid Glass blur, carátulas media e integraciones Core | — | 2026-11-14 21:27 |
| T-012 | ✅ hecha | baja | (Propuesta) Sincronizar el Tamagotchi con /v1/pet/state | T-006 | 2026-11-09 21:14 |

## Detalle

### T-001 · Entorno local de backend: Python 3.12, venv, dependencias, lint y tests

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Python 3.12 (el proyecto soporta 3.11-3.13), PyTorch CPU (sin GPU NVIDIA), requirements-dev.txt, `ruff check .` y `pytest` en verde. Pendiente fuera de pip: Ollama (+ gemma3:12b y embeddinggemma) y FFmpeg.

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-002 · Tablero compartido de tareas y protección de áreas (este sistema)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

`coordinacion/` + `scripts/tareas.py`, hooks de git (commit-msg y post-commit) y hooks de Claude Code (SessionStart, PreToolUse, Stop).

**Archivos:** `scripts/tareas.py`, `coordinacion/**`, `.githooks/**`, `.claude/settings.json`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-003 · Confirmación de acciones: agent.confirm con id y user.confirm en el WebSocket

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Registro de confirmaciones pendientes en MEKA Core: `agent.confirm` pasa a llevar `{id, action, expires_at}`; el cliente responde `user.confirm {id, approved}` por WebSocket o `POST /v1/confirmations/{id}` (para Telegram/móvil). Caducidad configurable y evento de resultado. Cambio de contrato ADITIVO: se avisa en coordinacion/README.md antes de publicarlo.

**Archivos:** `core/events.py`, `core/engine.py`, `server/app.py`, `tests/test_server.py`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-004 · Fase 3 · Manos (solo lectura): carpetas autorizadas, listar, leer y buscar

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

`hands.folders` en config.yml; nada fuera de ellas (resolución de rutas, sin symlinks que escapen). API `/v1/workspace/...` y herramientas MCP. Emite `agent.working`/`agent.done`/`agent.error` para que la mascota reaccione. Registro de cada acción.

**Archivos:** `core/**`, `server/app.py`, `channels/mcp/**`, `config.yml`, `tests/**`

**Commits:** `742af8d`

**Última nota (git (Nekimu)):** commit 742af8d: feat(backend): manos, Dynamic Island (música, batería, notificaciones) y filosof

### T-005 · Fase 3 · Manos (escritura): punto de restauración git + confirmación + deshacer

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

Antes de mover/renombrar/borrar: commit de restauración en la carpeta autorizada, `agent.confirm` (T-003) y operación `undo`.

**Archivos:** `core/**`, `server/app.py`, `tests/**`

**Depende de:** T-003, T-004

**Commits:** `742af8d`

**Última nota (git (Nekimu)):** commit 742af8d: feat(backend): manos, Dynamic Island (música, batería, notificaciones) y filosof

### T-006 · Estado de la mascota en el núcleo: GET/PUT /v1/pet/state persistido en SQLite

**Responsable:** Claude Code · **Estado:** 🚫 descartada · **Prioridad:** media

Guardar energía, saciedad, ánimo, afecto y desbloqueos en el Core para que escritorio, móvil y Telegram compartan la misma mascota. Las reglas del Tamagotchi siguen en el frontend; el Core solo almacena y difunde un evento `pet.state` (nuevo, aditivo).

**Archivos:** `core/memory.py`, `server/app.py`, `core/events.py`, `tests/**`

**Última nota (claude):** Descartada por decisión del usuario (2026-11-11): MEKA no tiene mecánicas de cuidado (energía, saciedad, ánimo, afecto, desbloqueos). El Tamagotchi solo inspira la interacción; la filosofía es productividad, no distraer.

### T-007 · Contrato publicado y versionado: GET /v1/contract (eventos, emociones, versión)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

El frontend puede leer en tiempo de ejecución los eventos y emociones válidos (`OUTBOUND_EVENTS`, `EMOTIONS`, eventos de entrada) y la versión del contrato, en lugar de duplicarlos a mano. Test que falle si cambia el contrato sin subir la versión.

**Archivos:** `server/app.py`, `core/events.py`, `tests/test_server.py`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-008 · STT más rápido con faster-whisper (motor opcional, respaldo openai-whisper)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

Notas de voz 2-4x más rápidas en CPU (punto 3 de la auditoría). `stt.engine` en config.yml.

**Archivos:** `ai/stt.py`, `config.yml`, `tests/**`

**Depende de:** T-001

**Commits:** `59b9a9a`, `d49c080`

**Última nota (git (Nekimu)):** commit 59b9a9a: feat(backend): voz a texto con faster-whisper y PyTorch opcional (cierra T-008, 

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

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

Propuesta de Claude Code como contraparte de T-003: diálogo Aprobar/Rechazar en la mascota que envía `user.confirm {id, approved}`. Antigravity puede aceptarla, cambiarla o descartarla.

**Archivos:** `pet/web/**`

**Depende de:** T-003

**Última nota (antigravity):** Aceptada e integrada: interfaz de confirmacion con botones Permitir/Cancelar, cierre reactivo, timeout sincronizado y soporte nativo en el notch.

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

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-016 · Modularidad: motores TTS como paquete con interfaz común (edge, piper, qwen)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

ai/tts.py (315 líneas) mezcla 3 motores, la conversión a OGG y el respaldo. Interfaz TTSEngine (pendiente de la auditoría) y un módulo por motor: añadir uno nuevo no toca los demás.

**Archivos:** `ai/tts.py`, `ai/tts/**`, `tests/test_tts.py`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-017 · Modularidad: extraer almacén de audios del motor e historial de conversación del servicio de IA

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

MekaEngine y AIService tienen responsabilidades secundarias (audios temporales, historial) que crecerán con T-003/T-005.

**Archivos:** `core/engine.py`, `core/audio_store.py`, `ai/service.py`, `core/history.py`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-018 · Guardia de tamaño: test que falla si un módulo del backend supera 300 líneas

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `tests/test_modularidad.py`

**Depende de:** T-015, T-016, T-017

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-019 · Filosofía 5.3: enrutamiento por tarea y privacidad (documentos/sensibles a local)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Hoy solo hay ai.local_only global. Falta: proveedor por tarea (chat, visión, documentos) y marca 'privado' por petición que obligue a un proveedor local, como pide la tabla de enrutamiento.

**Archivos:** `ai/**`, `core/engine.py`, `config.yml`, `tests/**`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-020 · Filosofía 5.1/8: respuesta normalizada del proveedor (texto, modelo, uso) y registro de ejecución sin contenido

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Provider.chat devuelve solo texto. Normalizar a ProviderResult(text, provider, model, tokens, latency) y guardar en SQLite proveedor, modelo, hora, tarea y resultado SIN el texto de la conversación. Base de T-010 (budget.low).

**Archivos:** `ai/providers/**`, `ai/service.py`, `core/**`, `tests/**`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-021 · Filosofía 5.2: eventos normalizados para el avatar (error y fin de respuesta)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

Si el cerebro falla, la mascota no se entera (solo se publica thinking y message). Publicar emotion=error / agent.error al fallar y volver a idle al terminar. Cambio aditivo del contrato: avisar a Antigravity.

**Archivos:** `core/engine.py`, `core/events.py`, `tests/**`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

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

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-027 · Ventana fija no redimensionable, flotante (Always on Top), fondo transparente nativo en Go y animaciones mejoradas

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `pet/desktop/window_windows.go`, `pet/desktop/main.go`, `pet/desktop/main_test.go`, `pet/web/pet.css`, `pet/web/pet.js`, `pet/README.md`

**Última nota (antigravity):** Configurada ventana fija 300x390 no redimensionable (HintFixed + WS_POPUP), AlwaysOnTop persistente con reafirmación en drag, fondo 100% transparente en WebView2 con ICoreWebView2Controller2::PutDefaultBackgroundColor y DWM, sombreado dinámico reactivo, squash/stretch y tacto al clic

### T-028 · Bug: emojis en la consola de Windows con salida redirigida daban HTTP 500 en /v1/chat

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `core/logger.py`, `tests/test_text_utils.py`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-029 · Modularidad: core/engine.py está en 290 líneas (límite 300); separar análisis de archivos y voz

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `core/**`, `tests/**`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-030 · Crear skill de Golang, corregir errores de UI (Drawer, arrastre, capturas) y sincronizar documentacion

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `pet/desktop/window_windows.go`, `pet/desktop/main_test.go`, `pet/web/index.html`, `pet/web/pet.js`, `pet/web/pet.css`, `pet/README.md`, `docs/VISION.md`, `docs/FILOSOFIA_HIBRIDA.md`, `README.md`, `CHANGELOG.md`

**Última nota (antigravity):** Creado skill golang en ~/.gemini/config/skills/golang/SKILL.md. Corregidos bugs de UI: Drawer simplificado con transicion popover sin cierres accidentales de IntersectionObserver, arrastre Dynamic Island con stageTop y liberacion de puntero, tarjetas de avatares en columna unica, DataPath persistente en WebView2, y documentacion sincronizada sin referencias legadas a Tauri

### T-031 · Privacidad de la memoria larga: recuerdos guardados en una conversación privada no deben ir a prompts en la nube

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Hoy la privacidad cubre la petición y el historial, pero un 'recuerda esto' dicho en modo privado se guarda como recuerdo normal y puede añadirse después al prompt de Claude/Gemini. Marcar recuerdos como privados y filtrarlos cuando el proveedor no es local.

**Archivos:** `core/memory.py`, `ai/service.py`, `core/semantic.py`, `tests/**`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-032 · Telegram: comando /privado para activar el modo privado de la conversación

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** baja

**Archivos:** `channels/telegram/**`, `tests/test_telegram.py`

**Última nota (claude):** creada

### T-033 · Corrección de fondo blanco en ventana Win32/DWM, bocadillo de diálogo no intrusivo y animaciones squash & stretch

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `pet/desktop/window_windows.go`, `pet/web/pet.css`, `pet/web/pet.js`

**Última nota (antigravity):** pet(desktop+web): transparencia DWM sin fondo blanco, clamp en bocadillo y animaciones squash & stretch

### T-034 · Diálogo de permisos: usar timeout del evento, cerrar con agent.confirmed y pedir pendientes al conectar

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Aviso de Claude Code: T-003 ya está en el Core. agent.confirm trae {id, action, timeout, expires_at, details?}; hoy pet.js cierra el diálogo a los 25 s fijos aunque el Core espera 'timeout'. Nuevo evento agent.confirmed {id, approved, by} para cerrar el diálogo si se resolvió en otro cliente o caducó (by: timeout). Al conectar: GET /v1/confirmations. user.confirm no cambia. Además: .gitignore actualizado por Claude: *.exe (meka-desktop.exe) y .gemini/ quedan fuera del repo; se quitaron las líneas de pet/src-tauri.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (antigravity):** Completado: 1) pet.js ahora escucha agent.confirmed para cerrar de inmediato el dialogo si la accion fue resuelta externamente o por timeout. 2) Tiempo limite calculado con precision desde expires_at o timeout del evento. 3) Peticion automatica de pendientes a GET /v1/confirmations al conectar el WebSocket.

### T-035 · Notch superior centrado estilo Apple Dynamic Island con negro profundo, retroiluminación morada tenue y despliegue elástico

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `pet/desktop/main.go`, `pet/desktop/window_windows.go`, `pet/desktop/main_test.go`, `pet/web/index.html`, `pet/web/pet.css`, `pet/web/pet.js`, `pet/README.md`

**Última nota (antigravity):** pet(desktop+web): notch superior estilo Apple Dynamic Island en negro profundo, aura tenue morada y despliegue elástico hacia abajo

### T-036 · App Go/web: leer eventos y emociones de GET /v1/contract y avisar si la versión mayor no coincide

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

Aviso de Claude Code (T-007): GET /v1/contract es público y devuelve version (1.4), events.outbound/inbound con campos y tipos, emotions y rest. /v1/health trae contract. Sugerencia: al conectar, si la versión mayor difiere, mostrar aviso en vez de fallar en silencio.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (antigravity):** Completado: 1) pet.js consulta GET /v1/contract y /v1/health al conectar. 2) Verifica compatibilidad de version mayor (1.x) y muestra advertencia clara si no coincide. 3) Sincroniza la personalidad activa del Core con los avatares disponibles.

### T-037 · Pruebas de la API con Postman CLI (colección generada + entorno local)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `tests/postman/**`, `README.md`

**Commits:** `92ca09c`

**Última nota (git (Nekimu)):** commit 92ca09c: feat(backend): núcleo modular, privacidad, permisos y contrato publicado

### T-038 · Dynamic Island: despliegue solo por clic, iluminacion/animacion al hover y auto-evasion de Snipping Tool

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Separar hover y click en Dynamic Island: hover intensifica retroiluminacion morada y anima mini-avatar/chevron sin desplegar; click despliega y repliega. Auto-dodge en Go para Snipping Tool evitando sobreposicion.

**Archivos:** `pet/web/pet.js`, `pet/web/pet.css`, `pet/desktop/window_windows.go`, `pet/desktop/main_test.go`

**Última nota (antigravity):** Completado: hover ya no despliega, intensifica iluminacion morada de fondo y anima mini-avatar/chevron; clic despliega/repliega exclusivamente. Auto-dodge en Go para Snipping Tool (Win+Shift+S) evitando sobreposicion.

### T-039 · Dynamic Island: arranque centrado con hook CBT, pildora flotante y diseno Apple autentico

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Eliminacion del salto inicial con hook CBT nativo de Win32; pildora flotante con border-radius continuo de 360 grados, eliminacion del recuadro anidado interno, especularidad vitrea y diseno fluido de Apple.

**Archivos:** `pet/desktop/window_windows.go`, `pet/desktop/main.go`, `pet/desktop/main_test.go`, `pet/web/pet.css`, `pet/web/index.html`

**Última nota (antigravity):** Hook CBT nativo de Win32 implementado (cero salto visual al arrancar); pildora flotante con border-radius 9999px y squircle 34px; diseno unificado sin caja anidada, especularidad vitrea Apple e iluminacion morada difusa.

### T-040 · Dynamic Island: inicio estrictamente colapsado en pildora y eliminacion de auto-despliegue

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Correccion del auto-despliegue que forzaba el estado expandido en el saludo inicial de say(); ahora inicia 100% como pildora flotante compacta, ocultando el escenario interno hasta que el usuario hace clic.

**Archivos:** `pet/web/pet.js`, `pet/web/pet.css`, `pet/desktop/window_windows.go`

**Última nota (antigravity):** Resuelto: 1) say() ya no auto-despliega el notch para saludos o mensajes normales, solo para agent.confirm urgente. 2) start() inicia estrictamente en modo pildora. 3) En modo colapsado los elementos internos se ocultan con display: none y la pildora flota con border-radius 9999px continuo.

### T-041 · Dynamic Island: eliminacion de halo cuadrado, auto-colapso por mouseleave y diseno Samsung Brief

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Eliminar halo/recuadro rectangular de fondo asegurando transparencia 100% pura exterior, colapso interactivo por clic en el notch sin re-apertura por bubbling, auto-colapso suave al salir el cursor (mouseleave) y estetica refinada inspirada en Samsung Brief.

**Archivos:** `pet/web/pet.css`, `pet/web/pet.js`, `pet/desktop/window_windows.go`

**Última nota (antigravity):** Completado: 1) Eliminado el halo/recuadro rectangular de fondo al contener la iluminacion morada como gradiente radial y resplandor interno (inset) sin sangrado exterior. 2) Corregido el clic en el notch al estar expandido para replegar a pildora sin re-apertura por bubbling. 3) Implementado auto-colapso suave (350ms) al salir el cursor (mouseleave) o al perder foco la ventana, respetando escritura en chat y autorizaciones. 4) Estetica inspirada en Samsung Brief / Dynamic Island con bordes squircle organicos, acrilico oscuro y tarjeta de briefing refinada.

### T-042 · Aislamiento de las manos antes de activar la escritura: usuario restringido de Windows (NTFS) vs Docker/WSL2

**Responsable:** Claude Code · **Estado:** ⬜ pendiente · **Prioridad:** media

Decisión del usuario (2026-11-11): la escritura (T-005) queda INACTIVA hasta tener una segunda capa de aislamiento del sistema operativo. Evaluar: (a) ejecutar MEKA Core con un usuario de Windows sin privilegios y permisos NTFS solo sobre las carpetas autorizadas (sin VM ni RAM extra); (b) Docker Desktop + WSL2 con montajes solo de esas carpetas (2-4 GB de RAM, comprobar virtualización en firmware, montajes lentos). Criterio: aislamiento real con el menor consumo en este equipo (i5-8265U, 16 GB).

**Archivos:** `core/hands/**`, `docs/**`

**Última nota (claude):** creada

### T-043 · Dynamic Island fluida en Go: ventana fija + resorte en JS, click-through, DPI y foco (ver propuesta)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Propuesta de Claude Code en coordinacion/propuestas/dynamic-island-go.md. Diagnóstico: mekaSetNotchExpanded redimensiona la ventana nativa con SetWindowPos y eso nunca será fluido. DynamicWin (inspiración; licencia CC BY-SA 4.0: no copiar código) usa una ventana FIJA y anima la isla dentro con un resorte de segundo orden. Pasos: 1) ventana fija + resorte JS; 2) clics que atraviesan lo transparente alternando WS_EX_TRANSPARENT según el cursor (lo que DynamicWin no resuelve); 3) DPI PerMonitorV2; 4) WS_EX_NOACTIVATE y foco para el chat. Opcional: eventos system.media/system.battery desde el Core.

**Archivos:** `pet/desktop/**`, `pet/web/**`

**Última nota (antigravity):** Implementada ventana fija 380x480 con click-through WS_EX_TRANSPARENT a 60Hz, resorte de segundo orden en JS, DPI PerMonitorV2, WS_EX_NOACTIVATE, desactivación de sombra DWM y HUD estilo DynamicWin/Samsung Brief

### T-044 · Datos del sistema para la Dynamic Island: system.media, system.battery y user.media (contrato 1.7)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

**Archivos:** `core/system/**`, `core/contract.py`, `server/routes/system.py`, `tests/test_system.py`, `requirements.txt`, `config.yml`

**Commits:** `742af8d`

**Última nota (git (Nekimu)):** commit 742af8d: feat(backend): manos, Dynamic Island (música, batería, notificaciones) y filosof

### T-045 · Isla: mostrar la música en reproducción y la batería (eventos system.* del Core)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

Ya disponible en el Core (contrato 1.7): system.media {playing, title?, artist?, app?, position?, duration?} y system.battery {percent, charging}, solo cuando cambian; al conectar, GET /v1/system. Controles: enviar user.media {action: play_pause|next|previous} por WebSocket. La posición no genera eventos: avanzarla en local con un temporizador mientras playing=true. Ver coordinacion/propuestas/dynamic-island-go.md.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (antigravity):** Integrados eventos system.media y system.battery: ecualizador reactivo en notch colapsado (#miniMusicBar), tarjeta reproductor (#mediaWidget) con progreso local, controles user.media por WebSocket/REST, y chip de batería con estado de carga en el glance HUD

### T-046 · Notificaciones de Windows para la isla: system.notification privado, apps permitidas, códigos ocultos, descartar y abrir

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `core/system/**`, `core/contract.py`, `server/routes/**`, `tests/**`, `requirements.txt`, `config.yml`

**Commits:** `742af8d`

**Última nota (git (Nekimu)):** commit 742af8d: feat(backend): manos, Dynamic Island (música, batería, notificaciones) y filosof

### T-047 · Pila de tarjetas tipo Brief en la isla con animaciones (música, batería, notificaciones, agentes, permisos, mensajes de MEKA)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Idea del usuario (inspiración Samsung Brief). La isla compone las tarjetas con eventos que ya existen: system.media, system.battery, system.notification (en camino, T-046), agent.working/done/error, agent.confirm (prioridad máxima) y message. Ordenar por prioridad y pasar entre tarjetas con animaciones. Controles: user.media y user.notification {id, action: dismiss|open}.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (antigravity):** Pila de tarjetas Samsung Brief con animaciones One UI 9 fluido (avatar, multimedia con ecualizador, y notificaciones con badge pulse), interaccion por rueda de raton y paginacion por dots

### T-048 · Modo compañero al desplegar la isla: avatar flotante y chat con MEKA

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

Idea del usuario: al expandir la isla aparece el avatar y pasa a modo compañero. El backend ya lo cubre: chat por WebSocket (user.message, con private opcional), respuestas con emoción, memoria y permisos. El estado de la mascota en el Core llegará con T-006.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (antigravity):** Modo companero integrado al desplegar la Dynamic Island: avatar flotante y chat con MEKA en el shelf

### T-049 · Quitar las mecánicas de cuidado del prototipo: alimentar, energía, saciedad, ánimo, afecto y desbloqueos

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Decisión del usuario (2026-11-11): el Tamagotchi es solo inspiración para INTERACTUAR y CONVERSAR con el asistente; no se le alimenta ni se le cuida. Filosofía: productividad y ayuda, no distraer. Quitar del prototipo las estadísticas (HUD de energía/saciedad/ánimo/afecto), alimentar/acariciar/jugar, el progreso offline, dormirse sola y los personajes desbloqueables por afecto (todos disponibles). Las emociones se quedan para comunicar lo que hace el asistente (pensando, trabajando, error, celebra una tarea). La emoción 'eating' queda heredada en el contrato; si ya no se usa, avísame y la retiro en un cambio de versión mayor. Ver la sección «Compañera, no mascota que cuidar» de docs/VISION.md.

**Archivos:** `pet/web/**`, `pet/desktop/**`, `pet/README.md`

**Última nota (antigravity):** Eliminadas todas las mecanicas de cuidado del prototipo (hambre, energia, animo, afecto y desbloqueos)

### T-050 · Modo concentración: retener lo que distrae, dejar pasar permisos y lo importante, resumen al terminar

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

**Archivos:** `core/focus.py`, `core/events.py`, `core/engine.py`, `core/contract.py`, `server/routes/**`, `tests/**`, `config.yml`

**Commits:** `fec83a0`

**Última nota (git (Nekimu)):** commit fec83a0: feat(backend): modo concentración (cierra T-050)

### T-051 · Modo concentración en la isla: botón empezar/terminar, cuenta atrás y tarjeta de resumen

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

Backend listo (T-050, contrato 1.9). Enviar user.focus {action: start, minutes?} / {action: stop}, o POST/DELETE /v1/focus. Recibir focus.started {until, minutes} → mostrar cuenta atrás discreta y dejar la isla quieta; focus.ended {reason, held, notifications} → una tarjeta: 'Mientras te concentrabas: N notificaciones' (detalle con GET /v1/system/notifications). Durante la sesión el Core ya no envía lo que distrae; los permisos (agent.confirm) y errores siguen llegando. Alineado con la filosofía: ayuda, no distrae.

**Archivos:** `pet/web/**`, `pet/desktop/**`

**Última nota (antigravity):** UI Modo Concentración integrada en Dynamic Island: eventos focus.started y focus.ended, temporizador en vivo (#focusBadge/#focusTimerText), supresión de expansiones distractoras, resumen al finalizar y controles WS/REST (#focusToggleBtn y menú contextual).

### T-052 · Instalación más ligera: PyTorch opcional (openai-whisper a requirements aparte)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

Con faster-whisper como motor por defecto, PyTorch (varios GB) solo hace falta para el respaldo openai-whisper y para Qwen-TTS. Mover openai-whisper a un requirements opcional y ajustar CI y README: la instalación base pasaría de varios GB a unos cientos de MB.

**Archivos:** `requirements.txt`, `requirements-*.txt`, `README.md`, `.github/**`

**Commits:** `59b9a9a`, `d49c080`

**Última nota (claude):** requirements-whisper.txt (opcional) con openai-whisper; requirements.txt sin PyTorch (comprobado en venv limpio: 71 paquetes sin torch vs 86 con él); CI sin el paso de PyTorch; README y config actualizados.

### T-053 · Enrutamiento por capacidades: cada cerebro declara qué entiende (texto, imagen, audio, PDF) y MEKA usa la ruta óptima

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Idea del usuario (2026-11-11): el objetivo del asistente es fijo, pero el cómo (qué herramientas usa y cuáles omite) depende del cerebro. Capacidades declaradas en config por proveedor/modelo (cambian rápido; no se adivinan). Voz: si el cerebro entiende audio (Gemini; Gemma 4 vía llama.cpp) se le envía la nota tal cual y se omite la transcripción; si no, faster-whisper. Si la ruta nativa falla, respaldo con transcripción. Lo mismo para imágenes (visión o modelo de visión aparte) y PDF (nativo o extracción de texto). La privacidad (T-019) sigue mandando: lo privado solo a locales. Decidir qué texto guarda el historial cuando no hay transcripción.

**Archivos:** `ai/**`, `core/**`, `config.yml`, `tests/**`

**Commits:** `b43e6dd`, `d49c080`

**Última nota (git (Nekimu)):** commit b43e6dd: feat(backend): enrutamiento por capacidades, voz y PDF nativos (cierra T-053)

### T-054 · Adaptador OpenAI-compatible (llama.cpp, LM Studio, vLLM): Gemma 4 local con audio nativo

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

Ollama aún no acepta audio de forma fiable con Gemma 4; llama-server (llama.cpp) sí, por /v1/chat/completions con input_audio. Un adaptador OpenAI-compatible abre además LM Studio, vLLM y otros servidores locales sin tocar el resto de MEKA.

**Archivos:** `ai/providers/**`, `config.yml`, `requirements*.txt`, `tests/**`

**Commits:** `7ab7c95`, `d49c080`

**Última nota (git (Nekimu)):** commit 7ab7c95: feat(backend): cerebro openai_compat, Gemma 4 con audio nativo en llama.cpp (cie

### T-055 · Isla sin Spotify ni notificaciones al arrancar: CORS para la mascota, primera lectura y estado inicial por WebSocket

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

La app de Go sirve la mascota en 127.0.0.1:<puerto> y el Core no enviaba CORS: WebView2 bloqueaba GET /v1/system, /v1/system/notifications y los POST de acciones. Solo llegaba el WebSocket, que no repite una canción en pausa ni las notificaciones que ya había.

**Archivos:** `server/security.py`, `server/app.py`, `server/routes/events.py`, `core/system/**`, `tests/**`

**Commits:** `579dac9`, `21980b9`

**Última nota (git (Nekimu)):** commit 579dac9: fix(backend): la isla ya ve Spotify y las notificaciones al arrancar (cierra T-0

### T-056 · Agenda y Hanna proactiva: tareas y recordatorios hablando, avisos a su hora y resumen no invasivo

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

Tareas y recordatorios en lenguaje natural (fechas en español sin modelo), contexto real para el cerebro, avisos reminder.due, resumen proactivo nudge con límites (silencio, concentración, conversación, frecuencia), API, WebSocket user.task, MCP. Contrato 1.10.

**Archivos:** `core/tasks/**`, `server/routes/tasks.py`, `server/schemas.py`, `core/contract.py`, `core/focus.py`, `channels/**`, `personas/dva/persona.yml`, `config.yml`, `tests/**`

**Commits:** `d1fd6f1`, `21980b9`

**Última nota (git (Nekimu)):** commit d1fd6f1: feat(backend): agenda y Hanna proactiva (cierra T-056)

### T-057 · Isla: agenda de Hanna (tarjeta de aviso con Hecho/Posponer, resumen proactivo, lista de tareas y botón ¿Qué tengo pendiente?)

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** alta

Contrato 1.10 (T-056): reminder.due, nudge y task.changed; acciones con user.task {id, action: done|snooze|reopen|delete, minutes?}; lista en GET /v1/users/{user}/tasks; botón → POST /v1/proactive/check. Los textos ya vienen redactados por el personaje. Ver coordinacion/README.md.

**Archivos:** `pet/**`

**Depende de:** T-056

**Commits:** `21980b9`

### T-058 · Avisos de Hanna en Telegram cuando no estás al equipo (botones Hecho/Posponer, /tareas)

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** alta

El canal de Telegram escucha el WebSocket del núcleo y reenvía reminder.due y nudge marcados remote (política away: isla cerrada o inactividad de Windows). Nunca tareas privadas ni notificaciones. Contrato 1.11.

**Archivos:** `channels/**`, `core/tasks/**`, `core/system/presence.py`, `core/contract.py`, `server/routes/events.py`, `config.yml`, `tests/**`

**Última nota (claude):** Probado con el bot real: el aviso llegó a Telegram con botones, '⏰ 10 min' lo pospuso, /tareas no muestra las privadas y la privada no salió del equipo. En modo away (isla cerrada, 12 min inactivo) un aviso real llegó al móvil. Alias me/local = dueño para la isla. Silenciado WinError 10054.

### T-059 · Settings en menú 3 puntos, reply dock inferior, Liquid Glass blur, carátulas media e integraciones Core

**Responsable:** Antigravity (Gemini) · **Estado:** ✅ hecha · **Prioridad:** media

Rediseñar #stageSettingsCard en #menuBtn con toggles (Concentración, Liquid Glass, Privado, Reposo, Tema), acciones rápidas y diagnóstico Core (/v1/runs, /v1/proactive, reset sesión); ocultar switches en hero/laterales y quitar lista redundante de skins; anclar respuestas en #agentReplyDock con transición desde #bubble; blur real en #stageGlassFx; integración de carátulas multimedia; creación rápida de tareas (/v1/users/me/tasks) y subida de voz (/v1/voice, /v1/audio).

**Archivos:** `pet/web/index.html`, `pet/web/pet.css`, `pet/web/pet.js`

**Última nota (antigravity):** Implementado #stageSettingsCard, #agentReplyDock con animacion desde #bubble, #stageGlassFx blur, caratulas en #mediaWidget/#briefMediaCover e integraciones /v1/voice, /v1/audio, /v1/runs, /v1/proactive, /v1/users/me/tasks y reset de sesion.

### T-060 · Carátulas de lo que suena y «Mientras no estabas» al volver al equipo

**Responsable:** Claude Code · **Estado:** ✅ hecha · **Prioridad:** media

artwork y album en system.media (SMTC, solo al cambiar de canción) y GET /v1/system/media/artwork; nudge kind welcome al volver tras welcome_minutes; el resumen no repite lo recién avisado. Contrato 1.12.

**Archivos:** `core/system/**`, `core/tasks/**`, `server/routes/system.py`, `core/contract.py`, `personas/dva/persona.yml`, `config.yml`, `tests/**`

**Última nota (claude):** Carátula en vivo: Spotify 'Aguanta Corazón' → 200 image/png 207 KB por /v1/system/media/artwork, con CORS para la mascota; pet.js ya lee 'artwork' (resolveMediaCoverCandidate), pero el index.html servido no tiene los <img> de portada. «Mientras no estabas» y el resumen sin repetir lo recién avisado con tests. 473 tests.

### T-061 · Isla recogida: foco momentáneo en el hero al llegar una notificación o cambiar de canción

**Responsable:** Antigravity (Gemini) · **Estado:** ⬜ pendiente · **Prioridad:** alta

Pedido por el usuario. Solo en modo isla (notch recogido): al llegar system.notification o al cambiar de canción (system.media con otro title/artist; isNewTrack en updateMedia) expandir unos segundos y mostrarlo en el panel hero, y volver a recoger. Si la isla ya está expandida o el usuario interactúa, no cambiar de vista. Hoy: onNotification expande a 'notifs' 5 s (pet.js ~1826) y el cambio de canción solo hace previewBrief('media') (~2260), sin expandir. No en pausa/reanudar ni en avance de posición; respetar focusActive. El backend no cambia: los eventos ya llevan todo.

**Archivos:** `pet/**`

**Última nota (claude):** creada

### T-062 · Isla: arreglos menores que vio Claude (doble POST /v1/focus, errores de fetch silenciados, aviso de formato)

**Responsable:** Antigravity (Gemini) · **Estado:** ⬜ pendiente · **Prioridad:** media

1) Al activar concentración la isla envía POST /v1/focus dos veces seguidas y luego un DELETE /v1/focus que da 404 (log del Core, 14/11 21:03): ¿doble clic o doble envío? 2) Los fetch a /v1/system, /v1/system/notifications, etc. tienen catch vacío: registrar el error en consola para que un fallo (Core apagado, CORS) no pase desapercibido; hoy la isla queda vacía sin explicación. Ideal: indicar 'Core desconectado' en la isla. 3) Aviso: Claude ejecutó por error 'ruff format' sobre pet/tools/pixelize.py (solo estilo: comillas y saltos de línea, sin cambiar lógica); revísalo. Detalle en coordinacion/README.md (T-055, T-060).

**Archivos:** `pet/**`

**Última nota (claude):** creada
