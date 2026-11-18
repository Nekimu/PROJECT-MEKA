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


LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def host_name(value: str) -> str:
    """'127.0.0.1:8765' → '127.0.0.1'; '[::1]:8765' → '::1'."""
    value = value.strip().lower()
    if value.startswith("["):
        return value[1 : value.find("]")] if "]" in value else value
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def add_browser_access(app, extra_origins: list[str], *, check_host=False, extra_hosts=()):
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
    # Por fuera de CORS: lo ajeno ni llega. `check_host`: sin token, solo nombres de este equipo
    # (una web externa puede apuntar su dominio a 127.0.0.1: «DNS rebinding»)
    hosts = (LOCAL_HOSTS | {h.lower() for h in extra_hosts}) if check_host else None
    app.add_middleware(OriginGuard, extra_origins=extra, hosts=hosts)


class OriginGuard:
    """Rechaza peticiones de webs ajenas (un navegador puede llamar a localhost desde cualquier
    página). Las herramientas sin navegador (Telegram, MCP, curl) no envían Origin."""

    def __init__(self, app, extra_origins: list[str], hosts: frozenset | set | None = None):
        self.app = app
        self.extra = {origin.rstrip("/") for origin in extra_origins}
        self.hosts = hosts  # None: no se comprueba (hay token)

    def allowed(self, origin: str | None) -> bool:
        return not origin or bool(DEFAULT_ORIGINS.match(origin)) or origin in self.extra

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            headers = dict(scope.get("headers") or [])
            origin = headers.get(b"origin", b"").decode("latin-1") or None
            host = host_name(headers.get(b"host", b"").decode("latin-1"))
            problem = None
            if not self.allowed(origin):
                problem = f"origen no permitido: {origin}"
            elif self.hosts is not None and host and host not in self.hosts:
                problem = f"Host ajeno: {host}"
            if problem:
                logger.warning(f"Conexión rechazada ({problem})")
                if scope["type"] == "websocket":
                    await send({"type": "websocket.close", "code": 1008})
                    return
                response = JSONResponse({"detail": "Origen no permitido"}, status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
