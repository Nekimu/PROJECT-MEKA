"""Memoria persistente de hechos ("recuerda esto: ..."), aislada por usuario."""

import contextlib
import json
import os
import re
import tempfile
import threading
import time
import unicodedata
from pathlib import Path

from core.config import resolve_path
from core.logger import setup_logger

logger = setup_logger("Memory_System")

# Palabras a ignorar en la búsqueda (conectores y disparadores), ya normalizadas sin tildes.
STOPWORDS = {
    "recuerdas", "recuerda", "acuerdas", "sabes", "dijiste", "sobre", "esto", "esta", "este",
    "donde", "cual", "cuales", "como", "cuando", "porque", "para", "algo", "nada", "todo",
    "tengo", "tienes", "mucho", "cosas", "dime", "eres", "estas", "quien",
}  # fmt: skip


def normalize_text(text: str) -> str:
    """Minúsculas, sin tildes y sin signos de puntuación (¿recuérdas? -> recuerdas)."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^\w\s]", " ", text)


def extract_keywords(text: str) -> list[str]:
    return [w for w in normalize_text(text).split() if len(w) > 3 and w not in STOPWORDS]


class MemorySystem:
    def __init__(self, file_path=None, legacy_owner_id: int | str | None = None):
        self.file_path = Path(file_path) if file_path else resolve_path("memory.json")
        self._lock = threading.Lock()
        self.data = self._load(legacy_owner_id)

    def _load(self, legacy_owner_id):
        """Carga la memoria desde el archivo JSON (y migra el formato antiguo global)."""
        data = {"users": {}}
        if not self.file_path.exists():
            return data
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            backup = self.file_path.with_name(f"{self.file_path.name}.corrupt-{int(time.time())}")
            logger.error(f"Error cargando memoria ({e}). Se conserva una copia en {backup.name}")
            with contextlib.suppress(OSError):
                self.file_path.replace(backup)
            return data

        for user_id, facts in (raw.get("users") or {}).items():
            data["users"][str(user_id)] = [str(f) for f in facts]

        # Formato antiguo: {"facts": [...]} compartido por TODOS los usuarios.
        legacy = list(raw.get("facts") or []) + list(raw.get("legacy_facts") or [])
        if legacy:
            if legacy_owner_id is not None:
                owner = data["users"].setdefault(str(legacy_owner_id), [])
                owner.extend(f for f in legacy if f not in owner)
                logger.info(
                    f"Migrados {len(legacy)} recuerdos antiguos al usuario {legacy_owner_id}"
                )
                self.data = data
                self._save()
            else:
                data["legacy_facts"] = legacy
                logger.warning(
                    f"Hay {len(legacy)} recuerdos en formato antiguo sin dueño. Define "
                    "ALLOWED_USER_IDS en .env para asignarlos al primer usuario de la lista."
                )
        return data

    def _save(self):
        """Guarda la memoria de forma atómica (archivo temporal + reemplazo)."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=self.file_path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.file_path)
        except Exception as e:
            logger.error(f"Error guardando memoria: {e}")

    def add_fact(self, user_id: int | str, fact: str) -> bool:
        """Añade un hecho a la memoria del usuario."""
        fact = fact.strip()
        if not fact:
            return False
        with self._lock:
            facts = self.data["users"].setdefault(str(user_id), [])
            if fact in facts:
                return False
            facts.append(fact)
            self._save()
        logger.info(f"Nuevo hecho recordado para el usuario {user_id}")
        return True

    def get_facts(self, user_id: int | str) -> list[str]:
        """Devuelve todos los hechos recordados del usuario."""
        return list(self.data["users"].get(str(user_id), []))

    def clear(self, user_id: int | str) -> int:
        """Borra los recuerdos del usuario y devuelve cuántos había."""
        with self._lock:
            removed = self.data["users"].pop(str(user_id), [])
            if removed:
                self._save()
        return len(removed)

    def search(self, user_id: int | str, query: str, limit: int = 5) -> list[str]:
        """Busca hechos relevantes del usuario, ordenados por número de palabras clave."""
        facts = self.get_facts(user_id)
        keywords = extract_keywords(query)
        if not keywords:
            # Si no hay palabras clave claras, devolver los últimos recuerdos
            return facts[-limit:]

        scored = []
        for index, fact in enumerate(facts):
            normalized = normalize_text(fact)
            score = sum(1 for kw in keywords if kw in normalized)
            if score:
                scored.append((score, index, fact))
        if not scored:
            return facts[-3:]
        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [fact for _, _, fact in scored[:limit]]
