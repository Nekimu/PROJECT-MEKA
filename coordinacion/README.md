# Coordinación Claude Code ↔ Antigravity

Este directorio es el **punto de consulta compartido** entre los dos agentes que trabajan en Project MEKA:

| Agente | Rol |
|---|---|
| **Claude Code** | Backend, IA, agente ("manos") y canales |
| **Antigravity (Gemini)** | Frontend, UI/UX y arte |

| Archivo | Qué es |
|---|---|
| [`TABLERO.md`](TABLERO.md) | Vista del tablero. **Se genera solo**; no lo edites a mano. |
| [`tareas.json`](tareas.json) | Fuente de verdad: tareas, estados, historial y reparto de áreas. |
| [`../scripts/tareas.py`](../scripts/tareas.py) | Herramienta para leer y cambiar el tablero (solo biblioteca estándar). |

## Reglas

1. **Cada uno solo toca su área** (tabla de abajo). Si necesitas algo del otro lado, **crea una tarea para el otro agente**; no edites sus archivos.
2. **Todo trabajo tiene una tarea `T-XXX`**, y cada commit la menciona en el mensaje.
3. **Archivos compartidos** (`README.md`, `CHANGELOG.md`, `docs/*.md`, `requirements*.txt`, `.github/**`, `coordinacion/**`): edítalos solo si tu tarea los nombra en `archivos`, y en commits pequeños.
4. **El contrato (abajo) solo cambia de forma aditiva** y con aviso previo: una tarea que lo describa, antes de publicar el cambio.
5. **Un commit = un área.** El hook `commit-msg` rechaza commits que mezclen archivos de los dos agentes.
6. **Módulos pequeños.** En el backend ningún `.py` pasa de 300 líneas (`tests/test_modularidad.py`); si crece, se divide por responsabilidades.

## Reparto de archivos

| Área | Responsable | Archivos exclusivos |
|---|---|---|
| Frontend, UI/UX y arte | Antigravity | `pet/web/**`, `pet/src-tauri/**`, `pet/tools/**`, `pet/README.md`, `docs/assets/**`, `docs/screenshots/**`, `tests/test_pet_skins.py` |
| Backend, IA, agente y canales | Claude Code | `core/**`, `ai/**`, `server/**`, `channels/**`, `personas/**`, `scripts/**`, `run.py`, `config.yml`, `tests/**` (excepto `test_pet_skins.py`), `.claude/**` |

El reparto vive en `tareas.json` → `areas`. Para saber de quién es un archivo:

```bash
python scripts/tareas.py propietario pet/web/pet.js server/app.py README.md
```

## Uso del tablero

```bash
python scripts/tareas.py tablero                                   # Regenera TABLERO.md y muestra lo abierto
python scripts/tareas.py lista --agente antigravity                # Tus tareas
python scripts/tareas.py nueva --agente antigravity --titulo "Rediseño del menú" --prioridad alta --archivos pet/web/pet.css
python scripts/tareas.py estado T-011 en_progreso --agente antigravity --nota "Empiezo el diálogo"
python scripts/tareas.py estado T-011 hecha --agente antigravity
```

Estados: `pendiente` · `en_progreso` · `bloqueada` · `en_revision` · `hecha`.

### Actualización automática

| Qué pasa | Efecto en el tablero |
|---|---|
| Commit que menciona `T-011` | La tarea pasa a `en_progreso` y guarda el commit |
| Commit con `cierra T-011` (o `closes`, `completa`, `resuelve`, `fixes`) | La tarea pasa a `hecha` |
| Commit que mezcla archivos de las dos áreas | El hook `commit-msg` lo rechaza |
| Claude Code intenta editar un archivo de Antigravity | Su hook `PreToolUse` lo bloquea |
| Claude Code empieza una sesión | Lee el tablero al arrancar (hook `SessionStart`) |
| Claude Code termina un turno | Sincroniza el tablero con git (hook `Stop`) |

Los hooks de git están en [`.githooks/`](../.githooks) y se activan una vez por clon:

```bash
git config core.hooksPath .githooks
```

> Ejemplo de mensaje: `feat(pet): diálogo de confirmación (cierra T-011)`.

## Contrato de integración (Frontend ↔ Backend)

Definido en `core/events.py` y `server/routes/` (eventos en `server/routes/events.py`); detalle en [`docs/VISION.md`](../docs/VISION.md#contrato-de-eventos).

**WebSocket** `ws://127.0.0.1:8765/v1/events`

- Core → Frontend (`OUTBOUND_EVENTS`): `agent.working`, `agent.done`, `agent.error`, `agent.confirm`, `agent.confirmed`, `message`, `emotion`, `budget.low`.
- Emociones válidas (`EMOTIONS`): `idle`, `happy`, `working`, `thinking`, `sleeping`, `eating`, `error`, `celebrate`, `sad`.
- Frontend → Core: `client.hello`, `user.message` y `user.confirm` (`{"id": "...", "approved": true/false}`, implementado en **T-003**).

**REST** `http://127.0.0.1:8765/v1/...`

- El frontend puede consumir `/v1/health`, `/v1/persona`, `/v1/chat`, `/v1/speech`, `/v1/audio/{id}` y `/v1/users/{user}/memories`, respetando `OriginGuard` y el token (`Authorization: Bearer` o `?token=`).

**Ya publicados (aditivos):**

| Tarea | Cambio | Qué implica para el frontend |
|---|---|---|
| T-021 | Si el cerebro falla, el `message` llega con `"emotion": "error"`, y si el núcleo revienta se envía `emotion: error`. Si no entendió una nota de voz: `emotion: sad`. | Antes la mascota podía quedarse en `thinking` para siempre. Basta con tratar `error` y `sad`, que ya están en `EMOTIONS`. |
| T-019 | `private` (opcional, `false`) en `POST /v1/chat`, `/v1/voice`, `/v1/files` y en `user.message` del WebSocket (`{"text": "...", "private": true}`). Cada respuesta trae `"private": true/false`. | Opcional: un modo privado en la mascota y un 🔒 en las respuestas privadas. |
| T-060 | **Contrato 1.12** (solo campos opcionales). `system.media` añade `album?` y `artwork?` (URL relativa, p. ej. `/v1/system/media/artwork?v=b972215e0581`; cambia con cada carátula, cacheable). `nudge.kind` puede ser `welcome` (al volver al equipo). | Mostrar la carátula en la tarjeta de música (`GET` a la URL de `artwork`, con el token si lo hay; 404 = sin carátula → icono por defecto). Tarjeta de bienvenida para `kind: welcome`. Nota: la isla hace `POST /v1/focus` dos veces seguidas y luego un `DELETE` con 404 (¿doble clic o doble envío?). |
| T-058 | **Contrato 1.11** (solo campos opcionales). `reminder.due` añade `private?` y `remote?`; `nudge` añade `remote?` y `shareable?` (texto sin tareas privadas ni notificaciones, para el móvil). `GET /v1/proactive` dice si ahora avisaría al móvil (`remote`, `at_desk`, `idle_seconds`). | Nada obligatorio. La isla debe enviar `client.hello` con `client: "pet"` (ya lo hace): así el núcleo sabe que estás al equipo y no duplica avisos en el móvil. |
| T-056 | **Contrato 1.10.** Nuevos eventos: `task.changed {id, status, action}`, `reminder.due {id, title, text, due?}` y `nudge {text, kind, tasks, overdue, notifications}`. Nuevo `user.task {id, action, minutes?}` (`done`, `reopen`, `snooze`, `delete`). REST: `GET/POST /v1/users/{user}/tasks`, `POST /v1/users/{user}/tasks/{id}`, `GET /v1/proactive`, `POST /v1/proactive/check`. En modo concentración `reminder.due` y `task.changed` pasan; `nudge` se retiene. | Tarjeta de aviso con «Hecho» y «Posponer 10 min» (`user.task`); tarjeta del resumen; lista de tareas en la isla (recargar al recibir `task.changed`); botón «¿Qué tengo pendiente?» → `POST /v1/proactive/check`. El texto (`text`) ya viene redactado por el personaje. |
| T-055 | **Sin cambio de contrato.** El Core envía CORS a los orígenes permitidos (`127.0.0.1:<puerto>` de la app de Go): `fetch` a `/v1/system`, `/v1/health`, `/v1/confirmations` y los POST de acciones ya funcionan desde la mascota. Al conectarse, el WebSocket envía primero `system.media` y `system.battery` con el estado actual. | La isla puede pintar la música al recibir ese primer evento; las notificaciones que ya había siguen en `GET /v1/system/notifications`. Antes esas peticiones fallaban en silencio (`catch` vacío): conviene registrar el error en la consola. |
| T-053 | **Sin cambio de contrato.** `POST /v1/voice` puede devolver `"transcription": null` **con** respuestas: el cerebro entendió el audio sin transcribirlo. Solo es un fallo si además `replies` viene vacío. | Si la isla muestra lo que se dijo en una nota de voz, no asumir que hay transcripción. |
| T-050 | **Contrato 1.9. Modo concentración.** `focus.started {until, minutes}` y `focus.ended {reason, held, notifications}`; entrada `user.focus {action: start\|stop, minutes?}`; `GET/POST/DELETE /v1/focus`. Mientras está activo, el Core **no envía** notificaciones, música, batería normal, `message` de otros canales ni `agent.working/done`; **sí** envía permisos, errores, `emotion`, apps de `focus.allow_apps` y batería crítica. Si escribes en la mascota, la respuesta te llega directa. | Botón para empezar/terminar, cuenta atrás en la isla y tarjeta de resumen al terminar (T-051). Con la concentración activa, la isla puede quedarse quieta. |
| T-046 | **Contrato 1.8.** `system.notification {id, app, title?, body?, time}` por cada notificación nueva de Windows y `system.notification_removed {id}`; entrada `user.notification {id, action: dismiss\|open}`; `GET /v1/system/notifications` (al conectar) y `POST /v1/system/notifications/{id}`. Privadas: solo por el WebSocket local; códigos de verificación y datos sensibles ya ocultos. No se pueden pulsar botones de otras apps (Windows no lo permite). | Tarjetas de notificación en la pila tipo Brief (T-047): mostrar, descartar y abrir la app. |
| T-044 | **Contrato 1.7.** `system.media {playing, title?, artist?, app?, position?, duration?}` y `system.battery {percent, charging}` (solo cuando cambian); entrada `user.media {action: play_pause\|next\|previous}`; `GET /v1/system` y `POST /v1/system/media`. | Para la Dynamic Island (T-045): mostrar la canción y la batería; la posición, avanzarla en local. |
| T-005 | **Contrato 1.6.** `POST /v1/hands/{carpeta}/write|move|delete|mkdir|undo` y `GET .../history`; las carpetas indican `writable`. Cada cambio pide permiso (`agent.confirm` con `details: {folder, op, paths}`). **Inactivo**: ninguna carpeta es `writable` hasta resolver el aislamiento (T-042). | Nada por ahora. Cuando se active, el diálogo de permisos ya sirve tal cual; `details` permite mostrar las rutas. |
| T-004 | **Contrato 1.5.** `GET /v1/hands` (carpetas autorizadas), `/v1/hands/{carpeta}/list|read|search`. Solo lectura; las búsquedas emiten `agent.working` → `agent.done` (o `agent.error`). | Opcional: un panel de "archivos" en la mascota; las búsquedas ya animan a la mascota con los eventos de siempre. |
| T-007 | **`GET /v1/contract`** (público): versión del contrato, eventos con sus campos y tipos, emociones y todas las rutas REST (con o sin token). `/v1/health` incluye la versión (`"contract": "1.9"`). `POST /v1/events` valida los campos contra el contrato. | Leer eventos y emociones de ahí en lugar de copiarlos; al conectar, comparar la versión mayor (1.x) para detectar incompatibilidades. |
| T-003 | `agent.confirm` trae `{id, action, timeout, expires_at, details?}`. Nuevo `agent.confirmed {id, approved, by}` cuando se resuelve (desde cualquier cliente o por caducidad: `by: "timeout"`). `GET /v1/confirmations` lista los pendientes; `POST /v1/confirmations/{id} {approved}` responde sin WebSocket. Sin respuesta = **no**. `POST /v1/events` ya no acepta `agent.confirm` a mano. | Usar `timeout` (no 25 s fijos) para el diálogo; cerrarlo al recibir `agent.confirmed`; al conectar, pedir `GET /v1/confirmations` para mostrar los pendientes. |
| T-031 | Los recuerdos tienen marca privada. `GET /v1/users/{u}/memories?include_private=false` los oculta (MCP y Telegram ya lo usan); `POST` acepta `"private": true`. Lo dicho con `private` se guarda como privado. | Si la mascota muestra recuerdos, puede pedir todos (corre en el equipo); no reenviarlos fuera. |
| T-020 | Nuevo `GET /v1/runs?limit=&days=`: últimas llamadas a la IA (proveedor, modelo, latencia, tokens, ok) y resumen por proveedor. **Nunca incluye texto.** | Opcional: un panel de "salud del cerebro" o de consumo. |

**Cambios previstos (todos aditivos):**

| Tarea | Cambio |
|---|---|
| T-006 | Nuevo `GET/PUT /v1/pet/state` y evento `pet.state` |
