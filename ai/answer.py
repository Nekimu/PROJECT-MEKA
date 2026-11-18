"""Respuesta del cerebro lista para el motor."""

from dataclasses import dataclass, field


@dataclass
class Answer:
    """Mensajes de la respuesta y si todo salió bien."""

    messages: list[str] = field(default_factory=list)
    ok: bool = True
    provider: str | None = None
    model: str | None = None
    latency_ms: int = 0
    private: bool = False  # Atendida solo por proveedores locales
