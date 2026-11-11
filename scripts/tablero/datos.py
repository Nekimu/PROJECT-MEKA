"""Datos del tablero: lectura/escritura segura de tareas.json, estados y áreas."""

from __future__ import annotations

import contextlib
import fnmatch
import json
import os
import time
from datetime import datetime
from pathlib import Path

ESTADOS = ("pendiente", "en_progreso", "bloqueada", "en_revision", "hecha", "descartada")
CERRADOS = ("hecha", "descartada")  # No cuentan como abiertas
PRIORIDADES = ("alta", "media", "baja")
ICONOS = {
    "pendiente": "⬜",
    "en_progreso": "🔄",
    "bloqueada": "⛔",
    "en_revision": "👀",
    "hecha": "✅",
    "descartada": "🚫",
}


class Rutas:
    def __init__(self, root: Path):
        self.root = root
        self.dir = root / "coordinacion"
        self.data = self.dir / "tareas.json"
        self.board = self.dir / "TABLERO.md"
        self.lock = self.dir / ".tareas.lock"


# Se sustituye en los tests por un repositorio temporal
RUTAS = Rutas(Path(__file__).resolve().parents[2])


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@contextlib.contextmanager
def locked(timeout: float = 10.0):
    """Bloqueo entre procesos: los dos agentes pueden escribir a la vez sin pisarse."""
    lock = RUTAS.lock
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            with contextlib.suppress(OSError):
                if time.time() - lock.stat().st_mtime > 30:  # Bloqueo huérfano
                    lock.unlink()
                    continue
            if time.monotonic() > deadline:
                raise SystemExit(
                    "El tablero está bloqueado por otro proceso; reinténtalo."
                ) from None
            time.sleep(0.1)
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        with contextlib.suppress(OSError):
            lock.unlink()


def load() -> dict:
    return json.loads(RUTAS.data.read_text(encoding="utf-8"))


def save(db: dict):
    """Escritura atómica de tareas.json (TABLERO.md lo regenera vista.render)."""
    tmp = RUTAS.data.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(RUTAS.data)


def find(db: dict, task_id: str) -> dict:
    task_id = task_id.upper()
    for task in db["tareas"]:
        if task["id"] == task_id:
            return task
    raise SystemExit(f"No existe la tarea {task_id}")


def set_state(task: dict, estado: str, por: str, nota: str = "") -> bool:
    if estado not in ESTADOS:
        raise SystemExit(f"Estado no válido: {estado}. Usa uno de {', '.join(ESTADOS)}")
    if task["estado"] == estado and not nota:
        return False
    task["estado"] = estado
    task["actualizada"] = now()
    entry = {"fecha": task["actualizada"], "estado": estado, "por": por}
    if nota:
        entry["nota"] = nota
    task.setdefault("historial", []).append(entry)
    return True


def owner(db: dict, path: str) -> str:
    """Agente dueño de una ruta, o "compartido" si no es exclusiva de nadie."""
    rel = Path(path)
    with contextlib.suppress(ValueError):
        rel = rel.resolve().relative_to(RUTAS.root)
    posix = rel.as_posix()
    # El orden importa: las excepciones (p. ej. tests/test_pet_skins.py) van primero
    for agente in db["prioridad_areas"]:
        for pattern in db["areas"][agente]["rutas"]:
            if fnmatch.fnmatch(posix, pattern) or (
                pattern.endswith("/**") and posix.startswith(pattern[:-2])
            ):
                return agente
    return "compartido"


def new_task(db: dict, agente: str, titulo: str, **campos) -> dict:
    """Crea una tarea pendiente con el siguiente id libre (no guarda)."""
    if agente not in db["agentes"]:
        raise SystemExit(f"Agente desconocido. Usa: {', '.join(db['agentes'])}")
    numero = max((int(t["id"][2:]) for t in db["tareas"]), default=0) + 1
    task = {
        "id": f"T-{numero:03d}",
        "titulo": titulo,
        "responsable": agente,
        "estado": "pendiente",
        "prioridad": campos.get("prioridad", "media"),
        "descripcion": campos.get("descripcion", ""),
        "archivos": campos.get("archivos", []),
        "depende_de": campos.get("depende_de", []),
        "commits": [],
        "historial": [],
    }
    ajenos = [a for a in task["archivos"] if owner(db, a) not in (agente, "compartido")]
    if ajenos:
        raise SystemExit(f"Estos archivos son de otra área: {', '.join(ajenos)}")
    set_state(task, "pendiente", campos.get("por") or agente, "creada")
    db["tareas"].append(task)
    return task
