"""Memoria semántica: recordar por significado, no solo por palabras.

"¿Qué te conté de mi mascota?" encuentra "mi perro se llama Toby" aunque no
compartan ninguna palabra. Cada recuerdo se convierte en un vector (embedding) con
un modelo local de Ollama y se guarda en la misma base SQLite. Nada sale del equipo.

Los vectores se calculan sin prisa: al buscar se indexan los recuerdos que aún no
tienen (nuevos, migrados del JSON o de un modelo de embeddings anterior).
"""

import asyncio
from typing import Protocol

from core.logger import setup_logger
from core.memory import MemoryStore

logger = setup_logger("Semantic")


class Embedder(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def check_health(self) -> bool: ...


class OllamaEmbedder:
    """Embeddings con Ollama. `embeddinggemma` es multilingüe, ligero (~600 MB) y local."""

    def __init__(self, settings: dict, client=None):
        self.model = settings.get("model", "embeddinggemma")
        self.host = settings.get("base_url", "http://localhost:11434")
        self.keep_alive = settings.get("keep_alive", 0)
        if client is None:
            from ollama import Client

            client = Client(host=self.host)
        self.client = client

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embed(model=self.model, input=texts, keep_alive=self.keep_alive)
        return [list(vector) for vector in response.embeddings]

    def check_health(self) -> bool:
        try:
            self.client.show(self.model)
            return True
        except Exception as e:
            logger.warning(
                f"Memoria semántica sin modelo '{self.model}' ({e}). "
                f"Descárgalo con: ollama pull {self.model}. Mientras tanto se busca por palabras."
            )
            return False


class SemanticMemory:
    def __init__(
        self,
        store: MemoryStore,
        embedder: Embedder,
        *,
        query_prefix: str = "",
        document_prefix: str = "",
        batch_size: int = 32,
    ):
        self.store = store
        self.embedder = embedder
        # Algunos modelos rinden mejor si se marca qué es pregunta y qué es documento
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self.batch_size = batch_size
        self._warned = False

    @classmethod
    def from_config(cls, store: MemoryStore, config: dict) -> "SemanticMemory | None":
        semantic = config.get("memory", {}).get("semantic") or {}
        if not semantic.get("enabled", False):
            return None
        ollama = (config.get("ai", {}).get("providers") or {}).get("ollama") or {}
        settings = {"base_url": ollama.get("base_url", "http://localhost:11434"), **semantic}
        return cls(
            store,
            OllamaEmbedder(settings),
            query_prefix=semantic.get("query_prefix", ""),
            document_prefix=semantic.get("document_prefix", ""),
        )

    @property
    def model(self) -> str:
        return self.embedder.model

    def check_health(self) -> bool:
        return self.embedder.check_health()

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        # La llamada a Ollama es bloqueante: en un hilo aparte
        return await asyncio.to_thread(self.embedder.embed, texts)

    async def index(self, user_id) -> int:
        """Calcula los vectores que falten para los recuerdos del usuario."""
        done = 0
        while pending := self.store.facts_without_vectors(user_id, self.model, self.batch_size):
            vectors = await self._embed([self.document_prefix + fact for _, fact in pending])
            self.store.set_vectors(
                self.model,
                [(fact_id, vec) for (fact_id, _), vec in zip(pending, vectors, strict=True)],
            )
            done += len(pending)
        if done:
            logger.info(f"Indexados {done} recuerdo(s) del usuario {user_id} con {self.model}")
        return done

    async def search(self, user_id, query: str, limit: int = 5) -> list[tuple[str, float]]:
        """Recuerdos por significado con su similitud (0 a 1). Vacío si Ollama no responde."""
        if not self.store.has_facts(user_id):
            return []  # Sin recuerdos no hace falta llamar al modelo
        try:
            await self.index(user_id)
            [vector] = await self._embed([self.query_prefix + query])
        except Exception as e:
            if not self._warned:  # Avisar una vez, no en cada mensaje
                logger.warning(f"Memoria semántica no disponible ({e}); se busca por palabras")
                self._warned = True
            return []
        self._warned = False
        return self.store.nearest(user_id, self.model, vector, limit)
