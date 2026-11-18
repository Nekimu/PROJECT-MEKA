"""Integración con git: estados a partir de los commits y control de áreas al commitear.

un commit que menciona `T-003`                 -> en_progreso
un commit con `cierra T-003` / `closes T-003`  -> hecha
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import datos

REF = re.compile(r"\bT-(\d{3,})\b")
CIERRE = re.compile(
    r"\b(?:cierra|cerrada|completa|resuelve|closes?|fix(?:es)?|done)\s*:?\s+T-(\d{3,})\b",
    re.IGNORECASE,
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=datos.RUTAS.root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    ).stdout


def sync(db: dict, limit: int = 200) -> list[str]:
    """Aplica a las tareas lo que dicen los mensajes de commit (idempotente)."""
    changes = []
    log = git("log", f"-{limit}", "--format=%H%x1f%an%x1f%B%x1e")
    by_id = {t["id"]: t for t in db["tareas"]}
    for record in reversed(log.split("\x1e")):  # Del más antiguo al más reciente
        if not record.strip():
            continue
        sha, author, message = [*record.strip().split("\x1f"), "", ""][:3]
        closed = {f"T-{n}" for n in CIERRE.findall(message)}
        for task_id in {f"T-{n}" for n in REF.findall(message)}:
            task = by_id.get(task_id)
            if not task or sha in task.setdefault("commits", []):
                continue
            task["commits"].append(sha)
            target = "hecha" if task_id in closed else None
            if target is None and task["estado"] in ("pendiente", "bloqueada"):
                target = "en_progreso"
            nota = f"commit {sha[:7]}: {message.strip().splitlines()[0][:80]}"
            if target and datos.set_state(task, target, f"git ({author})", nota):
                changes.append(f"{task_id} -> {target}")
            else:
                task["actualizada"] = datos.now()
    return changes


def staged_files() -> list[str]:
    return [f for f in git("diff", "--cached", "--name-only").splitlines() if f]


def check_commit(db: dict, msg_file: str) -> int:
    """Hook commit-msg: un commit no puede mezclar archivos de las dos áreas."""
    message = Path(msg_file).read_text(encoding="utf-8", errors="replace")
    ids = {f"T-{n}" for n in REF.findall(message)}
    by_id = {t["id"]: t for t in db["tareas"]}
    owners = {f: datos.owner(db, f) for f in staged_files()}
    agentes = {o for o in owners.values() if o != "compartido"}

    if not ids:
        print("ℹ️  [tareas] El commit no menciona ninguna tarea (T-XXX); el tablero no cambiará.")
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        print(f"⚠️  [tareas] Tareas inexistentes en el mensaje: {', '.join(sorted(unknown))}")

    responsables = {by_id[i]["responsable"] for i in ids if i in by_id}
    ajenos = [
        f for f, o in owners.items() if o in agentes and responsables and o not in responsables
    ]
    if len(agentes) > 1 or ajenos:
        print("❌ [tareas] Este commit toca archivos de las dos áreas:")
        for f, o in sorted(owners.items()):
            if o != "compartido":
                print(f"     {o:12} {f}")
        print("   Sepáralo en un commit por agente (o usa --no-verify si el usuario lo aprobó).")
        return 1
    return 0
