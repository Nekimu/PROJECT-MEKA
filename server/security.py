"""Seguridad del servidor: token de la API y bloqueo de webs ajenas (Origin)."""

import hmac
import re

from fastapi import HTTPException, Request, WebSocket, status
from fastapi.responses import JSONResponse

from core.config import is_loopback
from core.logger import setup_logger

logger = setup_logger("Server")

# La mascota (app de Go: http://127.0.0.1:<puerto>; antes Tauri) y las páginas de este equipo
DEFAULT_ORIGINS = re.compile(
    r"^(tauri://localhost|https?://tauri\.localhost|https?://(localhost|127\.0\.0\.1)(:\d+)?)$"
)


class ConfigError(RuntimeError):
    """Configuración del servidor insegura o inválida."""


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


def bearer(value: str | None) -> str:
    if value and value.lower().startswith("bearer "):
        return value[7:].strip()
    return ""


def token_matches(expected: str, supplied: str) -> bool:
    """Sin token configurado todo vale (solo escucha en este equipo)."""
    return not expected or hmac.compare_digest(supplied.encode(), expected.encode())


def require_token(request: Request):
    """Dependencia de FastAPI para las rutas protegidas (cabecera Authorization: Bearer)."""
    if not token_matches(request.app.state.token, bearer(request.headers.get("authorization"))):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o ausente")


def websocket_authorized(websocket: WebSocket) -> bool:
    """El WebSocket acepta el token por `?token=` (los navegadores no envían cabeceras)."""
    supplied = websocket.query_params.get("token") or bearer(websocket.headers.get("authorization"))
    return token_matches(websocket.app.state.token, supplied)


def add_browser_access(app, extra_origins: list[str]):
    """Deja que las páginas permitidas lean la API REST (CORS) y rechaza las demás.

    La mascota se sirve desde otro puerto (`127.0.0.1:<aleatorio>`): para el navegador es otro
    origen, y sin estas cabeceras solo le llegaba el WebSocket (ni `GET /v1/system` al
    arrancar ni las acciones con POST). CORS solo abre la lectura a los orígenes que ya
    admite `OriginGuard`; el token sigue siendo obligatorio si está configurado.
    """
    from fastapi.middleware.cors import CORSMiddleware

    extra = [origin.rstrip("/") for origin in extra_origins]
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=DEFAULT_ORIGINS.pattern,
        allow_origins=extra,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )
    app.add_middleware(OriginGuard, extra_origins=extra)  # Por fuera: lo ajeno ni llega a CORS


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
