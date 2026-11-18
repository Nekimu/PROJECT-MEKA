"""Dependencias compartidas por las rutas: el motor, la autenticación y las subidas."""

from pathlib import Path

from fastapi import Depends, HTTPException, Request, UploadFile

from core.engine import MekaEngine
from server.security import require_token

# Para `dependencies=` de las rutas que necesitan token
AUTH = [Depends(require_token)]


def get_engine(request: Request) -> MekaEngine:
    return request.app.state.engine


OWNER_ALIASES = {"me", "local"}


def resolve_user(user: str, request: Request) -> str:
    """`me` (o `local`) = el dueño: el primer ID de ALLOWED_USER_IDS, o "local" si no hay.
    La mascota no conoce tu ID de Telegram; así ve las mismas tareas que el bot."""
    return request.app.state.local_user if user in OWNER_ALIASES else user


async def save_upload(upload: UploadFile, request: Request) -> Path:
    """Guarda la subida en temp/uploads cortando si supera `server.max_upload_mb`."""
    engine = get_engine(request)
    max_upload = request.app.state.max_upload
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
