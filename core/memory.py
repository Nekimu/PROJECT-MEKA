"""Memoria persistente de MEKA en SQLite: recuerdos por usuario e historial por conversación.

Un solo archivo (`paths.memory_db`, por defecto `data/meka.db`), sin servidor y sin
dependencias: `sqlite3` viene con Python. La búsqueda usa FTS5 (índice de texto completo
que ignora tildes) y ordena por relevancia (BM25). La evaluación frente a JSON y
PostgreSQL está en docs/MEMORIA.md.
"""

import contextlib
import json
import re
import sqlite3
import threading
import time
import unicodedata
from pathlib import Path

from core.logger import setup_logger

logger = setup_logger("Memory")

SCHEMA_VERSION = 1

# Palabras a ignorar en la búsqueda (conectores y disparadores), ya normalizadas sin tildes.
STOPWORDS = {
    "recuerdas", "recuerda", "acuerdas", "sabes", "dijiste", "sobre", "esto", "esta", "este",
    "donde", "cual", "cuales", "como", "cuando", "porque", "para", "algo", "nada", "todo",
    "tengo", "tienes", "mucho", "cosas", "dime", "eres", "estas", "quien",
}  # fmt: skip

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id         INTEGER PRIMARY KEY,
    user_id    TEXT NOT NULL,
    fact       TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (user_id, fact)
);
CREATE INDEX IF NOT EXISTS facts_user ON facts (user_id, id);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY,
    session    TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_session ON messages (session, id);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    fact, content='facts', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts (rowid, fact) VALUES (new.id, new.fact);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts (facts_fts, rowid, fact) VALUES ('delete', old.id, old.fact);
END;
"""


def normalize_text(text: str) -> str:
    """Minúsculas, sin tildes y sin signos de puntuación (¿recuérdas? -> recuerdas)."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^\w\s]", " ", text)


def extract_keywords(text: str) -> list[str]:
    return [w for w in normalize_text(text).split() if len(w) > 3 and w not in STOPWORDS]


def stem(word: str) -> str:
    """Quita el plural para buscar por prefijo: juegos -> juego*, canciones -> cancion*."""
    if len(word) > 5 and word.endswith("es"):
        return word[:-2]
    if len(word) > 4 and word.endswith("s"):
        return word[:-1]
    return word


class MemoryStore:
    def __init__(self, db_path: str | Path, *, legacy_json: Path | None = None, legacy_owner=None):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Un hilo a la vez (el lock), pero desde cualquier hilo: el servidor usa asyncio.to_thread
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")  # Lecturas sin bloquear escrituras
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.fts = self._create_fts()
        self.db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self.db.commit()
        if legacy_json is not None:
            self.import_json(Path(legacy_json), legacy_owner)

    def _create_fts(self) -> bool:
        try:
            self.db.executescript(FTS_SCHEMA)
            return True
        except sqlite3.OperationalError as e:  # SQLite compilado sin FTS5 (muy raro)
            logger.warning(f"FTS5 no disponible ({e}); la búsqueda será más simple")
            return False

    def close(self):
        with self._lock:
            self.db.close()

    # ------------------------------------------------------------------ recuerdos

    def add_fact(self, user_id: int | str, fact: str) -> bool:
        """Añade un hecho a la memoria del usuario. False si estaba vacío o repetido."""
        fact = fact.strip()
        if not fact:
            return False
        with self._lock, self.db:
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO facts (user_id, fact, created_at) VALUES (?, ?, ?)",
                (str(user_id), fact, time.time()),
            )
        if cursor.rowcount:
            logger.info(f"Nuevo hecho recordado para el usuario {user_id}")
        return bool(cursor.rowcount)

    def get_facts(self, user_id: int | str) -> list[str]:
        with self._lock:
            rows = self.db.execute(
                "SELECT fact FROM facts WHERE user_id = ? ORDER BY id", (str(user_id),)
            ).fetchall()
        return [row[0] for row in rows]

    def clear(self, user_id: int | str) -> int:
        """Borra los recuerdos del usuario y devuelve cuántos había."""
        with self._lock, self.db:
            return self.db.execute("DELETE FROM facts WHERE user_id = ?", (str(user_id),)).rowcount

    def search(self, user_id: int | str, query: str, limit: int = 5) -> list[str]:
        """Recuerdos relevantes del usuario, del más al menos relevante."""
        keywords = extract_keywords(query)
        if not keywords:
            # Sin palabras clave claras, los últimos recuerdos
            return self.get_facts(user_id)[-limit:]
        found = self._search_fts(user_id, keywords, limit) if self.fts else None
        if found is None:
            found = self._search_simple(user_id, keywords, limit)
        return found or self.get_facts(user_id)[-3:]

    def _search_fts(self, user_id, keywords: list[str], limit: int) -> list[str] | None:
        # "color"* encuentra también "colores"; OR para que baste con una palabra
        match = " OR ".join(f'"{stem(word)}"*' for word in keywords)
        try:
            with self._lock:
                rows = self.db.execute(
                    "SELECT f.fact FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid "
                    "WHERE facts_fts MATCH ? AND f.user_id = ? "
                    "ORDER BY bm25(facts_fts), f.id DESC LIMIT ?",
                    (match, str(user_id), limit),
                ).fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"Búsqueda FTS fallida ({e}); se usa la simple")
            return None
        return [row[0] for row in rows]

    def _search_simple(self, user_id, keywords: list[str], limit: int) -> list[str]:
        scored = []
        for index, fact in enumerate(self.get_facts(user_id)):
            normalized = normalize_text(fact)
            score = sum(1 for kw in keywords if stem(kw) in normalized)
            if score:
                scored.append((score, index, fact))
        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [fact for _, _, fact in scored[:limit]]

    # ------------------------------------------------------------------ historial

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
        with self._lock, self.db:
            return self.db.execute(
                "DELETE FROM messages WHERE session = ?", (str(session),)
            ).rowcount

    def prune_messages(self, session: str, keep: int):
        """Conserva solo los `keep` mensajes más recientes de la conversación."""
        with self._lock, self.db:
            self.db.execute(
                "DELETE FROM messages WHERE session = ? AND id NOT IN "
                "(SELECT id FROM messages WHERE session = ? ORDER BY id DESC LIMIT ?)",
                (str(session), str(session), keep),
            )

    # ------------------------------------------------------------------ migración

    def import_json(self, path: Path, legacy_owner=None) -> int:
        """Importa el antiguo memory.json y lo renombra a .migrated. Devuelve cuántos importó."""
        if not path.is_file():
            return 0
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"No se pudo leer {path.name} para migrarlo ({e}); se deja como está")
            return 0

        facts = [(str(user), str(fact)) for user, items in (raw.get("users") or {}).items()
                 for fact in items]  # fmt: skip
        # Formato más antiguo: {"facts": [...]} compartido por todos los usuarios
        legacy = list(raw.get("facts") or []) + list(raw.get("legacy_facts") or [])
        if legacy and legacy_owner is None:
            logger.warning(
                f"{path.name} tiene {len(legacy)} recuerdos sin dueño. Define ALLOWED_USER_IDS "
                "en .env para asignarlos al primer usuario; hasta entonces no se migra."
            )
            return 0
        facts += [(str(legacy_owner), str(fact)) for fact in legacy]

        imported = sum(self.add_fact(user, fact) for user, fact in facts)
        with contextlib.suppress(OSError):
            path.replace(path.with_name(path.name + ".migrated"))
        logger.info(f"Migrados {imported} recuerdos de {path.name} a {self.db_path.name}")
        return imported
