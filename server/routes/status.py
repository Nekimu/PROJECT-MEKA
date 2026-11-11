"""Estado del núcleo y del personaje activo."""

from fastapi import APIRouter, Request

from core.contract import CONTRACT_VERSION
from server.deps import AUTH, get_engine

router = APIRouter(prefix="/v1", tags=["estado"])


@router.get("/health")
def health(request: Request):
    engine = get_engine(request)
    return {
        "status": "ok",
        "version": request.app.version,
        "contract": CONTRACT_VERSION,
        "persona": engine.persona.id,
        "brain": engine.ai.describe(),
        "clients": engine.bus.subscribers,
    }


@router.get("/persona", dependencies=AUTH)
def persona(request: Request):
    """Nombre, frases y avatar del personaje activo (sin su prompt)."""
    return get_engine(request).persona.public()
