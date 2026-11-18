"""Tareas y recordatorios (core/tasks/), y la vigilancia proactiva de Hanna."""

from fastapi import APIRouter, HTTPException, Query, Request

from server.deps import AUTH, get_engine, resolve_user
from server.schemas import TaskAction, TaskRequest

# `user` = un ID, o `me` para el dueño (lo que usa la mascota)
router = APIRouter(prefix="/v1/users/{user}/tasks", tags=["tareas"], dependencies=AUTH)
proactive_router = APIRouter(prefix="/v1/proactive", tags=["tareas"], dependencies=AUTH)


@router.get("")
def list_tasks(
    user: str,
    request: Request,
    status: str = Query("pending", description="pending | done | all"),
    include_private: bool = Query(
        True, description="false para clientes que sacan los datos del equipo (MCP, Telegram)"
    ),
):
    """Las de fecha más cercana primero; las que no tienen fecha, al final."""
    user = resolve_user(user, request)
    if status not in ("pending", "done", "all"):
        raise HTTPException(422, "status debe ser pending, done o all")
    tasks = get_engine(request).tasks.store.list(
        user, status=None if status == "all" else status, include_private=include_private
    )
    return {"tasks": [task.public() for task in tasks]}


@router.post("")
def add_task(user: str, body: TaskRequest, request: Request):
    """Con `when` en lenguaje natural («mañana a las 5») o con `due_at`/`remind_at` en epoch."""
    user = resolve_user(user, request)
    try:
        task = get_engine(request).tasks.add(
            user,
            body.title,
            text_when=body.when,
            due_at=body.due_at,
            remind_at=body.remind_at,
            private=body.private,
            source=body.source,
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return task.public()


@router.post("/{task_id}")
def task_action(user: str, task_id: int, body: TaskAction, request: Request):
    """done | reopen | snooze (con `minutes`) | delete. Publica task.changed."""
    user = resolve_user(user, request)
    engine = get_engine(request)
    current = engine.tasks.store.get(task_id)
    if current is None or current.user_id != user:
        raise HTTPException(404, "No existe esa tarea")
    try:
        task = engine.tasks.act(task_id, body.action, minutes=body.minutes)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"done": True, "task": task.public() if body.action != "delete" else None}


@proactive_router.get("")
def proactive_status(request: Request):
    """Si está activa, cuándo será el próximo resumen y por qué está esperando."""
    return get_engine(request).proactive.status()


@proactive_router.post("/check")
def check_now(request: Request):
    """«¿Qué tengo pendiente?» desde la isla: el resumen ahora, sin esperar a su turno."""
    nudge = get_engine(request).proactive.nudge(force=True)
    return {"nudge": nudge}
