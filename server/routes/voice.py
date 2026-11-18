"""Síntesis de voz y descarga de los audios generados."""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from server.deps import AUTH, get_engine
from server.schemas import SpeechRequest

router = APIRouter(prefix="/v1", tags=["voz"], dependencies=AUTH)

MEDIA_TYPES = {".ogg": "audio/ogg", ".mp3": "audio/mpeg", ".wav": "audio/wav"}


@router.post("/speech")
async def speech(body: SpeechRequest, request: Request):
    """Sintetiza un texto con la voz del personaje. Devuelve el id para GET /v1/audio."""
    return {"audio": await get_engine(request).speak(body.text)}


@router.get("/audio/{audio_id}")
def audio(audio_id: str, request: Request):
    """Descarga un audio generado (una sola vez: después se borra)."""
    path = get_engine(request).take_audio(audio_id)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio no encontrado o caducado")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES.get(path.suffix, "application/octet-stream"),
        filename=path.name,
        background=BackgroundTask(path.unlink, missing_ok=True),
    )
