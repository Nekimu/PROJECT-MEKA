"""Contrato común de los proveedores de IA (Ollama, Claude, Gemini...).

Todos reciben lo mismo: un prompt de sistema y una lista de mensajes
`{"role": "user" | "assistant", "content": str, "images": [ruta, ...]}`,
y devuelven texto. Cada adaptador traduce ese formato al de su API.
"""

import mimetypes
from pathlib import Path
from typing import Protocol


class ProviderError(RuntimeError):
    """El proveedor no está disponible o falló la llamada."""


class RefusalError(ProviderError):
    """El proveedor se negó a responder (políticas de seguridad)."""


class Provider(Protocol):
    name: str
    model: str
    local: bool  # True = la conversación no sale del equipo

    async def chat(self, system: str, messages: list[dict], *, vision: bool = False) -> str: ...

    def check_health(self) -> bool: ...

    def unload(self) -> None: ...


def image_bytes(path: str | Path) -> tuple[bytes, str]:
    """Lee una imagen y adivina su tipo MIME (las APIs en la nube lo piden)."""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return path.read_bytes(), mime


def build_provider(name: str, config: dict) -> Provider:
    """Crea el adaptador `name` con su sección `ai.providers.<name>` de config.yml."""
    settings = (config.get("ai", {}).get("providers") or {}).get(name) or {}
    if name == "ollama":
        from ai.providers.ollama import OllamaProvider

        return OllamaProvider(settings)
    if name == "claude":
        from ai.providers.claude import ClaudeProvider

        return ClaudeProvider(settings)
    if name == "gemini":
        from ai.providers.gemini import GeminiProvider

        return GeminiProvider(settings)
    raise ProviderError(f"Proveedor de IA desconocido: {name!r}. Opciones: ollama, claude, gemini")
