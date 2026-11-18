"""Hooks de Claude Code (ver .claude/settings.json)."""

from __future__ import annotations

import json
import sys

from . import datos, vista


def _emit(event: str, **fields):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, **fields}}))


def pretooluse(db: dict, agente: str):
    """PreToolUse: impide que un agente edite archivos del área del otro."""
    payload = json.loads(sys.stdin.read() or "{}")
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return
    dueño = datos.owner(db, path)
    if dueño in (agente, "compartido"):
        return
    nombre = db["agentes"][dueño]["nombre"]
    _emit(
        "PreToolUse",
        permissionDecision="deny",
        permissionDecisionReason=(
            f"{path} pertenece al área de {nombre} (coordinacion/README.md). "
            f"No lo edites: crea una tarea para {nombre} con "
            f"`python scripts/tareas.py nueva --agente {dueño} --titulo ...`."
        ),
    )


def session(db: dict):
    """SessionStart: el agente empieza cada sesión viendo el tablero actualizado."""
    _emit(
        "SessionStart",
        additionalContext=(
            "Tablero compartido con Antigravity (coordinacion/TABLERO.md). Actualiza estados con "
            "`python scripts/tareas.py estado T-XXX <estado> --agente claude` y menciona T-XXX "
            "en los commits.\n" + vista.summary(db)
        ),
    )
