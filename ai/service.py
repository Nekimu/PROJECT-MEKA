import asyncio
import re
import time
from collections import deque

import ollama
from ollama import Client

from ai.prompts import MEMORY_CONTEXT_TEMPLATE, build_system_prompt, build_vision_prompt
from ai.text_utils import split_into_messages, split_paragraphs
from core.config import resolve_path, settings
from core.logger import log_conversation, setup_logger
from core.memory import MemorySystem, normalize_text
from core.persona import Persona, load_active_persona

logger = setup_logger("AI_Service")

DEFAULT_OPTIONS = {
    "num_predict": 512,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.2,  # Penaliza la repetición de palabras/frases
    "repeat_last_n": 64,  # Cuánto atrás mirar para penalizar
}
DEFAULT_VISION_OPTIONS = {"temperature": 0.6, "num_predict": 1024}  # Menor temperatura: precisión

# Valores por defecto de la sección `memory` de config.yml
DEFAULT_REMEMBER_PATTERN = r"recuerda\s+esto\s*:\s*(.+)"
DEFAULT_RECALL_TRIGGERS = ("recuerdas", "te acuerdas", "sabes algo de", "que me dijiste de")


class ConversationStore:
    """Historial reciente de mensajes, separado por chat (antes era global y se mezclaba)."""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._chats: dict[int, deque] = {}

    def get(self, chat_id: int | str) -> list[dict]:
        return list(self._chats.get(chat_id, ()))

    def add_exchange(self, chat_id: int | str, user_text: str, assistant_text: str):
        history = self._chats.setdefault(chat_id, deque(maxlen=self.max_messages))
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})

    def clear(self, chat_id: int | str):
        self._chats.pop(chat_id, None)


class AIService:
    def __init__(
        self,
        config: dict | None = None,
        client=None,
        memory=None,
        persona: Persona | None = None,
    ):
        config = settings if config is None else config
        ai_config = config.get("ai", {})
        self.model = ai_config.get("model", "gemma3:12b")
        self.host = ai_config.get("base_url", "http://localhost:11434")
        # keep_alive=0 libera la RAM inmediatamente después de responder
        self.keep_alive = ai_config.get("keep_alive", 0)
        self.options = {
            **DEFAULT_OPTIONS,
            "temperature": ai_config.get("temperature", 0.8),
            **(ai_config.get("options") or {}),
        }
        self.vision_options = {**DEFAULT_VISION_OPTIONS, **(ai_config.get("vision_options") or {})}

        # Identidad: viene del paquete de personaje, no del proveedor de IA
        self.persona = persona if persona is not None else load_active_persona(config)
        self.system_prompt = build_system_prompt(self.persona.prompt)
        self.vision_prompt = build_vision_prompt(self.persona.name)
        self.history = ConversationStore(ai_config.get("history_size", 20))

        memory_config = config.get("memory", {})
        self.memory = (
            memory
            if memory is not None
            else MemorySystem(
                resolve_path(config.get("paths", {}).get("memory_file", "memory.json"))
            )
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
        self.log_conversations = config.get("app", {}).get("log_conversations", True)
        self.client = client if client is not None else Client(host=self.host)
        logger.info(f"Cliente de Ollama configurado en {self.host} con el modelo {self.model}")

    def check_health(self) -> bool:
        """Verifica la conectividad con Ollama y que el modelo esté descargado."""
        try:
            self.client.show(self.model)
            return True
        except ollama.ResponseError as e:
            logger.critical(
                f"Ollama no tiene el modelo '{self.model}' ({e}). "
                f"Descárgalo con: ollama pull {self.model}"
            )
        except Exception as e:
            logger.critical(
                f"No se pudo conectar con Ollama en {self.host}: {e}. "
                "¿Está corriendo `ollama serve`?"
            )
        return False

    def _log(self, role: str, message: str):
        if self.log_conversations:
            log_conversation(role, message)

    async def _chat(self, messages: list[dict], options: dict) -> tuple[str, int]:
        """Llama a Ollama en un hilo aparte para no bloquear el event loop del bot."""
        start = time.perf_counter()
        response = await asyncio.to_thread(
            self.client.chat,
            model=self.model,
            messages=messages,
            options=options,
            keep_alive=self.keep_alive,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return (response.message.content or "").strip(), latency_ms

    def _memory_context(self, user_id: int | str, user_text: str) -> str:
        """Guarda "recuerda esto: ..." y recupera recuerdos si el usuario pregunta por ellos."""
        match = self.remember_pattern.search(user_text)
        if match:
            self.memory.add_fact(user_id, match.group(1).strip())

        normalized = normalize_text(user_text)
        if not any(trigger in normalized for trigger in self.recall_triggers):
            return ""
        memories = self.memory.search(user_id, user_text, limit=self.memory_limit)
        if not memories:
            return ""
        return MEMORY_CONTEXT_TEMPLATE.format(memories="\n".join(f"- {m}" for m in memories))

    async def generate_response(
        self, chat_id: int | str, user_id: int | str, user_text: str, *, use_memory: bool = True
    ) -> list[str]:
        """Genera una respuesta con Ollama y la divide en múltiples mensajes."""
        self._log("User", user_text)
        context = self._memory_context(user_id, user_text) if use_memory else ""
        messages = [
            {"role": "system", "content": self.system_prompt + context},
            *self.history.get(chat_id),
            {"role": "user", "content": user_text},
        ]

        try:
            raw_text, latency_ms = await self._chat(messages, self.options)
        except Exception as e:
            logger.error(f"Error generando respuesta con Ollama: {e}")
            return [self.persona.line("error")]

        if not raw_text:
            return [self.persona.line("empty_reply")]

        # Solo se guarda en el historial si la llamada tuvo éxito
        self.history.add_exchange(chat_id, user_text, raw_text)
        bot_messages = split_into_messages(raw_text)

        logger.info(f"Respuesta generada en {latency_ms}ms | Modelo: {self.model}")
        self._log(self.persona.name, f"({latency_ms}ms) " + " | ".join(bot_messages))
        return bot_messages

    async def generate_multimodal_response(
        self, chat_id: int | str, user_text: str, image_path
    ) -> list[str]:
        """Analiza una imagen utilizando la capacidad multimodal del modelo (p. ej. Gemma 3)."""
        self._log("User (Multimodal)", f"{user_text} [Imagen]")
        messages = [
            {"role": "system", "content": self.vision_prompt},
            {"role": "user", "content": user_text, "images": [str(image_path)]},
        ]

        try:
            logger.info("Enviando imagen al modelo para análisis...")
            raw_text, latency_ms = await self._chat(messages, self.vision_options)
        except Exception as e:
            logger.error(f"Error en análisis multimodal: {e}")
            return [self.persona.line("vision_error")]

        # El archivo de la imagen se borra tras procesarse: en el historial guardamos solo
        # texto. Guardar la ruta hacía fallar todas las respuestas posteriores del chat.
        self.history.add_exchange(chat_id, f"[Te envié una imagen] {user_text}", raw_text)

        logger.info(f"Análisis multimodal completado en {latency_ms}ms")
        self._log(f"{self.persona.name} (visión)", f"({latency_ms}ms) {raw_text}")
        return split_paragraphs(raw_text) or [self.persona.line("empty_reply")]

    def reset_conversation(self, chat_id: int | str):
        self.history.clear(chat_id)

    def unload_model(self):
        """Descarga el modelo de la memoria de Ollama."""
        try:
            logger.info(f"Descargando modelo {self.model} de memoria...")
            # Un chat vacío con keep_alive=0 descarga el modelo sin generar nada
            self.client.chat(model=self.model, messages=[], keep_alive=0)
        except Exception as e:
            logger.error(f"Error al descargar el modelo: {e}")
