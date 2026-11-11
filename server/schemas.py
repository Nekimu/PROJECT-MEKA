"""Modelos de las peticiones de la API REST."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session: str = Field(
        min_length=1, max_length=200, description="Conversación (p. ej. telegram:123)"
    )
    user: str = Field(min_length=1, max_length=200, description="Dueño de la memoria")
    text: str = Field(min_length=1, max_length=20_000)
    audio: bool = Field(True, description="Sintetizar las frases marcadas con [AUDIO]")
    use_memory: bool = True
    private: bool = Field(False, description="Solo proveedores locales: nada sale del equipo")


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5_000)


class FactRequest(BaseModel):
    fact: str = Field(min_length=1, max_length=2_000)
    private: bool = Field(False, description="Solo podrá llegar a proveedores locales")


class EventRequest(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class ConfirmationRequest(BaseModel):
    action: str = Field(min_length=1, max_length=300, description="Qué se va a hacer")
    timeout: float | None = Field(None, ge=1, le=600, description="Segundos de espera")
    details: dict[str, Any] = Field(default_factory=dict, description="Contexto para mostrar")


class ConfirmationAnswer(BaseModel):
    approved: bool
