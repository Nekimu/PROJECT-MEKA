"""Contrato común de los proveedores de IA (Ollama, Claude, Gemini...).

Todos reciben lo mismo: un prompt de sistema y una lista de mensajes
`{"role": "user" | "assistant", "content": str, "images": [ruta, ...]}`,
y devuelven un `ProviderReply` normalizado: el texto y, si la API lo informa, el uso
de tokens. Cada adaptador traduce ese formato al de su API.
"""

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class ProviderReply:
    """Respuesta normalizada: el resto de MEKA no sabe qué proveedor la generó."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderError(RuntimeError):
    """El proveedor no está disponible o falló la llamada."""


class RefusalError(ProviderError):
    """El proveedor se negó a responder (políticas de seguridad)."""


# Lo que un cerebro puede entender de forma nativa (T-053). Depende del MODELO, no solo del
# proveedor: cada adaptador trae las suyas por defecto y config.yml las corrige con
# `ai.providers.<nombre>.capabilities`. Si un cerebro no entiende algo, MEKA usa otra ruta
# (transcribir el audio, extraer el texto del PDF...).
CAPABILITIES = frozenset({"text", "vision", "audio", "pdf"})


class Provider(Protocol):
    name: str
    model: str
    local: bool  # True = la conversación no sale del equipo
    capabilities: frozenset[str]

    async def chat(
        self, system: str, messages: list[dict], *, vision: bool = False
    ) -> ProviderReply: ...

    def check_health(self) -> bool: ...

    def unload(self) -> None: ...


def image_bytes(path: str | Path) -> tuple[bytes, str]:
    """Lee una imagen y adivina su tipo MIME (las APIs en la nube lo piden)."""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return path.read_bytes(), mime


def file_bytes(path: str | Path, default_mime: str) -> tuple[bytes, str]:
    """Audio o documento con su tipo MIME."""
    path = Path(path)
    return path.read_bytes(), mimetypes.guess_type(path.name)[0] or default_mime


def build_provider(name: str, config: dict) -> Provider:
    """Crea el adaptador `name` con su sección `ai.providers.<name>` de config.yml."""
    settings = (config.get("ai", {}).get("providers") or {}).get(name) or {}
    if name == "ollama":
        from ai.providers.ollama import OllamaProvider as Adapter
    elif name == "claude":
        from ai.providers.claude import ClaudeProvider as Adapter
    elif name == "gemini":
        from ai.providers.gemini import GeminiProvider as Adapter
    elif name == "openai_compat":  # llama.cpp, LM Studio, vLLM... (T-054)
        from ai.providers.openai_compat import OpenAICompatProvider as Adapter
    else:
        raise ProviderError(
            f"Proveedor de IA desconocido: {name!r}. "
            "Opciones: ollama, claude, gemini, openai_compat"
        )
    provider = Adapter(settings)
    return with_capabilities(provider, settings.get("capabilities"))


def with_capabilities(provider, declared) -> Provider:
    """Aplica las capacidades declaradas en config.yml (si las hay) sobre las del adaptador."""
    if declared:
        unknown = set(declared) - CAPABILITIES
        if unknown:
            raise ProviderError(
                f"Capacidades desconocidas en {provider.name}: {sorted(unknown)}. "
                f"Opciones: {sorted(CAPABILITIES)}"
            )
        provider.capabilities = frozenset(declared) | {"text"}
    return provider
