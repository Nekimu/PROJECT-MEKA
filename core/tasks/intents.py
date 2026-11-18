"""Qué pide el usuario sobre su agenda, dicho con naturalidad:

- **Añadir**: «recuérdame pagar la luz antes del 15», «apunta comprar pan», «ponme un
  recordatorio para llamar a mamá mañana a las 5». Varias en un mensaje también valen.
- **Consultar**: «¿qué tareas me quedan?», «mis pendientes», «¿qué tengo hoy?».
- **Completar**: «ya pagué la luz», «marca comprar pan como hecha».

Reglas sin modelo: funcionan con cualquier cerebro y con la transcripción de una nota de voz.
«Recuerda esto: …» sigue siendo un recuerdo (ai/recall.py), no una tarea.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from core.tasks.when import When, fold, numbers_as_digits, parse_when

_ADD = re.compile(
    r"\b(?:recuerdame|recuerda\s+me|recordarme|recuerdeme|no\s+me\s+dejes\s+olvidar|"
    r"(?:pon|ponme|crea|creame)\s+(?:un\s+)?recordatorio(?:\s+(?:para|de))?|"
    r"(?:anade|agrega|apunta|anota)(?:me)?(?:\s+(?:a\s+)?(?:mis|la\s+lista\s+de)\s+"
    r"(?:tareas|pendientes))?(?:\s+(?:la|una|como))?(?:\s+(?:tarea|pendiente))?|"
    r"nueva\s+tarea|tengo\s+pendiente)\b\s*:?\s*(?:que\s+|de\s+)?"
)
_END = re.compile(
    r"[.;?!\n]|,?\s+y\s+(?:dime|lista|muestra|ensename|que|cuales|cual|recuerdame|tambien|"
    r"apunta|anota|agrega)\b|,\s*(?:dime|que|cuales)\b"
)
_LIST = re.compile(
    r"\b(?:que|cuales|cual)\s+(?:son\s+)?(?:mis\s+|las\s+)?(?:tareas|pendientes|recordatorios)\b|"
    r"\bmis\s+(?:tareas|pendientes|recordatorios)\b|"
    r"\b(?:tareas|pendientes|recordatorios)\s+(?:tengo|me\s+quedan|hay|pendientes)\b|"
    r"\bque\s+(?:tengo|me\s+queda)\s+(?:pendiente|que\s+hacer|para\s+hoy|hoy|manana)\b|"
    r"\bmi\s+agenda\b"
)
PAST_VERBS = {
    "pague": "pagar", "termine": "terminar", "hice": "hacer", "complete": "completar",
    "envie": "enviar", "entregue": "entregar", "compre": "comprar", "llame": "llamar",
    "revise": "revisar", "saque": "sacar", "tome": "tomar", "acabe": "acabar",
    "mande": "mandar", "estudie": "estudiar", "limpie": "limpiar", "regue": "regar",
}  # fmt: skip
_DONE = re.compile(
    r"\bya\s+(" + "|".join(PAST_VERBS) + r")\b\s*(.*)|"
    r"\bmarca(?:r)?\s+(?:la\s+tarea\s+)?(.+?)\s+como\s+(?:hecha|terminada|completada|lista)\b"
)
_TRAILING = re.compile(r"(?:\s+(?:para|antes|el|la|de|del|a|que|y|hasta|en))+\s*$")
STOP = {"para", "antes", "que", "las", "los", "una", "del", "con", "por", "the", "mis", "tus"}


@dataclass
class Request:
    add: list[tuple[str, When]] = field(default_factory=list)
    show: bool = False
    done: str | None = None  # Lo que dijo que ya hizo («pagar la luz»)

    @property
    def any(self) -> bool:
        return bool(self.add or self.show or self.done)


def understand(text: str, now: datetime, *, morning_hour: int = 9) -> Request:
    text = numbers_as_digits(text)
    folded = fold(text)
    request = Request(show=bool(_LIST.search(folded)))
    for match in _ADD.finditer(folded):
        start = match.end()
        end_match = _END.search(folded, start)
        end = end_match.start() if end_match else len(text)
        segment = text[start:end]
        when = parse_when(segment, now, morning_hour=morning_hour)
        title = _clean(segment, when)
        if title:
            request.add.append((title, when))
    done = _DONE.search(folded)
    if done and not request.add:
        if done.group(1):
            end_match = _END.search(folded, done.end(1))
            rest = text[done.end(1) : end_match.start() if end_match else len(text)]
            request.done = f"{PAST_VERBS[done.group(1)]} {rest}".strip()
        else:
            request.done = text[done.start(3) : done.end(3)].strip()
    return request


def _clean(segment: str, when: When) -> str:
    chars = list(segment)
    for start, end in when.spans:
        chars[start:end] = [" "] * (end - start)
    title = " ".join("".join(chars).split()).strip(" ,.:;-")
    trailing = _TRAILING.search(fold(title))
    if trailing:
        title = title[: trailing.start()]
    return title.strip(" ,.:;-")


def keywords(text: str) -> set[str]:
    """Raíces para comparar lo que dijo con los títulos («pagué la luz» ~ «pagar la luz»)."""
    words = re.findall(r"\w+", fold(text))
    words = [PAST_VERBS.get(w, w) for w in words]
    return {w[:5] for w in words if len(w) >= 3 and w not in STOP}


def best_match(said: str, titles: dict[int, str]) -> int | None:
    """El id de la tarea que mejor encaja, o None si no hay una clara."""
    wanted = keywords(said)
    scores = sorted(
        ((len(wanted & keywords(title)), task_id) for task_id, title in titles.items()),
        reverse=True,
    )
    if not scores or scores[0][0] == 0:
        return None
    if len(scores) > 1 and scores[1][0] == scores[0][0]:
        return None  # Empate: mejor preguntar que marcar la equivocada
    return scores[0][1]
