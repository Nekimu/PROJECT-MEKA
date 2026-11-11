"""Rutas de MEKA Core agrupadas por dominio. Una ruta nueva va al módulo de su dominio."""

from server.routes import (
    confirmations,
    contract,
    conversation,
    events,
    memory,
    runs,
    status,
    voice,
)

ROUTERS = [
    status.router,
    contract.router,
    runs.router,
    conversation.router,
    voice.router,
    memory.router,
    events.router,
    confirmations.router,
]
