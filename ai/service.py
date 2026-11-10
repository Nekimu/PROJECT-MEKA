"""Servicio de IA: personaje + memoria + el proveedor elegido (Ollama, Claude o Gemini)."""

import re
import time
from collections import deque

from ai.prompts import MEMORY_CONTEXT_TEMPLATE, build_system_prompt, build_vision_prompt
from ai.providers import Provider, ProviderError, build_provider
from ai.text_utils import split_into_messages, split_paragraphs
from core.config import resolve_path, settings
from core.logger import log_conversation, setup_logger
from core.memory import MemoryStore, normalize_text
from core.persona import Persona, load_active_persona
from core.semantic import SemanticMemory

logger = setup_logger("AI_Service")

# Valores por defecto de la sección `memory` de config.yml
DEFAULT_REMEMBER_PATTERN = r"recuerda\s+esto\s*:\s*(.+)"
DEFAULT_RECALL_TRIGGERS = ("recuerdas", "te acuerdas", "sabes algo de", "que me dijiste de")


class ConversationStore:
    """Historial reciente de mensajes, separado por chat.

    Con `store` (la base de datos) sobrevive a los reinicios; sin él, vive en la RAM.
    """

    def __init__(self, max_messages: int = 20, store: MemoryStore | None = None):
        self.max_messages = max_messages
        self.store = store
        self._chats: dict[str, deque] = {}

    def get(self, chat_id: int | str) -> list[dict]:
        if self.store is not None:
            return self.store.recent_messages(str(chat_id), self.max_messages)
        return list(self._chats.get(str(chat_id), ()))

    def add_exchange(self, chat_id: int | str, user_text: str, assistant_text: str):
        if self.store is not None:
            self.store.add_messages(
                str(chat_id), [("user", user_text), ("assistant", assistant_text)]
            )
            self.store.prune_messages(str(chat_id), self.max_messages)
            return
        history = self._chats.setdefault(str(chat_id), deque(maxlen=self.max_messages))
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})

    def clear(self, chat_id: int | str):
        if self.store is not None:
            self.store.clear_messages(str(chat_id))
        self._chats.pop(str(chat_id), None)


class AIService:
    def __init__(
        self,
        config: dict | None = None,
        *,
        memory=None,
        persona: Persona | None = None,
        providers: dict[str, Provider] | None = None,
        semantic: SemanticMemory | None = None,
    ):
        config = settings if config is None else config
        ai_config = config.get("ai", {})

        # Enrutamiento: qué cerebro usa cada tarea y cuál entra si el principal falla
        self.primary = ai_config.get("provider", "ollama")
        self.vision_name = ai_config.get("vision_provider") or self.primary
        self.fallback = ai_config.get("fallback_provider") or None
        self.local_only = bool(ai_config.get("local_only", False))
        self.providers = dict(providers or {})
        for name in dict.fromkeys([self.primary, self.vision_name, self.fallback]):
            if name and name not in self.providers:
                self.providers[name] = build_provider(name, config)
        if self.local_only:
            self._enforce_local()

        # Identidad: viene del paquete de personaje, no del proveedor de IA
        self.persona = persona if persona is not None else load_active_persona(config)
        self.system_prompt = build_system_prompt(self.persona.prompt)
        self.vision_prompt = build_vision_prompt(self.persona.name)
        memory_config = config.get("memory", {})
        self.memory = (
            memory
            if memory is not None
            else MemoryStore(resolve_path(config.get("paths", {}).get("memory_db", "data/meka.db")))
        )
        persist = memory_config.get("persist_history", True)
        self.history = ConversationStore(
            ai_config.get("history_size", 20), self.memory if persist else None
        )
        self.remember_pattern = re.compile(
            memory_config.get("remember_pattern") or DEFAULT_REMEMBER_PATTERN,
            re.IGNORECASE | re.DOTALL,
        )
        self.recall_triggers = tuple(
            normalize_text(t).strip()
            for t in memory_config.get("recall_triggers", DEFAULT_RECALL_TRIGGERS)
        )
        self.memory_limit = memory_config.get("search_limit", 5)

        # Memoria semántica: si el usuario pregunta por el pasado basta una similitud baja;
        # sin pregunta explícita, solo se añaden recuerdos muy relacionados (auto_recall)
        semantic_config = memory_config.get("semantic") or {}
        self.semantic = semantic
        self.min_similarity = float(semantic_config.get("min_similarity", 0.35))
        self.auto_recall = float(semantic_config.get("auto_recall_similarity", 0.6))
        self.log_conversations = config.get("app", {}).get("log_conversations", True)
        logger.info(f"Cerebro: {self.describe()}")

    def describe(self) -> str:
        names = {"chat": self.primary, "visión": self.vision_name, "respaldo": self.fallback}
        return " · ".join(
            f"{role}={name} ({self.providers[name].model})" for role, name in names.items() if name
        )

    def _enforce_local(self):
        """`ai.local_only`: ninguna conversación sale del equipo."""
        cloud = [n for n, p in self.providers.items() if not p.local]
        if cloud:
            logger.warning(f"ai.local_only activo: se ignoran {', '.join(cloud)}; se usa Ollama")
            if "ollama" not in self.providers:
                self.providers["ollama"] = build_provider("ollama", {})
            for role in ("primary", "vision_name", "fallback"):
                if getattr(self, role) in cloud:
                    setattr(self, role, "ollama" if role != "fallback" else None)

    def check_health(self) -> bool:
        """Verifica el proveedor principal (y el de visión si es otro)."""
        names = dict.fromkeys([self.primary, self.vision_name])
        return all(self.providers[name].check_health() for name in names)

    def _log(self, role: str, message: str):
        if self.log_conversations:
            log_conversation(role, message)

    async def _chat(
        self, system: str, messages: list[dict], *, vision=False
    ) -> tuple[str, int, str]:
        """Pregunta al proveedor que toque; si falla, al de respaldo."""
        order = [self.vision_name if vision else self.primary]
        if self.fallback and self.fallback not in order:
            order.append(self.fallback)
        for index, name in enumerate(order):
            start = time.perf_counter()
            try:
                text = await self.providers[name].chat(system, messages, vision=vision)
            except ProviderError as e:
                if index == len(order) - 1:
                    raise
                logger.warning(f"{e}. Se prueba con '{order[index + 1]}'")
                continue
            return text, int((time.perf_counter() - start) * 1000), name
        raise ProviderError("Ningún proveedor respondió")  # pragma: no cover

    async def recall(self, user_id: int | str, query: str, *, asked: bool = True) -> list[str]:
        """Recuerdos relevantes: primero por significado, después por palabras."""
        found: list[str] = []
        if self.semantic is not None:
            threshold = self.min_similarity if asked else self.auto_recall
            if threshold > 0:
                hits = await self.semantic.search(user_id, query, self.memory_limit)
                found = [fact for fact, similarity in hits if similarity >= threshold]
        if asked:
            for fact in self.memory.search(user_id, query, limit=self.memory_limit):
                if fact not in found:
                    found.append(fact)
        return found[: self.memory_limit]

    async def _memory_context(self, user_id: int | str, user_text: str) -> str:
        """Guarda "recuerda esto: ..." y añade al prompt los recuerdos que vengan al caso."""
        match = self.remember_pattern.search(user_text)
        if match:
            self.memory.add_fact(user_id, match.group(1).strip())
            return ""  # Acaba de contarlo: no hace falta recordárselo

        normalized = normalize_text(user_text)
        asked = any(trigger in normalized for trigger in self.recall_triggers)
        if not asked and self.semantic is None:
            return ""
        memories = await self.recall(user_id, user_text, asked=asked)
        if not memories:
            return ""
        return MEMORY_CONTEXT_TEMPLATE.format(memories="\n".join(f"- {m}" for m in memories))

    async def generate_response(
        self, chat_id: int | str, user_id: int | str, user_text: str, *, use_memory: bool = True
    ) -> list[str]:
        """Genera una respuesta y la divide en varios mensajes."""
        self._log("User", user_text)
        context = await self._memory_context(user_id, user_text) if use_memory else ""
        messages = [*self.history.get(chat_id), {"role": "user", "content": user_text}]

        try:
            raw_text, latency_ms, used = await self._chat(self.system_prompt + context, messages)
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            return [self.persona.line("error")]

        if not raw_text:
            return [self.persona.line("empty_reply")]

        # Solo se guarda en el historial si la llamada tuvo éxito
        self.history.add_exchange(chat_id, user_text, raw_text)
        bot_messages = split_into_messages(raw_text)

        logger.info(f"Respuesta generada en {latency_ms}ms | {used}")
        self._log(self.persona.name, f"({latency_ms}ms) " + " | ".join(bot_messages))
        return bot_messages

    async def generate_multimodal_response(
        self, chat_id: int | str, user_text: str, image_path
    ) -> list[str]:
        """Analiza una imagen con el proveedor de visión."""
        self._log("User (Multimodal)", f"{user_text} [Imagen]")
        messages = [{"role": "user", "content": user_text, "images": [str(image_path)]}]

        try:
            logger.info("Enviando imagen al modelo para análisis...")
            raw_text, latency_ms, used = await self._chat(self.vision_prompt, messages, vision=True)
        except Exception as e:
            logger.error(f"Error en análisis multimodal: {e}")
            return [self.persona.line("vision_error")]

        # El archivo de la imagen se borra tras procesarse: en el historial guardamos solo
        # texto. Guardar la ruta hacía fallar todas las respuestas posteriores del chat.
        self.history.add_exchange(chat_id, f"[Te envié una imagen] {user_text}", raw_text)

        logger.info(f"Análisis multimodal completado en {latency_ms}ms | {used}")
        self._log(f"{self.persona.name} (visión)", f"({latency_ms}ms) {raw_text}")
        return split_paragraphs(raw_text) or [self.persona.line("empty_reply")]

    def reset_conversation(self, chat_id: int | str):
        self.history.clear(chat_id)

    def unload_model(self):
        """Libera los modelos locales (Ollama) al apagar."""
        for provider in self.providers.values():
            provider.unload()
