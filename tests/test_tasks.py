"""Agenda (T-056): fechas en español, órdenes en el chat, almacén, API, WebSocket y MCP."""

import asyncio
import time
from datetime import datetime
from types import SimpleNamespace

import pytest

from core import contract
from core.events import EventBus
from core.tasks import TaskService, TaskStore, describe_when
from core.tasks.intents import best_match, understand
from core.tasks.when import numbers_as_digits, parse_when
from tests.fakes import FakeProvider
from tests.test_server import PERSONA, make_client, make_engine

NOW = datetime(2026, 11, 14, 19, 40).astimezone()  # Sábado por la tarde


def when(text):
    return parse_when(numbers_as_digits(text), NOW)


def at(result):
    return result.due.strftime("%d/%m %H:%M") if result.due else None


# ---------------------------------------------------------------------- fechas


@pytest.mark.parametrize(
    ("text", "due", "remind"),
    [
        ("mañana a las 5 de la tarde", "15/11 17:00", "15/11 17:00"),
        ("en 2 horas", "14/11 21:40", "14/11 21:40"),
        ("en media hora", "14/11 20:10", "14/11 20:10"),
        ("el viernes", "20/11 23:59", "20/11 09:00"),  # Todo el día: aviso por la mañana
        ("el 3 de diciembre a las 10:30", "03/12 10:30", "03/12 10:30"),
        ("a las 9", "15/11 09:00", "15/11 09:00"),  # Ya pasaron las 9: mañana
        ("a la una de la tarde", "15/11 13:00", "15/11 13:00"),
        ("esta noche", "14/11 21:00", "14/11 21:00"),
        ("antes del viernes", "20/11 00:00", "19/11 09:00"),  # Aviso la mañana anterior
        ("el dos de enero", "02/01 23:59", "02/01 09:00"),  # Ya pasó este año: el siguiente
    ],
)
def test_spanish_dates(text, due, remind):
    result = when(text)
    assert at(result) == due
    assert result.remind.strftime("%d/%m %H:%M") == remind


def test_deadline_tomorrow_reminds_soon_when_the_morning_already_passed():
    result = when("antes del quince de noviembre")  # Hoy es 14 y ya son las 19:40
    assert at(result) == "15/11 00:00"
    assert result.remind.strftime("%H:%M") == "20:40"  # En una hora, no «nunca»


def test_no_date_and_numbers_left_alone():
    assert not when("regar las plantas").found
    assert numbers_as_digits("paga una factura el quince") == "paga una factura el 15"


# ---------------------------------------------------------------------- órdenes


def test_the_real_voice_note():
    said = ("Hola MEKA, recuérdame pagar la factura de la luz antes del quince de noviembre "
            "y dime qué tareas me quedan pendientes para hoy.")  # fmt: skip
    request = understand(said, NOW)
    assert [(title, at(w)) for title, w in request.add] == [
        ("pagar la factura de la luz", "15/11 00:00")
    ]
    assert request.show
    # faster-whisper a veces lo separa
    assert understand("recuerda me pagar la luz", NOW).add[0][0] == "pagar la luz"


@pytest.mark.parametrize(
    ("text", "titles"),
    [
        ("Apunta comprar pan y recuérdame llamar a mamá mañana a las 5", ["comprar pan", "llamar a mamá"]),
        ("ponme un recordatorio para revisar el correo en 2 horas", ["revisar el correo"]),
        ("no me dejes olvidar sacar la basura esta noche", ["sacar la basura"]),
        ("recuerda esto: mi perro se llama Toby", []),  # Es un recuerdo, no una tarea
        ("hola, ¿cómo estás?", []),
    ],
)  # fmt: skip
def test_adding_tasks(text, titles):
    assert [title for title, _ in understand(text, NOW).add] == titles


def test_listing_and_completing():
    assert understand("¿Qué tengo hoy?", NOW).show
    assert understand("mis pendientes", NOW).show
    assert understand("ya pagué la luz", NOW).done.split() == ["pagar", "la", "luz"]
    assert understand("marca comprar pan como hecha", NOW).done == "comprar pan"
    titles = {1: "pagar la factura de la luz", 2: "comprar pan", 3: "pagar el agua"}
    assert best_match("pagar la luz", titles) == 1
    assert best_match("pagar", {1: "pagar la luz", 3: "pagar el agua"}) is None  # Empate


def test_describe_when():
    assert describe_when(datetime(2026, 11, 15).astimezone().timestamp(), NOW, deadline=True) == (
        "antes de mañana"
    )
    assert describe_when(datetime(2026, 11, 14, 21).astimezone().timestamp(), NOW) == (
        "hoy a las 21:00"
    )
    assert describe_when(datetime(2026, 11, 20, 23, 59).astimezone().timestamp(), NOW) == (
        "vie 20 nov"
    )


# ---------------------------------------------------------------------- almacén


def test_store(tmp_path):
    store = TaskStore(tmp_path / "meka.db")
    later = store.add("u", "sin fecha")
    soon = store.add("u", "  con   fecha ", due_at=100.0, remind_at=50.0)
    store.add("u", "secreta", private=True)
    store.add("otra", "ajena")
    assert soon.title == "con fecha"
    assert [t.title for t in store.list("u")] == ["con fecha", "sin fecha", "secreta"]
    assert [t.title for t in store.list("u", include_private=False)] == ["con fecha", "sin fecha"]
    assert [t.id for t in store.due_reminders(now=60)] == [soon.id]
    store.mark_reminded(soon.id)
    assert store.due_reminders(now=60) == []  # No avisa dos veces
    store.snooze(soon.id, 70.0)
    assert [t.id for t in store.due_reminders(now=80)] == [soon.id]  # Pospuesta: vuelve
    store.set_status(later.id, "done")
    assert store.get(later.id).done_at is not None
    assert [t.title for t in store.list("u", status="done")] == ["sin fecha"]
    with pytest.raises(ValueError):
        store.add("u", "   ")


# ---------------------------------------------------------------------- en el chat


def test_chat_adds_the_task_and_the_brain_gets_the_real_agenda(tmp_path):
    engine = make_engine(tmp_path)
    brain = FakeProvider("ollama", "¡Claro! Cuenta conmigo.", local=True)
    engine.ai.providers["ollama"] = brain
    replies = asyncio.run(
        engine.chat("s", "u", "recuérdame pagar la luz el viernes y dime mis pendientes")
    )
    texts = [r.text for r in replies]
    assert "pagar la luz" in texts[0] and "(vie" in texts[0]  # La fecha no se pierde
    assert "pagar la luz" in texts[1]  # La lista real
    assert texts[2] == "¡Claro! Cuenta conmigo."
    assert "[Agenda]" in brain.calls[0]["system"] and "no inventes" in brain.calls[0]["system"]
    assert [t.title for t in engine.tasks.store.list("u")] == ["pagar la luz"]

    brain.replies.append("¡Bien hecho!")
    replies = asyncio.run(engine.chat("s", "u", "ya pagué la luz"))
    assert "pagar la luz" in replies[0].text and engine.tasks.store.list("u") == []


def test_private_tasks_never_reach_a_cloud_brain(tmp_path):
    engine = make_engine(tmp_path)
    engine.tasks.add("u", "renovar el pasaporte", private=True)
    agenda = engine.tasks.handle("u", "mis pendientes", private=False, local=False)
    assert "pasaporte" not in agenda.context and "pasaporte" not in agenda.replies[0]
    agenda = engine.tasks.handle("u", "mis pendientes", private=False, local=True)
    assert "pasaporte" in agenda.context


def test_default_lines_for_personas_without_agenda_phrases(tmp_path):
    bare = SimpleNamespace(lines={})  # Un personaje sin frases de agenda
    service = TaskService({}, TaskStore(tmp_path / "t.db"), EventBus(), bare)
    assert service.line("task_list_empty").startswith("No tienes nada pendiente")
    assert PERSONA.line("task_done", title="x")  # El personaje por defecto trae las suyas


# ---------------------------------------------------------------------- API y WebSocket


def test_api_and_websocket(tmp_path):
    engine = make_engine(tmp_path)
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        created = client.post(
            "/v1/users/u/tasks", json={"title": "llamar al banco", "when": "mañana a las 10"}
        )
        assert created.status_code == 200 and created.json()["due_at"] > time.time()
        assert ws.receive_json()["type"] == "task.changed"
        bad = client.post("/v1/users/u/tasks", json={"title": "x", "when": "cuando pueda"})
        assert bad.status_code == 422
        listed = client.get("/v1/users/u/tasks").json()["tasks"]
        assert [t["title"] for t in listed] == ["llamar al banco"] and "user_id" not in listed[0]
        task_id = listed[0]["id"]
        assert (
            client.post(f"/v1/users/otro/tasks/{task_id}", json={"action": "done"}).status_code
            == 404
        )
        snoozed = client.post(
            f"/v1/users/u/tasks/{task_id}", json={"action": "snooze", "minutes": 30}
        )
        assert snoozed.json()["task"]["remind_at"] > time.time() + 29 * 60
        ws.receive_json()
        ws.send_json({"type": "user.task", "data": {"id": task_id, "action": "done"}})
        changed = ws.receive_json()
        assert changed == {
            "type": "task.changed",
            "data": {"id": task_id, "status": "done", "action": "done"},
        }
        assert client.get("/v1/users/u/tasks").json()["tasks"] == []
        assert len(client.get("/v1/users/u/tasks?status=all").json()["tasks"]) == 1
        fake = client.post(
            "/v1/events",
            json={"type": "reminder.due", "data": {"id": 1, "title": "x", "text": "x"}},
        )
        assert fake.status_code == 422  # Solo los publica el núcleo


def test_agenda_events_follow_the_contract(tmp_path):
    engine = make_engine(tmp_path)
    events = engine.bus.subscribe()
    task = engine.tasks.add("u", "x", due_at=time.time() + 60)
    engine.tasks.remind(task)
    for _ in range(events.qsize()):
        message = events.get_nowait()
        assert contract.validate(message["type"], message["data"]) == []


def test_me_is_the_owner(tmp_path):
    engine = make_engine(tmp_path)
    with make_client(engine) as client:
        client.app.state.local_user = "12345"  # Con ALLOWED_USER_IDS, el dueño es tu ID
        client.post("/v1/users/12345/tasks", json={"title": "desde Telegram"})
        for alias in ("me", "local"):  # La mascota no conoce el ID
            titles = [t["title"] for t in client.get(f"/v1/users/{alias}/tasks").json()["tasks"]]
            assert titles == ["desde Telegram"]
        task_id = client.post("/v1/users/me/tasks", json={"title": "desde la isla"}).json()["id"]
        assert (
            client.post(f"/v1/users/me/tasks/{task_id}", json={"action": "done"}).status_code == 200
        )
        assert engine.tasks.store.get(task_id).user_id == "12345"
