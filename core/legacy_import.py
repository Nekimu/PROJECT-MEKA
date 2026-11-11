"""Migración única del antiguo `memory.json` a SQLite (versiones anteriores a la 1.2)."""

import contextlib
import json
from pathlib import Path

from core.logger import setup_logger

logger = setup_logger("Memory")


def import_legacy_json(store, path: Path, legacy_owner=None) -> int:
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

    imported = sum(store.add_fact(user, fact) for user, fact in facts)
    with contextlib.suppress(OSError):
        path.replace(path.with_name(path.name + ".migrated"))
    logger.info(f"Migrados {imported} recuerdos de {path.name} a {store.db_path.name}")
    return imported
