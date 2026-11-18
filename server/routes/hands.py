"""Manos de MEKA (fase 3): leer carpetas autorizadas y, con permiso, cambiarlas."""

from fastapi import APIRouter, HTTPException, Query, Request

from core.hands import HandsError
from server.deps import AUTH, get_engine
from server.schemas import HandsMove, HandsPath, HandsWrite

router = APIRouter(prefix="/v1/hands", tags=["manos"], dependencies=AUTH)

PRIVATE = Query(True, description="false para clientes que sacan los datos del equipo (MCP)")


async def _safe(coro):
    try:
        return await coro
    except HandsError as e:
        raise HTTPException(e.status, str(e)) from e


@router.get("")
def folders(request: Request, include_private: bool = PRIVATE):
    """Carpetas autorizadas en config.yml (`hands.folders`)."""
    return {"folders": get_engine(request).hands.list_folders(include_private=include_private)}


@router.get("/{folder}/list")
async def list_files(
    folder: str,
    request: Request,
    path: str = ".",
    pattern: str | None = Query(None, description="Filtro tipo *.pdf"),
    include_private: bool = PRIVATE,
):
    hands = get_engine(request).hands
    return await _safe(hands.list(folder, path, pattern=pattern, include_private=include_private))


@router.get("/{folder}/read")
async def read_file(folder: str, path: str, request: Request, include_private: bool = PRIVATE):
    """Texto de un archivo (también PDF, DOCX y XLSX), recortado a `hands.max_read_chars`."""
    hands = get_engine(request).hands
    return await _safe(hands.read(folder, path, include_private=include_private))


@router.get("/{folder}/search")
async def search(
    folder: str,
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    content: bool = Query(True, description="Buscar también dentro de los archivos de texto"),
    include_private: bool = PRIVATE,
):
    """Busca por nombre (y contenido). La mascota muestra agent.working → agent.done."""
    hands = get_engine(request).hands
    return await _safe(hands.search(folder, q, content=content, include_private=include_private))


# ---------------------------------------------------------------------- cambios (T-005)
# Solo en carpetas con `writable: true`. Cada petición ESPERA a que el usuario dé permiso
# (agent.confirm en la mascota) y deja un punto de restauración. Sin permiso: 403.


@router.post("/{folder}/write")
async def write(folder: str, body: HandsWrite, request: Request, include_private: bool = PRIVATE):
    hands = get_engine(request).hands
    return await _safe(
        hands.write(
            folder,
            body.path,
            body.content,
            overwrite=body.overwrite,
            include_private=include_private,
        )
    )


@router.post("/{folder}/move")
async def move(folder: str, body: HandsMove, request: Request, include_private: bool = PRIVATE):
    hands = get_engine(request).hands
    return await _safe(hands.move(folder, body.src, body.dest, include_private=include_private))


@router.post("/{folder}/delete")
async def delete(folder: str, body: HandsPath, request: Request, include_private: bool = PRIVATE):
    """Borra un archivo (nunca carpetas enteras). Se puede deshacer."""
    hands = get_engine(request).hands
    return await _safe(hands.delete(folder, body.path, include_private=include_private))


@router.post("/{folder}/mkdir")
async def mkdir(folder: str, body: HandsPath, request: Request, include_private: bool = PRIVATE):
    hands = get_engine(request).hands
    return await _safe(hands.mkdir(folder, body.path, include_private=include_private))


@router.get("/{folder}/history")
def history(folder: str, request: Request, include_private: bool = PRIVATE):
    """Operaciones recientes de la carpeta (para saber qué se puede deshacer)."""
    try:
        return {
            "operations": get_engine(request).hands.history(folder, include_private=include_private)
        }
    except HandsError as e:
        raise HTTPException(e.status, str(e)) from e


@router.post("/{folder}/undo")
async def undo(folder: str, request: Request, include_private: bool = PRIVATE):
    """Deshace la última operación que siga en pie (también pide permiso)."""
    return await _safe(get_engine(request).hands.undo(folder, include_private=include_private))
