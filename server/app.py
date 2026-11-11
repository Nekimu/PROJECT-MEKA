"""Servidor local de MEKA Core: API REST + WebSocket de eventos.

Todos los canales (Telegram, MCP, la mascota, una futura app móvil) son clientes de
este servidor. Por defecto solo escucha en 127.0.0.1; para usarlo desde otro equipo
(red local o Tailscale) hace falta un token (`MEKA_API_TOKEN`).

Este módulo solo compone la aplicación; las rutas viven en `server/routes/` (una por
dominio) y la seguridad en `server/security.py`.

Documentación interactiva de la API: http://127.0.0.1:8765/docs
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import default_user
from core.engine import MekaEngine
from core.logger import setup_logger
from server.routes import ROUTERS
from server.security import ConfigError, OriginGuard, server_token

__all__ = ["API_VERSION", "ConfigError", "build_server", "create_app", "server_token"]

logger = setup_logger("Server")

API_VERSION = "1"


def create_app(
    config: dict, engine: MekaEngine | None = None, *, startup_checks: bool = True
) -> FastAPI:
    server = config.get("server", {})
    token = server_token(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.engine is None:
            app.state.engine = MekaEngine(config)
        engine = app.state.engine
        engine.clear_temp()
        if startup_checks:
            await asyncio.to_thread(engine.check_health)
        await engine.system.start()
        logger.info(f"MEKA Core listo con {engine.persona.name} ({engine.persona.id})")
        if not token:
            logger.warning("Sin MEKA_API_TOKEN: solo este equipo puede usar la API.")
        try:
            yield
        finally:
            await engine.system.stop()
            engine.close()
            logger.info(f"{engine.persona.name} se ha ido a descansar.")

    app = FastAPI(
        title="MEKA Core",
        version=API_VERSION,
        description="Núcleo local de Project MEKA: personaje, memoria, IA y voz.",
        lifespan=lifespan,
    )
    # Lo que las rutas necesitan de la configuración, sin depender de variables globales
    app.state.engine = engine
    app.state.token = token
    app.state.max_upload = int(server.get("max_upload_mb", 20)) * 1024 * 1024
    app.state.local_user = default_user(config)

    app.add_middleware(OriginGuard, extra_origins=server.get("allowed_origins") or [])
    for router in ROUTERS:
        app.include_router(router)
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
