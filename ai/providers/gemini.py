"""Gemini (Google): cerebro en la nube. Requiere GEMINI_API_KEY en .env.

Ojo con la privacidad: en el nivel gratuito Google puede usar las conversaciones
para mejorar sus productos.
"""

import importlib.util
import os

from ai.providers.base import ProviderError, RefusalError, image_bytes
from core.logger import setup_logger

logger = setup_logger("Gemini")


class GeminiProvider:
    name = "gemini"
    local = False

    def __init__(self, settings: dict, client=None):
        # Alias que Google actualiza con cada versión de Flash; fija uno concreto si prefieres
        self.model = settings.get("model", "gemini-flash-latest")
        self.temperature = settings.get("temperature", 0.8)
        self.max_output_tokens = int(settings.get("max_output_tokens", 2048))
        self._client = client

    @property
    def client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as e:
                raise ProviderError(
                    "Falta el SDK de Gemini: pip install -r requirements-cloud.txt"
                ) from e
            if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
                raise ProviderError("Gemini: falta GEMINI_API_KEY en .env")
            self._client = genai.Client()  # Lee GEMINI_API_KEY (o GOOGLE_API_KEY) del entorno
        return self._client

    async def chat(self, system: str, messages: list[dict], *, vision: bool = False) -> str:
        from google.genai import types

        contents = []
        for message in messages:
            parts = [types.Part.from_bytes(data=d, mime_type=m)
                     for d, m in map(image_bytes, message.get("images") or [])]  # fmt: skip
            parts.append(types.Part.from_text(text=message["content"]))
            role = "model" if message["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=parts))

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model, contents=contents, config=config
            )
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Gemini: {e}") from e

        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None and getattr(feedback, "block_reason", None):
            raise RefusalError(f"Gemini bloqueó la petición ({feedback.block_reason})")
        return (response.text or "").strip()

    def check_health(self) -> bool:
        try:
            installed = importlib.util.find_spec("google.genai") is not None
        except ModuleNotFoundError:
            installed = False
        if not installed:
            logger.critical("Falta el SDK de Gemini: pip install -r requirements-cloud.txt")
            return False
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            logger.warning("No hay GEMINI_API_KEY en .env: Gemini no podrá responder")
            return False
        return True

    def unload(self):
        pass
