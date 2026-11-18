"""Avisos de Hanna en Telegram (T-058): qué llega al móvil, cuándo, y los botones."""

import asyncio
from types import SimpleNamespace

import pytest

from channels.client import CoreClient, CoreRequestError
from channels.telegram.alerts import task_button, tasks_command, to_phone
from core.events import EventBus
from core.tasks import TaskService, TaskStore
from core.tasks.proactive import Proactive
from tests.test_proactive import MORNING
from tests.test_server import PERSONA


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------- qué sale del equipo


@pytest.mark.parametrize(
    ("message", "sent"),
    [
        ({"type": "reminder.due", "data": {"id": 1, "title": "x", "text": "⏰ x", "remote": True}}, "⏰ x"),
        ({"type": "reminder.due", "data": {"id": 1, "title": "x", "text": "⏰ x", "remote": False}}, None),
        ({"type": "reminder.due", "data": {"id": 1, "title": "x", "text": "⏰ x", "remote": True, "private": True}}, None),
        ({"type": "nudge", "data": {"text": "con notificaciones", "remote": True, "shareable": "solo tareas"}}, "solo tareas"),
        ({"type": "nudge", "data": {"text": "solo notificaciones", "remote": True}}, None),
        ({"type": "system.notification", "data": {"id": 1, "app": "WhatsApp", "remote": True}}, None),
        ({"type": "message", "data": {"text": "hola"}}, None),
    ],
)  # fmt: skip
def test_only_what_may_leave_the_computer(message, sent):
    alert = to_phone(message)
    assert (alert[0] if alert else None) == sent
    if message["type"] == "reminder.due" and alert:
        buttons = [b.callback_data for b in alert[1].inline_keyboard[0]]
        assert buttons == ["task:done:1", "task:s10:1", "task:s60:1"]


def proactive(tmp_path, *, at_desk=True, idle=None, **cfg):
    bus = EventBus()
    events = bus.subscribe()
    tasks = TaskService({}, TaskStore(tmp_path / "meka.db"), bus, PERSONA)
    config = {"proactive": {"enabled": True, "startup_minutes": 0, **cfg}}
    watcher = Proactive(config, tasks, bus, user="u", at_desk=lambda: at_desk, idle=lambda: idle)
    watcher.started_at = MORNING - 3600
    return watcher, tasks, events


@pytest.mark.parametrize(
    ("at_desk", "idle", "mode", "remote"),
    [
        (True, 30, "away", False),  # Estás al equipo: solo la isla
        (True, 900, "away", True),  # 15 min sin tocar nada: también al móvil
        (False, 0, "away", True),  # La isla está cerrada
        (True, None, "away", False),  # Sin datos de inactividad (no es Windows)
        (True, 0, "always", True),
        (False, 9999, "never", False),
    ],
)
def test_phone_only_when_you_are_away(tmp_path, at_desk, idle, mode, remote):
    watcher, _, _ = proactive(tmp_path, at_desk=at_desk, idle=idle, remote=mode)
    assert watcher.remote() is remote


def test_private_tasks_and_notifications_stay_home(tmp_path):
    inbox = SimpleNamespace(notifications=lambda: [
        {"id": 9, "app": "WhatsApp", "title": "Ana", "body": "x", "time": MORNING - 60}
    ])  # fmt: skip
    watcher, tasks, events = proactive(tmp_path, at_desk=False)
    watcher.system = inbox
    public = tasks.add("u", "pagar la luz", due_at=MORNING + 600, remind_at=MORNING - 60)
    secret = tasks.add(
        "u", "cita médica", due_at=MORNING + 900, remind_at=MORNING - 60, private=True
    )
    # Para el resumen: pendientes de hoy cuyo aviso fue hace rato
    tasks.store.add("u", "regar las plantas", due_at=MORNING + 1800)
    tasks.store.add("u", "renovar el pasaporte", due_at=MORNING + 1800, private=True)
    watcher.tick(MORNING)
    sent = [m for m in (events.get_nowait() for _ in range(events.qsize()))]
    reminders = {m["data"]["id"]: m["data"] for m in sent if m["type"] == "reminder.due"}
    assert reminders[public.id]["remote"] is True
    assert reminders[secret.id]["remote"] is False and reminders[secret.id]["private"] is True
    nudge = next(m["data"] for m in sent if m["type"] == "nudge")
    assert "pasaporte" in nudge["text"] and "WhatsApp" in nudge["text"]  # En la isla, todo
    assert "pagar la luz" not in nudge["text"]  # Se acaba de avisar: no se repite
    assert nudge["remote"] is True
    assert "regar las plantas" in nudge["shareable"]
    assert "pasaporte" not in nudge["shareable"] and "WhatsApp" not in nudge["shareable"]


def test_events_url_carries_the_token():
    assert CoreClient("http://127.0.0.1:8765").events_url() == "ws://127.0.0.1:8765/v1/events"
    secure = CoreClient("https://mi-pc.tail.ts.net", "a b").events_url()
    assert secure == "wss://mi-pc.tail.ts.net/v1/events?token=a%20b"


# ---------------------------------------------------------------------- botones y /tareas


class FakeCore:
    def __init__(self, error=None):
        self.actions, self.error = [], error

    async def task_action(self, user, task_id, action, **extra):
        if self.error:
            raise self.error
        self.actions.append((user, task_id, action, extra))
        return {"done": True}

    async def tasks(self, user, *, include_private=True):
        self.asked_private = include_private
        return [{"id": 1, "title": "pagar la luz"}]


def button(data, core, user_id=20, allowed=(20,)):
    answers, edits = [], []

    async def answer(text=None):
        answers.append(text)

    async def edit(text):
        edits.append(text)

    query = SimpleNamespace(data=data, answer=answer, edit_message_text=edit,
                            message=SimpleNamespace(text="⏰ pagar la luz"))  # fmt: skip
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=user_id))
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"core": core, "allowed_ids": set(allowed)})
    )
    run(task_button(update, context))
    return answers, edits


def test_buttons():
    core = FakeCore()
    answers, edits = button("task:done:7", core)
    assert core.actions == [("20", 7, "done", {})] and answers == ["✅ ¡Hecha!"]
    assert edits == ["⏰ pagar la luz\n\n✅ ¡Hecha!"]
    button("task:s10:7", core)
    assert core.actions[-1] == ("20", 7, "snooze", {"minutes": 10})
    assert button("task:zzz:7", FakeCore())[0] == ["Botón no válido"]
    assert button("task:done:7", FakeCore(CoreRequestError("x")))[0] == ["Esa tarea ya no existe"]
    stranger = FakeCore()
    assert button("task:done:7", stranger, user_id=99)[0] == ["No autorizado"]
    assert stranger.actions == []


def test_tasks_command_never_shows_private_ones():
    core, sent = FakeCore(), []

    async def reply_text(text):
        sent.append(text)

    update = SimpleNamespace(effective_user=SimpleNamespace(id=20),
                             effective_message=SimpleNamespace(reply_text=reply_text))  # fmt: skip
    run(
        tasks_command(update, SimpleNamespace(application=SimpleNamespace(bot_data={"core": core})))
    )
    assert core.asked_private is False and sent == ["Tus pendientes:\n• pagar la luz"]


def test_harmless_windows_disconnects_are_silenced():
    import run

    logged = []
    loop = SimpleNamespace(default_exception_handler=logged.append)
    run._quiet_disconnects(loop, {"exception": ConnectionResetError(10054, "reset")})
    assert logged == []
    run._quiet_disconnects(loop, {"exception": ValueError("de verdad")})
    assert len(logged) == 1  # Los demás errores se siguen viendo


# ---------------------------------------------------------------------- casos límite (revisión)


def test_a_telegram_error_does_not_stop_the_listener():
    from telegram.error import NetworkError

    from channels.telegram.alerts import _send

    class Bot:
        def __init__(self):
            self.calls = 0

        async def send_message(self, chat_id, text, reply_markup=None):
            self.calls += 1
            raise NetworkError("sin red")

    bot = Bot()
    run(_send(bot, 1, "⏰ x", None))  # No lanza: el bucle de avisos sigue vivo
    assert bot.calls == 1


def test_only_the_owners_reminders_go_to_the_phone(tmp_path):
    watcher, tasks, events = proactive(tmp_path, at_desk=False)
    mine = tasks.store.add("u", "lo mío", due_at=MORNING + 600, remind_at=MORNING - 60)
    other = tasks.store.add(
        "otra", "lo de otra persona", due_at=MORNING + 600, remind_at=MORNING - 60
    )
    watcher.tick(MORNING)
    sent = [events.get_nowait() for _ in range(events.qsize())]
    remote = {m["data"]["id"]: m["data"]["remote"] for m in sent if m["type"] == "reminder.due"}
    assert remote == {mine.id: True, other.id: False}


def test_telegram_restarts_after_a_failure(monkeypatch):
    from channels.telegram import app

    attempts = []

    async def failing(*args):
        attempts.append(1)
        if len(attempts) < 3:
            raise RuntimeError("Telegram no responde")
        raise asyncio.CancelledError

    monkeypatch.setattr(app, "_serve_telegram", failing)
    config = {"telegram": {"token": "123456:" + "A" * 35}}
    with pytest.raises(asyncio.CancelledError):
        run(app.run_telegram(config, retry=0.01))
    assert len(attempts) == 3
