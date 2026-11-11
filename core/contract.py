"""Contrato entre MEKA Core y sus clientes (mascota en Go/web, app móvil, Telegram, MCP).

Única fuente de verdad: el bus de eventos (core/events.py), la validación de la API y
`GET /v1/contract` salen de aquí. Los clientes pueden leerlo en tiempo de ejecución en vez
de copiar estas listas a mano.

Tipos de los campos: "str", "bool", "int", "float", "dict", "emotion" (una de EMOTIONS);
con "?" al final, el campo es opcional.

Reglas de versión (las comprueba tests/test_contract.py):
- Añadir un evento, un campo opcional o una ruta  → sube el menor (1.4 → 1.5).
- Quitar o renombrar algo, o volver obligatorio un campo → sube el mayor (1.x → 2.0) y
  avisa al frontend en coordinacion/README.md antes de publicarlo.

Historial:
- 1.0  Eventos base de la mascota y API REST (chat, voz, archivos, memoria).
- 1.1  `GET /v1/runs`; `emotion: error/sad` cuando algo falla (T-020, T-021).
- 1.2  `private` en chat, voz, archivos, `user.message` y recuerdos (T-019, T-031).
- 1.3  Permisos: `agent.confirmed`, `user.confirm`, `/v1/confirmations` (T-003).
- 1.4  `GET /v1/contract` y versión del contrato en `/v1/health` (T-007).
"""

CONTRACT_VERSION = "1.4"

EMOTIONS = frozenset({
    "idle", "happy", "working", "thinking", "sleeping", "eating", "error", "celebrate", "sad",
})  # fmt: skip

# Del núcleo a los clientes: tipo → campos de `data`
OUTBOUND: dict[str, dict[str, str]] = {
    "agent.working": {"task": "str?"},
    "agent.done": {"summary": "str?"},
    "agent.error": {"message": "str?"},
    "agent.confirm": {
        "id": "str",
        "action": "str",
        "timeout": "int",  # Segundos que quedan para responder
        "expires_at": "float",  # Epoch en segundos
        "details": "dict?",
    },
    "agent.confirmed": {"id": "str", "approved": "bool", "by": "str"},
    "message": {"text": "str", "emotion": "emotion?"},  # El núcleo siempre la envía
    "emotion": {"emotion": "emotion"},
    "budget.low": {},
}

# De los clientes al núcleo (WebSocket /v1/events)
INBOUND: dict[str, dict[str, str]] = {
    "client.hello": {"client": "str", "skin": "str?"},
    "user.message": {"text": "str", "private": "bool?"},
    "user.confirm": {"id": "str", "approved": "bool"},
}

# Solo los emite el núcleo: llevan un id del registro de confirmaciones (core/confirmations.py).
# Un agente externo pide permiso con POST /v1/confirmations, no publicándolos a mano.
CORE_ONLY_EVENTS = frozenset({"agent.confirm", "agent.confirmed"})


def describe() -> dict:
    """Eventos y emociones en un formato serializable (la parte REST la añade el servidor)."""
    return {
        "version": CONTRACT_VERSION,
        "emotions": sorted(EMOTIONS),
        "events": {
            "outbound": OUTBOUND,
            "inbound": INBOUND,
            "core_only": sorted(CORE_ONLY_EVENTS),
        },
    }


_TYPES = {
    "str": lambda v: isinstance(v, str),
    "bool": lambda v: isinstance(v, bool),
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "dict": lambda v: isinstance(v, dict),
    "emotion": lambda v: v in EMOTIONS,
}


def validate(type_: str, data: dict, *, inbound: bool = False) -> list[str]:
    """Errores de un evento frente al contrato (vacío = válido). Los campos extra se
    permiten: así un cliente antiguo no rompe con un núcleo más nuevo."""
    spec = (INBOUND if inbound else OUTBOUND).get(type_)
    if spec is None:
        return [f"Evento desconocido: {type_!r}"]
    errors = []
    for name, kind in spec.items():
        optional = kind.endswith("?")
        kind = kind.rstrip("?")
        if name not in data or data[name] is None:
            if not optional:
                errors.append(f"{type_}: falta el campo obligatorio {name!r}")
        elif not _TYPES[kind](data[name]):
            expected = f"una de {sorted(EMOTIONS)}" if kind == "emotion" else kind
            errors.append(f"{type_}.{name}: se esperaba {expected}")
    return errors
