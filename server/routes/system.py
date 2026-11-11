"""Datos del sistema para la Dynamic Island: música en reproducción y batería."""

from fastapi import APIRouter, HTTPException, Request

from server.deps import AUTH, get_engine
from server.schemas import MediaAction, NotificationAction

router = APIRouter(prefix="/v1/system", tags=["sistema"], dependencies=AUTH)


@router.get("")
def snapshot(request: Request):
    """Último estado conocido (para un cliente que se acaba de conectar). `null` si no hay
    datos: sin música, sin batería o con `system.enabled: false`."""
    return get_engine(request).system.snapshot()


@router.get("/notifications")
def notifications(request: Request):
    """Notificaciones visibles ahora (más recientes primero), con la privacidad ya aplicada."""
    return {"notifications": get_engine(request).system.notifications()}


@router.post("/notifications/{notification_id}")
async def notification_action(notification_id: int, body: NotificationAction, request: Request):
    """Descartar una notificación o abrir la app que la envió."""
    try:
        done = await get_engine(request).system.notification_action(notification_id, body.action)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"done": done}


@router.post("/media")
async def media(body: MediaAction, request: Request):
    """Reproducir/pausar o cambiar de canción en el reproductor activo de Windows."""
    try:
        done = await get_engine(request).system.media_control(body.action)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"done": done}
