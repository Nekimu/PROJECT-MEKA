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


class HandsWrite(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=1_000_000)
    overwrite: bool = Field(False, description="Reemplazar si ya existe")


class HandsMove(BaseModel):
    src: str = Field(min_length=1, max_length=500)
    dest: str = Field(min_length=1, max_length=500)


class HandsPath(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class ConfirmationRequest(BaseModel):
    action: str = Field(min_length=1, max_length=300, description="Qué se va a hacer")
    timeout: float | None = Field(None, ge=1, le=600, description="Segundos de espera")
    details: dict[str, Any] = Field(default_factory=dict, description="Contexto para mostrar")


class ConfirmationAnswer(BaseModel):
    approved: bool


class NotificationAction(BaseModel):
    action: str = Field(description="dismiss | open")


class FocusRequest(BaseModel):
    minutes: int | None = Field(None, ge=1, le=1440, description="Vacío = focus.default_minutes")


class MediaAction(BaseModel):
    action: str = Field(description="play_pause | next | previous")


class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    when: str | None = Field(
        None, max_length=200, description="En lenguaje natural: «mañana a las 5», «el viernes»"
    )
    due_at: float | None = Field(None, description="Cuándo vence (epoch); ignorado si hay `when`")
    remind_at: float | None = Field(None, description="Cuándo avisar (epoch)")
    private: bool = False
    source: str = Field("api", pattern="^(api|mcp|pet)$")


class TaskAction(BaseModel):
    action: str = Field(description="done | reopen | snooze | delete")
    minutes: int | None = Field(None, ge=1, le=10080, description="Para snooze (10 por defecto)")
