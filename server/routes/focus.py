"""Modo concentración: MEKA retiene lo que distrae durante un bloque de trabajo."""

from fastapi import APIRouter, HTTPException, Request

from server.deps import AUTH, get_engine
from server.schemas import FocusRequest

router = APIRouter(prefix="/v1/focus", tags=["concentración"], dependencies=AUTH)


@router.get("")
def status(request: Request):
    """¿Hay una sesión activa? Cuánto queda y cuántos avisos se han retenido."""
    return get_engine(request).focus.status()


@router.post("")
async def start(body: FocusRequest, request: Request):
    """Empieza (o amplía) una sesión. Publica focus.started."""
    try:
        return await get_engine(request).focus.start(body.minutes)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.delete("")
async def stop(request: Request):
    """Termina la sesión. Publica focus.ended con el resumen de lo retenido."""
    summary = get_engine(request).focus.stop("user")
    if summary is None:
        raise HTTPException(404, "No hay ninguna sesión de concentración activa")
    return summary
