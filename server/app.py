"""Servidor local de MEKA Core: API REST + WebSocket de eventos.

Todos los canales (Telegram, MCP, la mascota, una futura app móvil) son clientes de
este servidor. Por defecto solo escucha en 127.0.0.1; para usarlo desde otro equipo
(red local o Tailscale) hace falta un token (`MEKA_API_TOKEN`).

Documentación interactiva de la API: http://127.0.0.1:8765/docs
"""

import asyncio
import contextlib
import hmac
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from core.config import default_user, is_loopback
from core.engine import MekaEngine, UnsupportedFileError
from core.events import EMOTIONS, OUTBOUND_EVENTS
from core.logger import setup_logger

logger = setup_logger("Server")

API_VERSION = "1"
# La mascota (Tauri) y las páginas servidas desde este mismo equipo
DEFAULT_ORIGINS = re.compile(
    r"^(tauri://localhost|https?://tauri\.localhost|https?://(localhost|127\.0\.0\.1)(:\d+)?)$"
)


class ConfigError(RuntimeError):
    """Configuración del servidor insegura o inválida."""


# ---------------------------------------------------------------------- modelos de la API


class ChatRequest(BaseModel):
    session: str = Field(
        min_length=1, max_length=200, description="Conversación (p. ej. telegram:123)"
    )
    user: str = Field(min_length=1, max_length=200, description="Dueño de la memoria")
    text: str = Field(min_length=1, max_length=20_000)
    audio: bool = Field(True, description="Sintetizar las frases marcadas con [AUDIO]")
    use_memory: bool = True


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5_000)


class FactRequest(BaseModel):
    fact: str = Field(min_length=1, max_length=2_000)


class EventRequest(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------- seguridad


def server_token(config: dict) -> str:
    """Token de la API. Sin token, el servidor solo puede escuchar en este equipo."""
    server = config.get("server", {})
    token = str(server.get("token") or "").strip()
    host = server.get("host", "127.0.0.1")
    if not token and not is_loopback(host):
        raise ConfigError(
            f"server.host es {host!r} pero no hay MEKA_API_TOKEN en .env. "
            "Sin token, cualquiera en tu red podría hablar con MEKA y leer su memoria."
        )
    return token


def _bearer(value: str | None) -> str:
    if value and value.lower().startswith("bearer "):
        return value[7:].strip()
    return ""


class OriginGuard:
    """Rechaza peticiones de webs ajenas (un navegador puede llamar a localhost desde cualquier
    página). Las herramientas sin navegador (Telegram, MCP, curl) no envían Origin."""

    def __init__(self, app, extra_origins: list[str]):
        self.app = app
        self.extra = {origin.rstrip("/") for origin in extra_origins}

    def allowed(self, origin: str | None) -> bool:
        return not origin or bool(DEFAULT_ORIGINS.match(origin)) or origin in self.extra

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            headers = dict(scope.get("headers") or [])
            origin = headers.get(b"origin", b"").decode("latin-1") or None
            if not self.allowed(origin):
                logger.warning(f"Conexión rechazada desde un origen no permitido: {origin}")
                if scope["type"] == "websocket":
                    await send({"type": "websocket.close", "code": 1008})
                    return
                response = JSONResponse({"detail": "Origen no permitido"}, status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------- aplicación


def create_app(
    config: dict, engine: MekaEngine | None = None, *, startup_checks: bool = True
) -> FastAPI:
    token = server_token(config)
    server = config.get("server", {})
    max_upload = int(server.get("max_upload_mb", 20)) * 1024 * 1024
    local_user = default_user(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.engine is None:
            app.state.engine = MekaEngine(config)
        engine = app.state.engine
        engine.clear_temp()
        if startup_checks:
            await asyncio.to_thread(engine.check_health)
        logger.info(f"MEKA Core listo con {engine.persona.name} ({engine.persona.id})")
        if not token:
            logger.warning("Sin MEKA_API_TOKEN: solo este equipo puede usar la API.")
        try:
            yield
        finally:
            engine.close()
            logger.info(f"{engine.persona.name} se ha ido a descansar.")

    app = FastAPI(
        title="MEKA Core",
        version=API_VERSION,
        description="Núcleo local de Project MEKA: personaje, memoria, IA y voz.",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.add_middleware(OriginGuard, extra_origins=server.get("allowed_origins") or [])

    def get_engine(request: Request) -> MekaEngine:
        return request.app.state.engine

    def check_token(supplied: str):
        if token and not hmac.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o ausente")

    def require_token(request: Request):
        check_token(_bearer(request.headers.get("authorization")))

    auth = [Depends(require_token)]

    async def save_upload(upload: UploadFile, engine: MekaEngine) -> Path:
        """Guarda la subida en temp/uploads cortando si supera `server.max_upload_mb`."""
        path = engine.new_upload_path(Path(upload.filename or "").suffix)
        size = 0
        try:
            with path.open("wb") as out:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_upload:
                        raise HTTPException(413, "Archivo demasiado grande")
                    out.write(chunk)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return path

    # ------------------------------------------------------------------ estado

    @app.get("/v1/health", tags=["estado"])
    def health(request: Request):
        engine = get_engine(request)
        return {
            "status": "ok",
            "version": API_VERSION,
            "persona": engine.persona.id,
            "brain": engine.ai.describe(),
            "clients": engine.bus.subscribers,
        }

    @app.get("/v1/persona", tags=["estado"], dependencies=auth)
    def persona(request: Request):
        """Nombre, frases y avatar del personaje activo (sin su prompt)."""
        return get_engine(request).persona.public()

    # ------------------------------------------------------------------ conversación

    @app.post("/v1/chat", tags=["conversación"], dependencies=auth)
    async def chat(body: ChatRequest, request: Request):
        replies = await get_engine(request).chat(
            body.session, body.user, body.text, audio=body.audio, use_memory=body.use_memory
        )
        return {"replies": [r.to_dict() for r in replies]}

    @app.post("/v1/voice", tags=["conversación"], dependencies=auth)
    async def voice(
        request: Request,
        file: UploadFile = File(...),
        session: str = Form(...),
        user: str = Form(...),
        audio: bool = Form(True),
    ):
        """Nota de voz → transcripción (Whisper) → respuesta."""
        engine = get_engine(request)
        path = await save_upload(file, engine)
        try:
            transcription, replies = await engine.voice(session, user, path, audio=audio)
        finally:
            path.unlink(missing_ok=True)
        return {"transcription": transcription, "replies": [r.to_dict() for r in replies]}

    @app.post("/v1/files", tags=["conversación"], dependencies=auth)
    async def analyze_file(
        request: Request,
        file: UploadFile = File(...),
        session: str = Form(...),
        user: str = Form(...),
        caption: str | None = Form(None),
    ):
        """Imagen (visión) o documento (PDF, DOCX, XLSX, TXT, MD, CSV)."""
        engine = get_engine(request)
        file_name = Path(file.filename or "archivo").name
        path = await save_upload(file, engine)
        try:
            replies = await engine.analyze_file(session, user, path, file_name, caption)
        except UnsupportedFileError as e:
            raise HTTPException(415, f"Tipo de archivo no soportado: {e}") from e
        finally:
            path.unlink(missing_ok=True)
        return {"replies": [r.to_dict() for r in replies]}

    @app.post(
        "/v1/sessions/{session}/reset",
        tags=["conversación"],
        dependencies=auth,
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def reset(session: str, request: Request):
        get_engine(request).reset(session)

    # ------------------------------------------------------------------ voz

    @app.post("/v1/speech", tags=["voz"], dependencies=auth)
    async def speech(body: SpeechRequest, request: Request):
        """Sintetiza un texto con la voz del personaje. Devuelve el id para GET /v1/audio."""
        return {"audio": await get_engine(request).speak(body.text)}

    @app.get("/v1/audio/{audio_id}", tags=["voz"], dependencies=auth)
    def audio(audio_id: str, request: Request):
        """Descarga un audio generado (una sola vez: después se borra)."""
        path = get_engine(request).take_audio(audio_id)
        if path is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio no encontrado o caducado")
        media_type = {".ogg": "audio/ogg", ".mp3": "audio/mpeg", ".wav": "audio/wav"}
        return FileResponse(
            path,
            media_type=media_type.get(path.suffix, "application/octet-stream"),
            filename=path.name,
            background=BackgroundTask(path.unlink, missing_ok=True),
        )

    # ------------------------------------------------------------------ memoria

    @app.get("/v1/users/{user}/memories", tags=["memoria"], dependencies=auth)
    async def memories(user: str, request: Request, q: str | None = None):
        """Todos los recuerdos, o con `q` los relacionados (por significado y por palabras)."""
        engine = get_engine(request)
        if q:
            return {"memories": await engine.search_memories(user, q[:2_000])}
        return {"memories": engine.memories(user)}

    @app.post("/v1/users/{user}/memories", tags=["memoria"], dependencies=auth)
    def remember(user: str, body: FactRequest, request: Request):
        return {"added": get_engine(request).remember(user, body.fact)}

    @app.delete("/v1/users/{user}/memories", tags=["memoria"], dependencies=auth)
    def forget(user: str, request: Request):
        return {"removed": get_engine(request).forget(user)}

    # ------------------------------------------------------------------ eventos

    def validate_event(type_: str, data: dict) -> dict:
        if type_ not in OUTBOUND_EVENTS:
            raise ValueError(f"Evento desconocido: {type_!r}. Válidos: {sorted(OUTBOUND_EVENTS)}")
        emotion = data.get("emotion")
        if emotion is not None and emotion not in EMOTIONS:
            raise ValueError(f"Emoción desconocida: {emotion!r}. Válidas: {sorted(EMOTIONS)}")
        return data

    @app.post(
        "/v1/events", tags=["eventos"], dependencies=auth, status_code=status.HTTP_202_ACCEPTED
    )
    def publish(body: EventRequest, request: Request):
        """Un agente externo (MCP, scripts) avisa a la mascota: agent.working, agent.done..."""
        try:
            data = validate_event(body.type, body.data)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        engine = get_engine(request)
        engine.bus.publish(body.type, **data)
        return {"delivered": engine.bus.subscribers}

    @app.websocket("/v1/events")
    async def events(websocket: WebSocket):
        """Canal en tiempo real de la mascota y las apps (contrato en docs/VISION.md)."""
        supplied = websocket.query_params.get("token") or _bearer(
            websocket.headers.get("authorization")
        )
        if token and not hmac.compare_digest(supplied.encode(), token.encode()):
            await websocket.close(code=1008)
            return

        engine: MekaEngine = websocket.app.state.engine
        await websocket.accept()
        queue = engine.bus.subscribe()
        client = "cliente"

        async def pump():
            while True:
                await websocket.send_json(await queue.get())

        sender = asyncio.create_task(pump())
        try:
            while True:
                try:
                    message = json.loads(await websocket.receive_text())
                    type_ = message["type"]
                    data = message.get("data") or {}
                except (ValueError, KeyError, TypeError):
                    logger.warning("Mensaje WebSocket no válido; se ignora")
                    continue

                if type_ == "client.hello":
                    client = str(data.get("client") or client)[:50]
                    logger.info(f"Cliente conectado: {client}")
                elif type_ == "user.message" and str(data.get("text") or "").strip():
                    replies = await engine.chat(
                        f"ws:{client}", local_user, str(data["text"])[:20_000], audio=False
                    )
                    if not engine.broadcast:  # Si no se difunde, al menos lo recibe quien habló
                        text = " ".join(r.text for r in replies)
                        await websocket.send_json(
                            {"type": "message", "data": {"text": text, "emotion": "happy"}}
                        )
                else:
                    logger.debug(f"Mensaje de cliente sin manejar: {type_}")
        except WebSocketDisconnect:
            pass
        finally:
            engine.bus.unsubscribe(queue)
            sender.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await sender
            logger.info(f"Cliente desconectado: {client}")

    return app


def build_server(config: dict, engine: MekaEngine | None = None):
    """Servidor uvicorn listo para `await server.serve()`."""
    import uvicorn

    server = config.get("server", {})
    app = create_app(config, engine)
    return uvicorn.Server(
        uvicorn.Config(
            app,
            host=server.get("host", "127.0.0.1"),
            port=int(server.get("port", 8765)),
            log_level=str(config.get("app", {}).get("log_level", "INFO")).lower(),
            ws_max_size=1024 * 1024,
        )
    )
