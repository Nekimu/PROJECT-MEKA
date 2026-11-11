"""Memoria persistente de MEKA en SQLite: recuerdos por usuario e historial por conversación.

Un solo archivo (`paths.memory_db`, por defecto `data/meka.db`), sin servidor y sin
dependencias: `sqlite3` viene con Python. La búsqueda usa FTS5 (índice de texto completo
que ignora tildes) y ordena por relevancia (BM25). La evaluación frente a JSON y
PostgreSQL está en docs/MEMORIA.md.

La memoria semántica (recordar por significado) guarda un vector por recuerdo en
`fact_vectors`. Con la extensión `sqlite-vec` la similitud se calcula en C; sin ella,
en Python (de sobra para miles de recuerdos).
"""

import functools
import sqlite3
import threading
import time
from pathlib import Path

from core.legacy_import import import_legacy_json
from core.logger import setup_logger
from core.memory_sessions import SessionsMixin
from core.textsearch import (
    extract_keywords,
    normalize_text,
    pack,
    stem,
    unpack,
)

logger = setup_logger("Memory")

SCHEMA_VERSION = 3  # 3: facts.private

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id         INTEGER PRIMARY KEY,
    user_id    TEXT NOT NULL,
    fact       TEXT NOT NULL,
    created_at REAL NOT NULL,
    private    INTEGER NOT NULL DEFAULT 0,  -- Dicho en una conversación privada: solo local
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

CREATE TABLE IF NOT EXISTS private_sessions (
    session TEXT PRIMARY KEY,   -- Conversaciones en modo privado: solo proveedores locales
    since   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_vectors (
    fact_id INTEGER PRIMARY KEY REFERENCES facts (id) ON DELETE CASCADE,
    model   TEXT NOT NULL,
    vector  BLOB NOT NULL  -- float32, normalizado (longitud 1)
);
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


class MemoryStore(SessionsMixin):
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
        self._migrate()
        self.fts = self._create_fts()
        self.vec = self._load_sqlite_vec()
        self.db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self.db.commit()
        if legacy_json is not None:
            self.import_json(Path(legacy_json), legacy_owner)

    def _migrate(self):
        """Bases creadas por versiones anteriores: añade las columnas que falten."""
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(facts)")}
        if "private" not in columns:
            self.db.execute("ALTER TABLE facts ADD COLUMN private INTEGER NOT NULL DEFAULT 0")

    def _create_fts(self) -> bool:
        try:
            self.db.executescript(FTS_SCHEMA)
            return True
        except sqlite3.OperationalError as e:  # SQLite compilado sin FTS5 (muy raro)
            logger.warning(f"FTS5 no disponible ({e}); la búsqueda será más simple")
            return False

    def _load_sqlite_vec(self) -> bool:
        try:
            import sqlite_vec

            self.db.enable_load_extension(True)
            sqlite_vec.load(self.db)
            self.db.enable_load_extension(False)
            return True
        except Exception:  # No instalado, o Python sin soporte para extensiones
            return False

    def close(self):
        with self._lock:
            self.db.close()

    # ------------------------------------------------------------------ recuerdos

    def add_fact(self, user_id: int | str, fact: str, *, private: bool = False) -> bool:
        """Añade un hecho a la memoria del usuario. False si estaba vacío o repetido.

        Con `private`, solo podrá llegar a proveedores locales. Si ya existía, pasa a privado.
        """
        fact = fact.strip()
        if not fact:
            return False
        with self._lock, self.db:
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO facts (user_id, fact, created_at, private) VALUES (?, ?, ?, ?)",
                (str(user_id), fact, time.time(), int(private)),
            )
            if private and not cursor.rowcount:
                self.db.execute(
                    "UPDATE facts SET private = 1 WHERE user_id = ? AND fact = ?",
                    (str(user_id), fact),
                )
        if cursor.rowcount:
            logger.info(f"Nuevo hecho recordado para el usuario {user_id}")
        return bool(cursor.rowcount)

    def get_facts(self, user_id: int | str, *, include_private: bool = True) -> list[str]:
        with self._lock:
            rows = self.db.execute(
                "SELECT fact FROM facts WHERE user_id = ? AND (private = 0 OR ?) ORDER BY id",
                (str(user_id), int(include_private)),
            ).fetchall()
        return [row[0] for row in rows]

    def has_facts(self, user_id: int | str) -> bool:
        with self._lock:
            return (
                self.db.execute(
                    "SELECT 1 FROM facts WHERE user_id = ? LIMIT 1", (str(user_id),)
                ).fetchone()
                is not None
            )

    def clear(self, user_id: int | str) -> int:
        """Borra los recuerdos del usuario y devuelve cuántos había."""
        with self._lock, self.db:
            return self.db.execute("DELETE FROM facts WHERE user_id = ?", (str(user_id),)).rowcount

    def search(
        self, user_id: int | str, query: str, limit: int = 5, *, include_private: bool = True
    ) -> list[str]:
        """Recuerdos relevantes del usuario, del más al menos relevante."""
        keywords = extract_keywords(query)
        facts = functools.partial(self.get_facts, user_id, include_private=include_private)
        if not keywords:
            return facts()[-limit:]  # Sin palabras clave claras, los últimos recuerdos
        found = self._search_fts(user_id, keywords, limit, include_private) if self.fts else None
        if found is None:
            found = self._search_simple(facts(), keywords, limit)
        return found or facts()[-3:]

    def _search_fts(
        self, user_id, keywords: list[str], limit: int, include_private: bool
    ) -> list[str] | None:
        # "color"* encuentra también "colores"; OR para que baste con una palabra
        match = " OR ".join(f'"{stem(word)}"*' for word in keywords)
        try:
            with self._lock:
                rows = self.db.execute(
                    "SELECT f.fact FROM facts_fts JOIN facts f ON f.id = facts_fts.rowid "
                    "WHERE facts_fts MATCH ? AND f.user_id = ? AND (f.private = 0 OR ?) "
                    "ORDER BY bm25(facts_fts), f.id DESC LIMIT ?",
                    (match, str(user_id), int(include_private), limit),
                ).fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"Búsqueda FTS fallida ({e}); se usa la simple")
            return None
        return [row[0] for row in rows]

    @staticmethod
    def _search_simple(facts: list[str], keywords: list[str], limit: int) -> list[str]:
        scored = []
        for index, fact in enumerate(facts):
            normalized = normalize_text(fact)
            score = sum(1 for kw in keywords if stem(kw) in normalized)
            if score:
                scored.append((score, index, fact))
        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [fact for _, _, fact in scored[:limit]]

    # ------------------------------------------------------------------ vectores

    def facts_without_vectors(self, user_id, model: str, limit: int = 64) -> list[tuple[int, str]]:
        """Recuerdos sin vector de `model` (nuevos, migrados o de un modelo anterior)."""
        with self._lock:
            return self.db.execute(
                "SELECT f.id, f.fact FROM facts f LEFT JOIN fact_vectors v ON v.fact_id = f.id "
                "WHERE f.user_id = ? AND (v.fact_id IS NULL OR v.model != ?) ORDER BY f.id LIMIT ?",
                (str(user_id), model, limit),
            ).fetchall()

    def set_vectors(self, model: str, items: list[tuple[int, list[float]]]):
        with self._lock, self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO fact_vectors (fact_id, model, vector) VALUES (?, ?, ?)",
                [(fact_id, model, pack(vector)) for fact_id, vector in items],
            )

    def nearest(
        self, user_id, model: str, query: list[float], limit: int, include_private: bool = True
    ) -> list[tuple[str, float]]:
        """Los recuerdos más parecidos a `query`, con su similitud coseno (de -1 a 1)."""
        blob = pack(query)
        with self._lock:
            if self.vec:
                rows = self.db.execute(
                    "SELECT f.fact, 1 - vec_distance_cosine(v.vector, ?) AS similarity "
                    "FROM fact_vectors v JOIN facts f ON f.id = v.fact_id "
                    "WHERE f.user_id = ? AND v.model = ? AND (f.private = 0 OR ?) "
                    "ORDER BY similarity DESC LIMIT ?",
                    (blob, str(user_id), model, int(include_private), limit),
                ).fetchall()
                return [(fact, float(similarity)) for fact, similarity in rows]
            rows = self.db.execute(
                "SELECT f.fact, v.vector FROM fact_vectors v JOIN facts f ON f.id = v.fact_id "
                "WHERE f.user_id = ? AND v.model = ? AND (f.private = 0 OR ?)",
                (str(user_id), model, int(include_private)),
            ).fetchall()
        target = unpack(blob)
        scored = [
            (fact, sum(a * b for a, b in zip(unpack(v), target, strict=False))) for fact, v in rows
        ]
        scored.sort(key=lambda item: -item[1])
        return scored[:limit]

    # ------------------------------------------------------------------ migración

    def import_json(self, path: Path, legacy_owner=None) -> int:
        """Importa el antiguo memory.json (ver core/legacy_import.py)."""
        return import_legacy_json(self, path, legacy_owner)
