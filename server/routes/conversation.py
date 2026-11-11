"""Conversación: texto, notas de voz, archivos y reinicio de la sesión."""

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from core.engine import UnsupportedFileError
from server.deps import AUTH, get_engine, save_upload
from server.schemas import ChatRequest

router = APIRouter(prefix="/v1", tags=["conversación"], dependencies=AUTH)


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    replies = await get_engine(request).chat(
        body.session,
        body.user,
        body.text,
        audio=body.audio,
        use_memory=body.use_memory,
        private=body.private,
    )
    return {"replies": [r.to_dict() for r in replies]}


@router.post("/voice")
async def voice(
    request: Request,
    file: UploadFile = File(...),
    session: str = Form(...),
    user: str = Form(...),
    audio: bool = Form(True),
    private: bool = Form(False),
):
    """Nota de voz → transcripción (Whisper) → respuesta."""
    path = await save_upload(file, request)
    try:
        transcription, replies = await get_engine(request).voice(
            session, user, path, audio=audio, private=private
        )
    finally:
        path.unlink(missing_ok=True)
    return {"transcription": transcription, "replies": [r.to_dict() for r in replies]}


@router.post("/files")
async def analyze_file(
    request: Request,
    file: UploadFile = File(...),
    session: str = Form(...),
    user: str = Form(...),
    caption: str | None = Form(None),
    private: bool = Form(False),
):
    """Imagen (visión) o documento (PDF, DOCX, XLSX, TXT, MD, CSV)."""
    file_name = Path(file.filename or "archivo").name
    path = await save_upload(file, request)
    try:
        replies = await get_engine(request).analyze_file(
            session, user, path, file_name, caption, private=private
        )
    except UnsupportedFileError as e:
        raise HTTPException(415, f"Tipo de archivo no soportado: {e}") from e
    finally:
        path.unlink(missing_ok=True)
    return {"replies": [r.to_dict() for r in replies]}


@router.post("/sessions/{session}/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset(session: str, request: Request):
    get_engine(request).reset(session)
