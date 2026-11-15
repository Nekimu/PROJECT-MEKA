"""Fechas y horas dichas en español: «antes del 15 de noviembre», «mañana a las 5 de la tarde».

Sin modelos ni dependencias: funciona igual con un cerebro diminuto o con la transcripción de
una nota de voz. Devuelve también qué parte del texto era la fecha, para quitarla del título.

Reglas para saber cuándo avisar:
- Con hora («a las 18:30», «en 2 horas»): vence y se avisa a esa hora.
- Solo el día («el viernes», «el 15»): vence al final de ese día y se avisa por la mañana.
- «Antes del 15»: vence al empezar el 15 y se avisa la mañana anterior.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]  # fmt: skip
WEEKDAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
NUMBER_WORDS = {
    "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13,
    "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintiuna": 21, "veintidos": 22,
    "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30,
    "treinta y uno": 31, "treinta y una": 31,
}  # fmt: skip

_ACCENTS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def fold(text: str) -> str:
    """Minúsculas y sin tildes, con la **misma longitud** (las posiciones siguen valiendo)."""
    folded = text.translate(_ACCENTS).lower()
    if len(folded) != len(text):  # Algún carácter raro: se cae a la forma segura
        folded = "".join(
            unicodedata.normalize("NFD", c)[0].lower() if c.isalpha() else c.lower() for c in text
        )
    return folded


_NUMBER = re.compile(r"\b(" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")\b")
_UNIT_AFTER = re.compile(r"\s+(?:minutos?|horas?|dias?|semanas?)\b")
_MONTH_AFTER = re.compile(r"\s+de\s+(?:" + "|".join(MONTHS) + r")\b")
_TIME_BEFORE = re.compile(r"\b(?:las|la)\s+$")
_DAY_BEFORE = re.compile(r"\b(?:el|del|dia)\s+$")


def numbers_as_digits(text: str) -> str:
    """«antes del quince de noviembre» → «antes del 15 de noviembre». Solo junto a palabras de
    tiempo, para no tocar «paga una factura»."""
    folded = fold(text)
    out, last = [], 0
    for match in _NUMBER.finditer(folded):
        word, before, after = match.group(1), folded[: match.start()], folded[match.end() :]
        if word in ("un", "una", "uno"):
            near_time = _UNIT_AFTER.match(after) or _TIME_BEFORE.search(before)
        else:
            near_time = (
                _UNIT_AFTER.match(after) or _MONTH_AFTER.match(after)
                or _TIME_BEFORE.search(before) or _DAY_BEFORE.search(before)
            )  # fmt: skip
        if near_time:
            out += [text[last : match.start()], str(NUMBER_WORDS[word])]
            last = match.end()
    out.append(text[last:])
    return "".join(out)


@dataclass
class When:
    due: datetime | None = None
    remind: datetime | None = None
    spans: list[tuple[int, int]] = field(default_factory=list)  # Posiciones en el texto

    @property
    def found(self) -> bool:
        return self.due is not None


_MONTH = "|".join(MONTHS)
_DAY_WORD = re.compile(r"\b(pasado\s+manana|manana|hoy|esta\s+noche|esta\s+tarde)\b")
_WEEKDAY = re.compile(
    r"\b(?:el\s+)?(?:proximo\s+)?(" + "|".join(WEEKDAYS) + r")(?:\s+que\s+viene)?\b"
)
_DATE = re.compile(
    r"\b(?:(antes\s+del?|para\s+el|hasta\s+el|el|del)\s+)?(?:dia\s+)?(\d{1,2})"
    r"(?:\s+de\s+(" + _MONTH + r")(?:\s+(?:de|del)\s+(\d{4}))?|/(\d{1,2})(?:/(\d{2,4}))?)"
)
_DATE_DAY_ONLY = re.compile(
    r"\b(antes\s+del?|para\s+el|hasta\s+el|el|del)\s+(?:dia\s+)?(\d{1,2})\b(?!\s*[:h])"
)
_BEFORE_DAY = re.compile(r"\bantes\s+del?\s+(?:el\s+)?(" + "|".join(WEEKDAYS) + r"|manana)\b")
_TIME = re.compile(
    r"\b(?:a\s+las?|sobre\s+las?|para\s+las?)\s+(\d{1,2})(?:[:.](\d{2}))?"
    r"(?:\s*(?:hrs?|h)\b)?(?:\s*(am|pm|a\.\s?m\.|p\.\s?m\.)|\s+(?:de\s+la\s+|en\s+la\s+|por\s+la\s+)"
    r"(manana|tarde|noche|madrugada))?"
)
_NOON = re.compile(r"\b(?:al|a)\s+(mediodia|medianoche)\b")
_RELATIVE = re.compile(
    r"\b(?:en|dentro\s+de)\s+(\d+|media)\s+(minutos?|mins?|horas?|dias?|semanas?)\b"
)
_HALF_HOUR = re.compile(r"\ben\s+media\s+hora\b")


def parse_when(text: str, now: datetime, *, morning_hour: int = 9) -> When:
    """Busca una fecha u hora en `text` (ya con números en cifras). `now` con zona horaria."""
    folded = fold(text)
    when = When()

    relative = _RELATIVE.search(folded) or _HALF_HOUR.search(folded)
    if relative:
        if relative.re is _HALF_HOUR:
            delta = timedelta(minutes=30)
        else:
            amount = 0.5 if relative.group(1) == "media" else int(relative.group(1))
            unit = relative.group(2)
            delta = timedelta(
                minutes=amount if unit.startswith("min") else 0,
                hours=amount if unit.startswith("hora") else 0,
                days=amount
                if unit.startswith("dia")
                else (7 * amount if unit.startswith("seman") else 0),
            )
        when.due = when.remind = (now + delta).replace(second=0, microsecond=0)
        when.spans.append(relative.span())
        return when

    day, before, span = _find_day(folded, now)
    if span:
        when.spans.append(span)
    time_of_day, time_span = _find_time(folded)
    if time_span:
        when.spans.append(time_span)

    if day is None and time_of_day is None:
        return when
    if day is None:  # Solo la hora: hoy, o mañana si ya pasó
        moment = now.replace(hour=time_of_day[0], minute=time_of_day[1], second=0, microsecond=0)
        if moment <= now:
            moment += timedelta(days=1)
        when.due = when.remind = moment
        return when
    if time_of_day is not None:
        moment = day.replace(hour=time_of_day[0], minute=time_of_day[1])
        when.due = when.remind = moment
        return when
    if before:  # «Antes del 15»: vence al empezar el 15; aviso la mañana anterior
        when.due = day
        remind = (day - timedelta(days=1)).replace(hour=morning_hour)
    else:  # «El 15»: vence al final del día; aviso esa mañana
        when.due = day.replace(hour=23, minute=59)
        remind = day.replace(hour=morning_hour)
    if remind <= now < when.due:  # La mañana ya pasó, pero aún hay tiempo: aviso pronto
        remind = (now + min(timedelta(hours=1), (when.due - now) / 2)).replace(microsecond=0)
    when.remind = remind if remind > now else None  # Ya venció: lo recordará el resumen
    return when


def _midnight(now: datetime, date) -> datetime:
    return now.replace(year=date.year, month=date.month, day=date.day, hour=0, minute=0,
                       second=0, microsecond=0)  # fmt: skip


def _find_day(folded: str, now: datetime):
    """(día a medianoche, ¿era «antes de»?, posición) o (None, False, None)."""
    today = _midnight(now, now)
    match = _DATE.search(folded)
    if match:
        prefix, day_number = match.group(1) or "", int(match.group(2))
        month_name, year, month_number, year2 = (
            match.group(3),
            match.group(4),
            match.group(5),
            match.group(6),
        )
        month = MONTHS.index(month_name) + 1 if month_name else int(month_number)
        year = int(year or year2 or now.year)
        year += 2000 if year < 100 else 0
        try:
            day = today.replace(year=year, month=month, day=day_number)
        except ValueError:
            return None, False, None
        if day < today and not (year2 or match.group(4)):
            day = day.replace(year=day.year + 1)
        return day, prefix.startswith("antes"), match.span()
    match = _DATE_DAY_ONLY.search(folded)
    if match and 1 <= int(match.group(2)) <= 31:
        day_number = int(match.group(2))
        candidate = today
        for _ in range(3):  # Este mes o el siguiente con ese día
            try:
                day = candidate.replace(day=day_number)
            except ValueError:
                day = None
            if day is not None and day >= today:
                return day, match.group(1).startswith("antes"), match.span()
            candidate = (candidate.replace(day=1) + timedelta(days=32)).replace(day=1)
        return None, False, None
    match = _BEFORE_DAY.search(folded)
    if match:
        target = match.group(1)
        day = today + timedelta(days=1) if target == "manana" else _next_weekday(today, target)
        return day, True, match.span()
    match = _DAY_WORD.search(folded)
    if match and not re.search(r"(?:de|en|por)\s+la\s+$", folded[: match.start()]):
        word = re.sub(r"\s+", " ", match.group(1))
        offset = {"hoy": 0, "esta noche": 0, "esta tarde": 0, "manana": 1, "pasado manana": 2}[word]
        return today + timedelta(days=offset), False, match.span()
    match = _WEEKDAY.search(folded)
    if match:
        return _next_weekday(today, match.group(1)), False, match.span()
    return None, False, None


def _next_weekday(today: datetime, name: str) -> datetime:
    ahead = (WEEKDAYS.index(name) - today.weekday()) % 7 or 7  # «El lunes» un lunes: el próximo
    return today + timedelta(days=ahead)


def _find_time(folded: str):
    match = _NOON.search(folded)
    if match:
        return ((12, 0) if match.group(1) == "mediodia" else (23, 59)), match.span()
    match = _TIME.search(folded)
    if not match:
        if re.search(r"\besta\s+noche\b", folded):
            return (21, 0), None
        if re.search(r"\besta\s+tarde\b", folded):
            return (17, 0), None
        return None, None
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    suffix = (match.group(3) or "").replace(".", "").replace(" ", "")
    part = match.group(4)
    if hour > 23 or minute > 59:
        return None, None
    if (suffix == "pm" or part in ("tarde", "noche")) and hour < 12:
        hour += 12
    elif (suffix == "am" or part in ("manana", "madrugada")) and hour == 12:
        hour = 0
    elif not suffix and not part and 1 <= hour <= 7:
        hour += 12  # «A las 5» sin más: lo normal es por la tarde
    return (hour, minute), match.span()
