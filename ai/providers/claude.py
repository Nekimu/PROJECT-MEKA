"""Claude (Anthropic): cerebro en la nube. Requiere ANTHROPIC_API_KEY en .env."""

import base64
import importlib.util
import os

from ai.providers.base import ProviderError, RefusalError, image_bytes
from core.logger import setup_logger

logger = setup_logger("Claude")

# Si un filtro de seguridad rechaza la petición, la API la repite con otro modelo
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeProvider:
    name = "claude"
    local = False

    def __init__(self, settings: dict, client=None):
        self.model = settings.get("model", "claude-opus-5-5")
        self.max_tokens = int(settings.get("max_tokens", 16000))
        # Para charlar basta "low": respuestas rápidas y baratas. Sube a "medium"/"high" si
        # quieres que piense más (documentos largos, tareas complejas).
        self.effort = settings.get("effort", "low")
        self.fallbacks = settings.get("fallbacks", True)
        self._client = client

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise ProviderError(
                    "Falta el SDK de Claude: pip install -r requirements-cloud.txt"
                ) from e
            self._client = anthropic.AsyncAnthropic()  # Lee ANTHROPIC_API_KEY del entorno
        return self._client

    @staticmethod
    def _content(message: dict):
        if not message.get("images"):
            return message["content"]
        blocks = []
        for path in message["images"]:
            data, mime = image_bytes(path)
            blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime,
                           "data": base64.standard_b64encode(data).decode()},
            })  # fmt: skip
        blocks.append({"type": "text", "text": message["content"]})
        return blocks

    async def chat(self, system: str, messages: list[dict], *, vision: bool = False) -> str:
        request = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": m["role"], "content": self._content(m)} for m in messages],
            "output_config": {"effort": self.effort},
            "cache_control": {"type": "ephemeral"},  # Reutiliza el prompt del personaje
        }
        try:
            if self.fallbacks:
                response = await self.client.beta.messages.create(
                    **request, betas=[FALLBACK_BETA], fallbacks="default"
                )
            else:
                response = await self.client.messages.create(**request)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Claude: {e}") from e

        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            raise RefusalError(f"Claude declinó responder (categoría: {category})")
        if response.stop_reason == "max_tokens":
            logger.warning("La respuesta de Claude se cortó por max_tokens")
        return "".join(b.text for b in response.content if b.type == "text").strip()

    def check_health(self) -> bool:
        if importlib.util.find_spec("anthropic") is None:
            logger.critical("Falta el SDK de Claude: pip install -r requirements-cloud.txt")
            return False
        if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
            logger.warning("No hay ANTHROPIC_API_KEY en .env: Claude no podrá responder")
            return False
        return True

    def unload(self):
        pass  # Nada que liberar: el modelo vive en la nube
