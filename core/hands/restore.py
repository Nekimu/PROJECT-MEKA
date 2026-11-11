"""Puntos de restauración de las manos: un repositorio git "sombra" por carpeta autorizada.

El repositorio vive en `data/hands/<carpeta>.git`, **no** dentro de la carpeta del usuario,
y solo guarda los archivos que una operación va a tocar. El diario (SQLite) recuerda qué
hizo cada operación para poder deshacerla.
"""

import json
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from core.hands.policy import Folder, HandsError

SCHEMA = """
CREATE TABLE IF NOT EXISTS hands_ops (
    id         TEXT PRIMARY KEY,
    folder     TEXT NOT NULL,
    op         TEXT NOT NULL,      -- write | move | delete | mkdir
    paths      TEXT NOT NULL,      -- JSON: rutas relativas afectadas
    existed    TEXT NOT NULL,      -- JSON: qué rutas existían antes
    snapshot   TEXT,               -- Commit del punto de restauración
    created_at REAL NOT NULL,
    undone_at  REAL
);
"""


@dataclass
class Operation:
    id: str
    folder: str
    op: str
    paths: list[str]
    existed: dict[str, bool] = field(default_factory=dict)
    snapshot: str | None = None
    created_at: float = 0.0
    undone_at: float | None = None

    def public(self) -> dict:
        return {
            "id": self.id,
            "op": self.op,
            "paths": self.paths,
            "created_at": self.created_at,
            "undone": self.undone_at is not None,
        }


class RestorePoints:
    def __init__(self, data_dir: Path, db_path: Path):
        self.data_dir = Path(data_dir)
        self.git = shutil.which("git")
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(SCHEMA)

    def close(self):
        self._db.close()

    # ------------------------------------------------------------------ git

    def _run(self, folder: Folder, *args: str) -> str:
        if self.git is None:
            raise HandsError(
                "Hace falta git para los puntos de restauración y no está instalado", 503
            )
        gitdir = self.data_dir / f"{folder.name}.git"
        base = [self.git, "-c", "core.autocrlf=false", "-c", "core.quotepath=off",
                "-c", "user.name=MEKA", "-c", "user.email=meka@localhost"]  # fmt: skip
        location = [f"--git-dir={gitdir}", f"--work-tree={folder.root}"]
        if not gitdir.exists():
            # El repositorio vive en gitdir y trabaja sobre la carpeta (nada de .git dentro)
            gitdir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([*base, *location, "init", "-q"], check=True, capture_output=True)
        result = subprocess.run(
            [*base, *location, *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )  # fmt: skip
        if result.returncode != 0:
            raise HandsError(f"git falló: {result.stderr.strip()[:200]}", 500)
        return result.stdout.strip()

    def snapshot(self, folder: Folder, op: str, paths: list[str]) -> Operation:
        """Guarda el estado actual de `paths` antes de cambiarlos."""
        existed = {p: (folder.root / p).exists() for p in paths}
        files = [p for p in paths if (folder.root / p).is_file()]
        if files:
            self._run(folder, "add", "--force", "--", *files)  # --force: ignora .gitignore ajenos
        operation = Operation(uuid.uuid4().hex[:12], folder.name, op, paths, existed)
        self._run(folder, "commit", "-q", "--allow-empty", "-m", f"antes de {op} ({operation.id})")
        operation.snapshot = self._run(folder, "rev-parse", "HEAD")
        operation.created_at = time.time()
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO hands_ops VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                (operation.id, folder.name, op, json.dumps(paths), json.dumps(existed),
                 operation.snapshot, operation.created_at),
            )  # fmt: skip
        return operation

    def restore(self, folder: Folder, operation: Operation):
        """Deja las rutas como estaban antes de la operación."""
        for path in operation.paths:
            target = folder.root / path
            if operation.existed.get(path):
                if target.is_dir() or not self._in_snapshot(folder, operation, path):
                    continue  # Carpetas: existían y siguen ahí
                self._run(folder, "checkout", operation.snapshot, "--", path)
            elif target.is_file():
                target.unlink()  # La creó la operación
            elif target.is_dir() and not any(target.iterdir()):
                target.rmdir()
        with self._lock, self._db:
            self._db.execute(
                "UPDATE hands_ops SET undone_at = ? WHERE id = ?", (time.time(), operation.id)
            )

    def _in_snapshot(self, folder: Folder, operation: Operation, path: str) -> bool:
        listed = self._run(folder, "ls-tree", "--name-only", operation.snapshot, "--", path)
        return bool(listed)

    # ------------------------------------------------------------------ diario

    def history(self, folder: str, limit: int = 20) -> list[Operation]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM hands_ops WHERE folder = ? ORDER BY created_at DESC LIMIT ?",
                (folder, limit),
            ).fetchall()
        return [
            Operation(r[0], r[1], r[2], json.loads(r[3]), json.loads(r[4]), r[5], r[6], r[7])
            for r in rows
        ]

    def last_undoable(self, folder: str) -> Operation | None:
        """Se deshace como una pila: la operación más reciente que siga en pie."""
        for operation in self.history(folder, 100):
            if operation.undone_at is None:
                return operation
        return None
