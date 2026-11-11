"""Registro de ejecución del cerebro: qué proveedor respondió, cuánto tardó y cuánto gastó.

Cumple la sección 8 de la filosofía híbrida: se guardan proveedor, modelo, hora, tarea y
resultado, pero **nunca el texto de la conversación**. Vive en la misma base que la
memoria (`data/meka.db`) y es la base del control de presupuesto (`budget.low`).
"""

import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY,
    created_at    REAL NOT NULL,
    task          TEXT NOT NULL,          -- chat | vision | document
    provider      TEXT NOT NULL,
    model         TEXT NOT NULL,
    ok            INTEGER NOT NULL,
    latency_ms    INTEGER NOT NULL,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    error         TEXT                    -- Solo el tipo de error, sin detalles del contenido
);
CREATE INDEX IF NOT EXISTS runs_created ON runs (created_at);
"""


@dataclass
class Run:
    task: str
    provider: str
    model: str
    ok: bool
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
    created_at: float = 0.0


class RunLog:
    def __init__(self, db_path: str | Path, *, keep: int = 5000):
        self.keep = keep
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(SCHEMA)

    def close(self):
        self._db.close()

    def record(self, run: Run):
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO runs (created_at, task, provider, model, ok, latency_ms,"
                " input_tokens, output_tokens, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run.created_at or time.time(), run.task, run.provider, run.model, int(run.ok),
                 run.latency_ms, run.input_tokens, run.output_tokens, run.error),
            )  # fmt: skip
            # Se conservan solo las últimas `keep` ejecuciones
            self._db.execute(
                "DELETE FROM runs WHERE id <= (SELECT MAX(id) FROM runs) - ?", (self.keep,)
            )

    def recent(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT task, provider, model, ok, latency_ms, input_tokens, output_tokens,"
                " error, created_at FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [asdict(Run(*row[:3], bool(row[3]), *row[4:])) for row in rows]

    def summary(self, since: float = 0.0) -> dict[str, dict]:
        """Por proveedor: llamadas, fallos, tokens y latencia media desde `since`."""
        with self._lock:
            rows = self._db.execute(
                "SELECT provider, COUNT(*), SUM(1 - ok), COALESCE(SUM(input_tokens), 0),"
                " COALESCE(SUM(output_tokens), 0), CAST(AVG(latency_ms) AS INTEGER)"
                " FROM runs WHERE created_at >= ? GROUP BY provider",
                (since,),
            ).fetchall()
        return {
            provider: {
                "calls": calls,
                "errors": errors,
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "avg_latency_ms": latency,
            }
            for provider, calls, errors, tokens_in, tokens_out, latency in rows
        }
