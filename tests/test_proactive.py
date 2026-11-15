"""Hanna proactiva (T-056): avisa a su hora y resume sin estorbar."""

import asyncio
import time
from datetime import datetime
from types import SimpleNamespace

import pytest

from core import contract
from core.events import EventBus
from core.tasks import TaskService, TaskStore
from core.tasks.proactive import Proactive
from tests.test_server import PERSONA, make_client, make_engine

# Martes 17 de noviembre de 2026, 11:00 (fuera de las horas de silencio)
MORNING = datetime(2026, 11, 17, 11, 0).astimezone().timestamp()


class Inbox:
    def __init__(self, *items):
        self.items = list(items)

    def notifications(self):
        return self.items


def setup(tmp_path, *, focus=False, busy=False, last_activity=0.0, inbox=None, **cfg):
    bus = EventBus()
    events = bus.subscribe()
    tasks = TaskService({}, TaskStore(tmp_path / "meka.db"), bus, PERSONA)
    config = {"proactive": {"enabled": True, "startup_minutes": 0, **cfg}}
    proactive = Proactive(
        config,
        tasks,
        bus,
        user="u",
        focus=SimpleNamespace(active=focus),
        system=inbox,
        busy=lambda: busy,
        last_activity=lambda: last_activity,
    )
    proactive.started_at = MORNING - 3600
    return proactive, tasks, events


def drain(queue):
    return [queue.get_nowait() for _ in range(queue.qsize())]


def types(queue):
    return [m["type"] for m in drain(queue)]


def nudges(queue):
    return [m for m in drain(queue) if m["type"] == "nudge"]  # Sin los avisos de cada tarea


# ---------------------------------------------------------------------- avisos que pediste


def test_reminders_arrive_on_time_once(tmp_path):
    proactive, tasks, events = setup(tmp_path, focus=True)  # Incluso concentrado: lo pediste tú
    task = tasks.add("u", "pagar la luz", due_at=MORNING + 600, remind_at=MORNING - 60)
    drain(events)
    assert proactive.tick(MORNING)["reminded"] == 1
    reminder = drain(events)[0]
    assert reminder["type"] == "reminder.due" and reminder["data"]["id"] == task.id
    assert "pagar la luz" in reminder["data"]["text"]
    assert contract.validate("reminder.due", reminder["data"]) == []
    assert proactive.tick(MORNING + 60)["reminded"] == 0  # No repite
    tasks.complete(task.id)
    tasks.store.snooze(task.id, MORNING)
    assert proactive.tick(MORNING + 120)["reminded"] == 0  # Hecha: no avisa


# ---------------------------------------------------------------------- el resumen


def test_digest_with_overdue_and_today(tmp_path):
    proactive, tasks, events = setup(tmp_path)
    tasks.add("u", "entregar el informe", due_at=MORNING - 3600)  # Vencida
    tasks.add("u", "llamar al banco", due_at=MORNING + 3600)  # Hoy
    tasks.add("u", "algún día", due_at=None)
    tasks.add("u", "la semana que viene", due_at=MORNING + 6 * 86400)
    drain(events)
    nudge = proactive.tick(MORNING)["nudge"]
    assert nudge["tasks"] == 2 and nudge["overdue"] == 1 and nudge["kind"] == "tasks"
    assert "entregar el informe" in nudge["text"] and "llamar al banco" in nudge["text"]
    assert "algún día" not in nudge["text"] and "semana" not in nudge["text"]
    published = nudges(events)
    assert len(published) == 1 and contract.validate("nudge", published[0]["data"]) == []


def test_nothing_to_say_means_silence(tmp_path):
    proactive, tasks, events = setup(tmp_path)
    tasks.add("u", "sin prisa", due_at=None)
    assert proactive.tick(MORNING)["nudge"] is None and nudges(events) == []


@pytest.mark.parametrize(
    ("kwargs", "now", "reason"),
    [
        ({"focus": True}, MORNING, "modo concentración"),
        ({"busy": True}, MORNING, "ocupada"),
        ({"last_activity": MORNING - 60}, MORNING, "conversación en curso"),
        ({}, datetime(2026, 11, 17, 23, 30).astimezone().timestamp(), "horas de silencio"),
        ({}, datetime(2026, 11, 17, 7, 0).astimezone().timestamp(), "horas de silencio"),
    ],
)
def test_never_interrupts(tmp_path, kwargs, now, reason):
    proactive, tasks, events = setup(tmp_path, **kwargs)
    proactive.started_at = now - 3600
    tasks.add("u", "vencida", due_at=MORNING - 3600)
    result = proactive.tick(now)
    assert result["nudge"] is None and result["skipped"] == reason
    assert nudges(events) == []


def test_frequency_repetition_and_daily_limit(tmp_path):
    proactive, tasks, _ = setup(tmp_path, digest_minutes=60, repeat_hours=4, max_per_day=2)
    tasks.add("u", "vencida", due_at=MORNING - 3600)
    assert proactive.tick(MORNING)["nudge"] is not None
    assert proactive.tick(MORNING + 1800)["skipped"] == "resumen reciente"
    assert proactive.tick(MORNING + 3700)["nudge"] is None  # Lo mismo de antes: no lo repite
    tasks.add("u", "otra vencida", due_at=MORNING - 60)
    assert proactive.tick(MORNING + 3800)["nudge"] is not None  # Algo nuevo: sí
    tasks.add("u", "tercera", due_at=MORNING - 30)
    assert proactive.tick(MORNING + 7600)["skipped"] == "límite diario"


def test_waits_a_little_after_starting(tmp_path):
    proactive, tasks, _ = setup(tmp_path, startup_minutes=2)
    proactive.started_at = MORNING - 30
    tasks.add("u", "vencida", due_at=MORNING - 3600)
    assert proactive.tick(MORNING)["skipped"] == "acaba de arrancar"


def test_notifications_only_as_a_count(tmp_path):
    inbox = Inbox(
        {"id": 1, "app": "WhatsApp", "title": "Ana", "body": "secreto", "time": MORNING - 60},
        {"id": 2, "app": "Outlook", "title": "Factura", "body": "x", "time": MORNING - 30},
        {"id": 3, "app": "Antigua", "title": "vieja", "body": "x", "time": MORNING - 7200},
    )
    proactive, _, _ = setup(tmp_path, inbox=inbox)
    nudge = proactive.tick(MORNING)["nudge"]
    assert nudge["notifications"] == 2 and nudge["kind"] == "notifications"
    assert "WhatsApp" in nudge["text"] and "Outlook" in nudge["text"]
    assert "secreto" not in nudge["text"] and "Ana" not in nudge["text"]  # Nunca el contenido
    assert "Antigua" not in nudge["text"]  # Llegó antes de arrancar


def test_asking_for_it_skips_the_waiting(tmp_path):
    proactive, tasks, _ = setup(tmp_path, focus=True)
    tasks.add("u", "vencida", due_at=time.time() - 60)
    assert proactive.nudge(force=True)["overdue"] == 1
    assert proactive.nudge(force=True) is not None  # Aunque sea lo mismo: lo pidió


# ---------------------------------------------------------------------- en el servidor


def test_api_status_and_check(tmp_path):
    engine = make_engine(tmp_path)
    engine.tasks.add("u", "vencida", due_at=time.time() - 60)
    engine.proactive.user = "u"
    with make_client(engine) as client:
        status = client.get("/v1/proactive").json()
        assert status["enabled"] is False  # Los tests no vigilan con el reloj real
        nudge = client.post("/v1/proactive/check").json()["nudge"]
        assert nudge["overdue"] == 1


def test_focus_holds_the_digest_but_not_your_reminders(tmp_path):
    engine = make_engine(tmp_path)
    events = engine.bus.subscribe()

    async def scenario():
        await engine.focus.start(25)
        task = engine.tasks.add("u", "pastilla", due_at=time.time() + 60)
        engine.tasks.remind(task)
        engine.bus.publish("nudge", text="x", kind="tasks", tasks=1, overdue=0, notifications=0)
        engine.focus.stop("user")

    asyncio.run(scenario())
    sent = types(events)
    assert "reminder.due" in sent and "task.changed" in sent
    assert sent.index("focus.ended") > sent.index("reminder.due") and "nudge" not in sent
