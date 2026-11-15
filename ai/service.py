"""Servicio de IA: personaje + memoria + el proveedor elegido (Ollama, Claude o Gemini)."""

import time

from ai import privacy
from ai.answer import Answer
from ai.multimodal import MultimodalMixin
from ai.prompts import build_system_prompt, build_vision_prompt
from ai.providers import Provider, ProviderError, ProviderReply, build_provider
from ai.recall import Recall
from ai.routing import PrivacyError, Router
from ai.text_utils import split_into_messages
from core.config import resolve_path, settings
from core.history import ConversationStore
from core.logger import log_conversation, setup_logger
from core.memory import MemoryStore
from core.persona import Persona, load_active_persona
from core.runs import Run, RunLog
from core.semantic import SemanticMemory

logger = setup_logger("AI_Service")


__all__ = ["AIService", "Answer"]


class AIService(MultimodalMixin):
    def __init__(
        self,
        config: dict | None = None,
        *,
        memory=None,
        persona: Persona | None = None,
        providers: dict[str, Provider] | None = None,
        semantic: SemanticMemory | None = None,
        runs: RunLog | None = None,
    ):
        config = settings if config is None else config
        ai_config = config.get("ai", {})

        # Enrutamiento por tarea y privacidad (ai/routing.py)
        self.providers = dict(providers or {})
        for name in Router.needed(ai_config):
            if name not in self.providers:
                self.providers[name] = build_provider(name, config)
        self.router = Router(ai_config, self.providers)
        if self.router.local_only:
            self.router.enforce_local()
        privacy_config = ai_config.get("privacy") or {}
        self.private_documents = privacy_config.get("documents", True)
        self.detect_sensitive = privacy_config.get("detect_sensitive", True)
        # El audio no pasa por el detector de datos sensibles: a la nube solo si se permite
        self.audio_to_cloud = bool(privacy_config.get("audio_to_cloud", False))

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
        self.semantic = semantic
        self.recaller = Recall(self.memory, semantic, memory_config)  # ai/recall.py
        self.log_conversations = config.get("app", {}).get("log_conversations", True)
        self.runs = runs  # Registro de ejecución sin contenido (core/runs.py)
        logger.info(f"Cerebro: {self.describe()}")

    def describe(self) -> str:
        return self.router.describe()

    def check_health(self) -> bool:
        """Verifica los proveedores de la conversación y de la visión."""
        return all(self.providers[name].check_health() for name in self.router.health_targets())

    def _privacy(self, chat_id, text: str, requested: bool) -> bool:
        """¿Esta petición es privada? Lo es si se pide, si la conversación ya lo era o si
        el texto contiene datos sensibles. Una vez privada, lo sigue siendo hasta el reset."""
        if not (requested or self.history.is_private(chat_id)):
            reason = privacy.detect(text) if self.detect_sensitive else None
            if reason is None:
                return False
            logger.warning(f"Dato sensible detectado ({reason}): la conversación pasa a privada")
        self.history.mark_private(chat_id)
        return True

    def _log(self, role: str, message: str):
        if self.log_conversations:
            log_conversation(role, message)

    def _record(self, task: str, name: str, latency_ms: int, reply=None, error=None):
        """Anota la llamada en el registro de ejecución. Nunca guarda el texto."""
        if self.runs is None:
            return
        try:
            self.runs.record(
                Run(
                    task=task,
                    provider=name,
                    model=self.providers[name].model,
                    ok=error is None,
                    latency_ms=latency_ms,
                    input_tokens=getattr(reply, "input_tokens", None),
                    output_tokens=getattr(reply, "output_tokens", None),
                    error=type(error).__name__ if error else None,
                )
            )
        except Exception as e:  # El registro nunca debe impedir responder
            logger.warning(f"No se pudo guardar el registro de ejecución: {e}")

    async def _chat(
        self,
        system: str,
        messages: list[dict],
        *,
        task: str = "chat",
        private: bool = False,
        need: str | None = None,
    ) -> tuple[ProviderReply, int, str]:
        """Pregunta al proveedor que toque; si falla, al de respaldo (local si es privado).
        Con `need`, solo a los que entienden esa entrada de forma nativa (T-053)."""
        vision = task == "vision"
        order = self.router.order(task, private=private, need=need)
        for index, name in enumerate(order):
            start = time.perf_counter()
            try:
                reply = await self.providers[name].chat(system, messages, vision=vision)
            except ProviderError as e:
                self._record(task, name, int((time.perf_counter() - start) * 1000), error=e)
                if index == len(order) - 1:
                    raise
                logger.warning(f"{e}. Se prueba con '{order[index + 1]}'")
                continue
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._record(task, name, latency_ms, reply)
            return reply, latency_ms, name
        raise ProviderError("Ningún proveedor respondió")  # pragma: no cover

    def decide_privacy(self, chat_id, text: str, requested: bool = False) -> bool:
        """¿Será privada esta petición? (la decisión que tomará `answer`; queda anotada)."""
        return self._privacy(chat_id, text, requested)

    def stays_local(self, task: str, private: bool) -> bool:
        return self._stays_local(task, private)

    def _stays_local(self, task: str, private: bool) -> bool:
        """¿Todos los proveedores que podrían atender esta petición (respaldo incluido) son
        locales? Solo entonces pueden ir al prompt los recuerdos privados."""
        try:
            names = self.router.order(task, private=private)
        except PrivacyError:
            return False
        return all(self.providers[name].local for name in names)

    async def recall(
        self, user_id: int | str, query: str, *, asked: bool = True, include_private: bool = True
    ) -> list[str]:
        """Recuerdos relevantes (por significado y por palabras)."""
        return await self.recaller.search(
            user_id, query, asked=asked, include_private=include_private
        )

    async def answer(
        self,
        chat_id: int | str,
        user_id: int | str,
        user_text: str,
        *,
        use_memory: bool = True,
        task: str = "chat",
        private: bool = False,
        extra_context: str = "",
    ) -> Answer:
        """Genera una respuesta dividida en varios mensajes, con su resultado.
        `extra_context`: datos reales que el cerebro debe conocer (la agenda, core/tasks/)."""
        self._log("User", user_text)
        requested = private or (task == "document" and self.private_documents)
        private = self._privacy(chat_id, user_text, requested)
        context = (
            await self.recaller.context(
                user_id, user_text, private=private, local=self._stays_local(task, private)
            )
            if use_memory
            else ""
        )
        messages = [*self.history.get(chat_id), {"role": "user", "content": user_text}]

        try:
            reply, latency_ms, used = await self._chat(
                self.system_prompt + context + extra_context, messages, task=task, private=private
            )
        except Exception as e:
            logger.error(f"Error generando respuesta: {e}")
            return Answer([self.persona.line("error")], ok=False, private=private)

        if not reply.text:
            return Answer([self.persona.line("empty_reply")], False, used, private=private)

        # Solo se guarda en el historial si la llamada tuvo éxito
        self.history.add_exchange(chat_id, user_text, reply.text)
        bot_messages = split_into_messages(reply.text)

        logger.info(f"Respuesta generada en {latency_ms}ms | {used}")
        self._log(self.persona.name, f"({latency_ms}ms) " + " | ".join(bot_messages))
        return Answer(bot_messages, True, used, self.providers[used].model, latency_ms, private)

    # Compatibilidad: devuelven solo los mensajes
    async def generate_response(self, chat_id, user_id, user_text, *, use_memory=True) -> list[str]:
        return (await self.answer(chat_id, user_id, user_text, use_memory=use_memory)).messages

    async def generate_multimodal_response(self, chat_id, user_text, image_path) -> list[str]:
        return (await self.answer_image(chat_id, user_text, image_path)).messages

    def reset_conversation(self, chat_id: int | str):
        self.history.clear(chat_id)

    def unload_model(self):
        """Libera los modelos locales (Ollama) al apagar."""
        for provider in self.providers.values():
            provider.unload()
