"""Memoria a largo plazo de cada usuario."""

from fastapi import APIRouter, Query, Request

from server.deps import AUTH, get_engine
from server.schemas import FactRequest

router = APIRouter(prefix="/v1/users/{user}/memories", tags=["memoria"], dependencies=AUTH)


@router.get("")
async def memories(
    user: str,
    request: Request,
    q: str | None = None,
    include_private: bool = Query(
        True, description="false para clientes que sacan los datos del equipo (MCP, Telegram)"
    ),
):
    """Todos los recuerdos, o con `q` los relacionados (por significado y por palabras)."""
    engine = get_engine(request)
    if q:
        found = await engine.search_memories(user, q[:2_000], include_private=include_private)
        return {"memories": found}
    return {"memories": engine.memories(user, include_private=include_private)}


@router.post("")
def remember(user: str, body: FactRequest, request: Request):
    return {"added": get_engine(request).remember(user, body.fact, private=body.private)}


@router.delete("")
def forget(user: str, request: Request):
    return {"removed": get_engine(request).forget(user)}
