"""Historial por conversación y su marca de privacidad, guardados en la base de MemoryStore.

`SessionsMixin` es parte de `MemoryStore` (core/memory.py); usa su `db` y su `_lock`.
"""

import time


class SessionsMixin:
    def add_messages(self, session: str, messages: list[tuple[str, str]]):
        now = time.time()
        with self._lock, self.db:
            self.db.executemany(
                "INSERT INTO messages (session, role, content, created_at) VALUES (?, ?, ?, ?)",
                [(str(session), role, content, now) for role, content in messages],
            )

    def recent_messages(self, session: str, limit: int) -> list[dict]:
        with self._lock:
            rows = self.db.execute(
                "SELECT role, content FROM messages WHERE session = ? ORDER BY id DESC LIMIT ?",
                (str(session), limit),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def clear_messages(self, session: str) -> int:
        """Borra el historial (y con él la marca de privacidad: ya no hay nada que proteger)."""
        with self._lock, self.db:
            self.db.execute("DELETE FROM private_sessions WHERE session = ?", (str(session),))
            return self.db.execute(
                "DELETE FROM messages WHERE session = ?", (str(session),)
            ).rowcount

    def mark_private(self, session: str):
        with self._lock, self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO private_sessions (session, since) VALUES (?, ?)",
                (str(session), time.time()),
            )

    def is_private(self, session: str) -> bool:
        with self._lock:
            row = self.db.execute(
                "SELECT 1 FROM private_sessions WHERE session = ?", (str(session),)
            ).fetchone()
        return row is not None

    def prune_messages(self, session: str, keep: int):
        """Conserva solo los `keep` mensajes más recientes de la conversación."""
        with self._lock, self.db:
            self.db.execute(
                "DELETE FROM messages WHERE session = ? AND id NOT IN "
                "(SELECT id FROM messages WHERE session = ? ORDER BY id DESC LIMIT ?)",
                (str(session), str(session), keep),
            )
