"""Memoria en la conversación: guardar "recuerda esto: ..." y traer al prompt los recuerdos
que vengan al caso (por significado y por palabras).

Privacidad: lo dicho en una conversación privada se guarda como privado y solo vuelve a un
prompt si quien lo va a leer es un proveedor local.
"""

import re

from ai.prompts import MEMORY_CONTEXT_TEMPLATE
from core.memory import MemoryStore, normalize_text
from core.semantic import SemanticMemory

# Valores por defecto de la sección `memory` de config.yml
DEFAULT_REMEMBER_PATTERN = r"recuerda\s+esto\s*:\s*(.+)"
DEFAULT_RECALL_TRIGGERS = ("recuerdas", "te acuerdas", "sabes algo de", "que me dijiste de")


class Recall:
    def __init__(self, memory: MemoryStore, semantic: SemanticMemory | None, memory_config: dict):
        self.memory = memory
        self.semantic = semantic
        self.remember_pattern = re.compile(
            memory_config.get("remember_pattern") or DEFAULT_REMEMBER_PATTERN,
            re.IGNORECASE | re.DOTALL,
        )
        self.triggers = tuple(
            normalize_text(t).strip()
            for t in memory_config.get("recall_triggers", DEFAULT_RECALL_TRIGGERS)
        )
        self.limit = memory_config.get("search_limit", 5)
        # Si el usuario pregunta por el pasado basta una similitud baja; sin pregunta
        # explícita, solo se añaden recuerdos muy relacionados (auto_recall)
        semantic_config = memory_config.get("semantic") or {}
        self.min_similarity = float(semantic_config.get("min_similarity", 0.35))
        self.auto_recall = float(semantic_config.get("auto_recall_similarity", 0.6))

    async def search(
        self, user_id, query: str, *, asked: bool = True, include_private: bool = True
    ) -> list[str]:
        """Recuerdos relevantes: primero por significado, después por palabras."""
        found: list[str] = []
        if self.semantic is not None:
            threshold = self.min_similarity if asked else self.auto_recall
            if threshold > 0:
                hits = await self.semantic.search(
                    user_id, query, self.limit, include_private=include_private
                )
                found = [fact for fact, similarity in hits if similarity >= threshold]
        if asked:
            for fact in self.memory.search(
                user_id, query, limit=self.limit, include_private=include_private
            ):
                if fact not in found:
                    found.append(fact)
        return found[: self.limit]

    async def context(self, user_id, user_text: str, *, private: bool, local: bool) -> str:
        """Texto para el prompt (o vacío). `private`: la conversación es privada; `local`:
        todos los proveedores que la atenderán son locales."""
        match = self.remember_pattern.search(user_text)
        if match:
            self.memory.add_fact(user_id, match.group(1).strip(), private=private)
            return ""  # Acaba de contarlo: no hace falta recordárselo

        normalized = normalize_text(user_text)
        asked = any(trigger in normalized for trigger in self.triggers)
        if not asked and self.semantic is None:
            return ""
        memories = await self.search(user_id, user_text, asked=asked, include_private=local)
        if not memories:
            return ""
        return MEMORY_CONTEXT_TEMPLATE.format(memories="\n".join(f"- {m}" for m in memories))
