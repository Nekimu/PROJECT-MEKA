"""Ollama: modelos locales. Nada sale del equipo."""

import asyncio

from ai.providers.base import ProviderError
from core.logger import setup_logger

logger = setup_logger("Ollama")

DEFAULT_OPTIONS = {
    "num_predict": 512,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.2,  # Penaliza la repetición de palabras/frases
    "repeat_last_n": 64,  # Cuánto atrás mirar para penalizar
}
DEFAULT_VISION_OPTIONS = {"temperature": 0.6, "num_predict": 1024}  # Menor temperatura: precisión


class OllamaProvider:
    name = "ollama"
    local = True

    def __init__(self, settings: dict, client=None):
        self.model = settings.get("model", "gemma3:12b")
        self.host = settings.get("base_url", "http://localhost:11434")
        # keep_alive=0 libera la RAM inmediatamente después de responder
        self.keep_alive = settings.get("keep_alive", 0)
        self.options = {
            **DEFAULT_OPTIONS,
            "temperature": settings.get("temperature", 0.8),
            **(settings.get("options") or {}),
        }
        self.vision_options = {**DEFAULT_VISION_OPTIONS, **(settings.get("vision_options") or {})}
        if client is None:
            from ollama import Client

            client = Client(host=self.host)
        self.client = client
        logger.info(f"Ollama configurado en {self.host} con el modelo {self.model}")

    async def chat(self, system: str, messages: list[dict], *, vision: bool = False) -> str:
        payload = [{"role": "system", "content": system}]
        for message in messages:
            item = {"role": message["role"], "content": message["content"]}
            if message.get("images"):
                item["images"] = [str(path) for path in message["images"]]
            payload.append(item)
        try:
            # En un hilo aparte para no bloquear el event loop del servidor
            response = await asyncio.to_thread(
                self.client.chat,
                model=self.model,
                messages=payload,
                options=self.vision_options if vision else self.options,
                keep_alive=self.keep_alive,
            )
        except Exception as e:
            raise ProviderError(f"Ollama: {e}") from e
        return (response.message.content or "").strip()

    def check_health(self) -> bool:
        """Verifica la conexión con Ollama y que el modelo esté descargado."""
        import ollama

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

    def unload(self):
        """Un chat vacío con keep_alive=0 descarga el modelo sin generar nada."""
        try:
            self.client.chat(model=self.model, messages=[], keep_alive=0)
        except Exception as e:
            logger.debug(f"No se pudo descargar el modelo de Ollama: {e}")
