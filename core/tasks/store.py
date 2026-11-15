"""Tareas y recordatorios en SQLite, en la misma base que la memoria (`data/meka.db`).

Cada tarea tiene un título, cuándo vence (`due_at`) y cuándo avisar (`remind_at`), ambos
opcionales y en epoch. `reminded_at` evita avisar dos veces; posponer vuelve a ponerlo a NULL.
Lo dicho en una conversación privada se guarda como privado: no sale del equipo (MCP, nube).
"""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY,
    user_id     TEXT NOT NULL,
    title       TEXT NOT NULL,
    due_at      REAL,                  -- Cuándo vence (epoch); NULL: sin fecha
    remind_at   REAL,                  -- Cuándo avisar; NULL: sin aviso propio
    reminded_at REAL,                  -- Cuándo se avisó (NULL: pendiente de avisar)
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done')),
    private     INTEGER NOT NULL DEFAULT 0,
    source      TEXT NOT NULL DEFAULT 'chat',  -- chat | api | mcp
    created_at  REAL NOT NULL,
    done_at     REAL
);
CREATE INDEX IF NOT EXISTS tasks_user ON tasks (user_id, status, due_at);
CREATE INDEX IF NOT EXISTS tasks_remind ON tasks (status, remind_at);
"""

STATUSES = ("pending", "done")


@dataclass
class Task:
    id: int
    user_id: str
    title: str
    due_at: float | None
    remind_at: float | None
    reminded_at: float | None
    status: str
    private: bool
    source: str
    created_at: float
    done_at: float | None

    def public(self) -> dict:
        """Lo que ven los clientes (sin el usuario interno)."""
        data = asdict(self)
        data.pop("user_id")
        return data


class TaskStore:
    def __init__(self, db_path: str | Path):
        if str(db_path) != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(SCHEMA)

    def close(self):
        with self._lock:
            self._db.close()

    def _rows(self, sql: str, args=()) -> list[Task]:
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [_task(row) for row in rows]

    # ------------------------------------------------------------------ escribir

    def add(
        self,
        user_id,
        title: str,
        *,
        due_at: float | None = None,
        remind_at: float | None = None,
        private: bool = False,
        source: str = "chat",
    ) -> Task:
        title = " ".join(title.split())[:300]
        if not title:
            raise ValueError("La tarea necesita un título")
        with self._lock, self._db:
            cursor = self._db.execute(
                "INSERT INTO tasks (user_id, title, due_at, remind_at, private, source, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(user_id), title, due_at, remind_at, int(private), source, time.time()),
            )
        return self.get(cursor.lastrowid)

    def set_status(self, task_id: int, status: str) -> Task | None:
        if status not in STATUSES:
            raise ValueError(f"Estado no válido: {status!r}")
        done_at = time.time() if status == "done" else None
        with self._lock, self._db:
            self._db.execute(
                "UPDATE tasks SET status = ?, done_at = ? WHERE id = ?", (status, done_at, task_id)
            )
        return self.get(task_id)

    def snooze(self, task_id: int, until: float) -> Task | None:
        with self._lock, self._db:
            self._db.execute(
                "UPDATE tasks SET remind_at = ?, reminded_at = NULL WHERE id = ?", (until, task_id)
            )
        return self.get(task_id)

    def mark_reminded(self, task_id: int, when: float | None = None):
        with self._lock, self._db:
            self._db.execute(
                "UPDATE tasks SET reminded_at = ? WHERE id = ?", (when or time.time(), task_id)
            )

    def delete(self, task_id: int) -> bool:
        with self._lock, self._db:
            return self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount > 0

    # ------------------------------------------------------------------ leer

    def get(self, task_id: int) -> Task | None:
        found = self._rows("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return found[0] if found else None

    def list(
        self, user_id, *, status: str | None = "pending", include_private: bool = True
    ) -> list[Task]:
        """Las de fecha más cercana primero; las que no tienen fecha, al final."""
        sql = "SELECT * FROM tasks WHERE user_id = ?"
        args: list = [str(user_id)]
        if status:
            sql += " AND status = ?"
            args.append(status)
        if not include_private:
            sql += " AND private = 0"
        sql += " ORDER BY due_at IS NULL, due_at, id"
        return self._rows(sql, args)

    def due_reminders(self, now: float | None = None) -> list[Task]:
        """Pendientes cuyo aviso ya llegó y aún no se dio (todas las personas)."""
        return self._rows(
            "SELECT * FROM tasks WHERE status = 'pending' AND remind_at IS NOT NULL"
            " AND remind_at <= ? AND reminded_at IS NULL ORDER BY remind_at",
            (now or time.time(),),
        )

    def next_reminder(self) -> float | None:
        with self._lock:
            row = self._db.execute(
                "SELECT MIN(remind_at) FROM tasks WHERE status = 'pending'"
                " AND remind_at IS NOT NULL AND reminded_at IS NULL"
            ).fetchone()
        return row[0] if row else None


def _task(row: sqlite3.Row) -> Task:
    data = dict(row)
    data["private"] = bool(data["private"])
    return Task(**data)
