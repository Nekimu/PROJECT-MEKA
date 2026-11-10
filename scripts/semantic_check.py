"""Calibra la memoria semántica: muestra la similitud entre una pregunta y tus recuerdos.

Uso (desde la raíz del proyecto, con Ollama en marcha):
    python -m scripts.semantic_check "¿qué te conté de mi mascota?"
    python -m scripts.semantic_check "¿qué te conté de mi mascota?" --user 123456789

Sin --user usa unas frases de ejemplo. Con los números que salgan, ajusta
`memory.semantic.min_similarity` y `auto_recall_similarity` en config.yml.
"""

import argparse
import asyncio
import tempfile
from pathlib import Path

from core.config import default_user, resolve_path, settings
from core.memory import MemoryStore
from core.semantic import SemanticMemory

EXAMPLES = [
    "mi perro se llama Toby",
    "mi color favorito es el azul",
    "me encanta el ramen picante",
    "juego Overwatch con D.Va los viernes",
    "trabajo como desarrollador de software",
]


async def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query")
    parser.add_argument("--user", help="Usa los recuerdos reales de este usuario")
    args = parser.parse_args()

    config = {**settings, "memory": {**settings.get("memory", {})}}
    config["memory"]["semantic"] = {**(config["memory"].get("semantic") or {}), "enabled": True}

    if args.user:
        db = resolve_path(settings.get("paths", {}).get("memory_db", "data/meka.db"))
        store, user = MemoryStore(db), args.user
    else:
        store, user = MemoryStore(Path(tempfile.mkdtemp()) / "ejemplo.db"), default_user(settings)
        for fact in EXAMPLES:
            store.add_fact(user, fact)

    memory = SemanticMemory.from_config(store, config)
    print(f"Modelo: {memory.model}\nPregunta: {args.query}\n")
    for fact, similarity in await memory.search(user, args.query, limit=20):
        print(f"  {similarity:5.2f}  {fact}")

    semantic = config["memory"]["semantic"]
    print(
        f"\nUmbrales actuales: min_similarity={semantic.get('min_similarity', 0.35)} · "
        f"auto_recall_similarity={semantic.get('auto_recall_similarity', 0.6)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
