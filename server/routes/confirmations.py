"""Permisos antes de acciones delicadas (agent.confirm → user.confirm → agent.confirmed)."""

from fastapi import APIRouter, HTTPException, Request, status

from server.deps import AUTH, get_engine
from server.schemas import ConfirmationAnswer, ConfirmationRequest

router = APIRouter(prefix="/v1/confirmations", tags=["permisos"], dependencies=AUTH)


@router.get("")
def pending(request: Request):
    """Permisos que esperan respuesta (para un cliente que se acaba de conectar)."""
    return {"pending": get_engine(request).confirmations.pending()}


@router.post("")
async def ask(body: ConfirmationRequest, request: Request):
    """Pide permiso al usuario y **espera** su respuesta (la mascota muestra el diálogo).
    Sin respuesta a tiempo, `approved` es false."""
    approved = await get_engine(request).confirmations.ask(
        body.action, timeout=body.timeout, details=body.details
    )
    return {"approved": approved}


@router.post("/{confirmation_id}")
def answer(confirmation_id: str, body: ConfirmationAnswer, request: Request):
    """Responde a un permiso pendiente (Telegram, el móvil o cualquier cliente sin WebSocket)."""
    if not get_engine(request).confirmations.resolve(confirmation_id, body.approved, by="api"):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Permiso no encontrado, ya resuelto o caducado"
        )
    return {"resolved": True}
