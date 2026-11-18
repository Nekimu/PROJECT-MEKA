"""Detección de datos sensibles (filosofía híbrida §8): si un mensaje los contiene, la
conversación pasa a modo privado y solo la atienden proveedores locales.

Es una red de seguridad, no una garantía: detecta lo habitual (contraseñas dichas en el
chat, llaves de API, tokens, tarjetas, CURP). Para lo demás está la marca `private`.
"""

import re

# (motivo, patrón). El motivo va a los logs; el texto detectado nunca.
PATTERNS = [
    ("credencial", re.compile(
        r"\b(contrase[ñn]a|password|passwd|clave|nip|pin|cvv|cvc|token|api[ _-]?key|secret[oa]?)"
        r"\b\s*(?:es|era|:|=|is)\s*\S{3,}",
        re.IGNORECASE,
    )),
    ("llave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("llave de API", re.compile(
        r"\b(sk-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}"
        r"|gh[pousr]_[A-Za-z0-9]{36,}|xox[abprs]-[A-Za-z0-9-]{10,})\b"
    )),
    ("token JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("CURP", re.compile(r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b")),
]  # fmt: skip
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn(number: str) -> bool:
    digits = [int(d) for d in number][::-1]
    total = sum(digits[0::2]) + sum(sum(divmod(2 * d, 10)) for d in digits[1::2])
    return total % 10 == 0


def detect(text: str) -> str | None:
    """Motivo por el que el texto parece sensible, o None."""
    for reason, pattern in PATTERNS:
        if pattern.search(text):
            return reason
    for match in CARD.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            return "número de tarjeta"
    return None
