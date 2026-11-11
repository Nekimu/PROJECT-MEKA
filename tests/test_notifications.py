"""Notificaciones de Windows en la isla (T-046): privacidad, bandeja y acciones."""

import asyncio

import pytest

from core import contract
from core.events import EventBus
from core.system import SystemMonitor
from core.system.notifications import HIDDEN, SAFE_AUMID, allowed, protect
from tests.test_server import make_client, make_engine

# ---------------------------------------------------------------------- privacidad


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Tu código de verificación es 482913", "Tu código de verificación es ••••••"),
        ("Your verification code: G-551204", "Your verification code: ••••••"),
        ("Código 123 456 para entrar", "Código •••••• para entrar"),
        ("Pedido 482913 enviado", "Pedido 482913 enviado"),  # Sin contexto de código: se deja
        ("mi contraseña es Gato.2026", HIDDEN),  # Sensible (ai/privacy.py)
        ("Pago con tarjeta 4111 1111 1111 1111", HIDDEN),
        (None, None),
    ],
)
def test_codes_and_sensitive_text_are_hidden(text, expected):
    assert protect(text, hide_codes=True) == expected


def test_codes_can_be_shown_if_configured():
    assert protect("Tu código es 482913", hide_codes=False) == "Tu código es 482913"


@pytest.mark.parametrize(
    ("apps", "blocked", "app", "result"),
    [
        (["*"], [], "WhatsApp", True),
        (["whatsapp"], [], "WhatsApp", True),  # Sin distinguir mayúsculas
        (["Outlook"], [], "WhatsApp", False),
        (["*"], ["WhatsApp"], "WhatsApp", False),  # Bloquear gana
        (["5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"], [], "WhatsApp", True),  # Por AUMID
    ],
)
def test_allowed_apps(apps, blocked, app, result):
    assert allowed(app, "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App", apps, blocked) is result


def test_safe_app_ids():
    assert SAFE_AUMID.match("Microsoft.ScreenSketch_8wekyb3d8bbwe!App")
    assert not SAFE_AUMID.match('x" & calc.exe & "')
    assert not SAFE_AUMID.match("..\\..\\Windows\\System32\\cmd.exe")


# ---------------------------------------------------------------------- bandeja


class FakeInbox:
    available = True

    def __init__(self, *items):
        self.items = list(items)
        self.dismissed = []
        self.opened = []

    async def snapshot(self):
        return [dict(i) for i in self.items]

    async def dismiss(self, notification_id):
        self.dismissed.append(notification_id)
        self.items = [i for i in self.items if i["id"] != notification_id]
        return True

    async def open(self, aumid):
        self.opened.append(aumid)
        return True


def note(id_, app="WhatsApp", title="Ana", body="¿Vamos por café?", time=100.0):
    return {
        "id": id_,
        "app": app,
        "aumid": f"{app}.App",
        "title": title,
        "body": body,
        "time": time,
    }


def make_inbox(*items, **cfg):
    bus = EventBus()
    events = bus.subscribe()
    source = FakeInbox(*items)
    config = {"system": {"enabled": True, "notifications": {"enabled": True, **cfg}}}
    return (
        SystemMonitor(config, bus, media=None, battery=None, notifications=source),
        source,
        events,
    )


def drain(queue):
    return [queue.get_nowait() for _ in range(queue.qsize())]


def test_first_read_is_silent_then_only_changes():
    monitor, source, events = make_inbox(note(1, time=1.0))
    assert asyncio.run(monitor.refresh_notifications()) == ([], [])  # Las antiguas no se anuncian
    assert drain(events) == []
    assert [n["id"] for n in monitor.notifications()] == [1]

    source.items.append(note(2, body="Tu código de verificación es 482913", time=2.0))
    source.items = [i for i in source.items if i["id"] != 1]
    assert asyncio.run(monitor.refresh_notifications()) == ([2], [1])
    new, removed = drain(events)
    assert new == {
        "type": "system.notification",
        "data": {"id": 2, "app": "WhatsApp", "title": "Ana",
                 "body": "Tu código de verificación es ••••••", "time": 2.0},
    }  # fmt: skip
    assert "aumid" not in new["data"]  # El identificador interno no sale
    assert removed == {"type": "system.notification_removed", "data": {"id": 1}}
    for event in (new, removed):
        assert contract.validate(event["type"], event["data"]) == []


def test_filters_and_limit():
    items = [note(i, app="Outlook" if i % 2 else "WhatsApp", time=float(i)) for i in range(1, 7)]
    monitor, _, _ = make_inbox(*items, apps=["WhatsApp"], max_items=2)
    asyncio.run(monitor.refresh_notifications())
    assert [n["id"] for n in monitor.notifications()] == [6, 4]  # Solo WhatsApp, las 2 más nuevas


def test_actions_only_on_visible_notifications():
    monitor, source, events = make_inbox(note(1), note(2, app="Outlook"), apps=["WhatsApp"])
    asyncio.run(monitor.refresh_notifications())
    assert asyncio.run(monitor.notification_action(1, "open")) is True
    assert source.opened == ["WhatsApp.App"]  # El AUMID sale de la bandeja, nunca del cliente
    assert asyncio.run(monitor.notification_action(2, "dismiss")) is False  # No visible
    assert asyncio.run(monitor.notification_action(99, "dismiss")) is False
    with pytest.raises(ValueError):
        asyncio.run(monitor.notification_action(1, "responder"))

    assert asyncio.run(monitor.notification_action(1, "dismiss")) is True
    assert source.dismissed == [1]
    assert drain(events)[-1] == {"type": "system.notification_removed", "data": {"id": 1}}


# ---------------------------------------------------------------------- API y WebSocket


def test_api_and_websocket(tmp_path):
    engine = make_engine(tmp_path)
    monitor, source, _ = make_inbox(note(7, body="Tu código es 991122"))
    monitor.bus = engine.bus
    engine.system = monitor
    asyncio.run(monitor.refresh_notifications())
    with make_client(engine) as client, client.websocket_connect("/v1/events") as ws:
        listed = client.get("/v1/system/notifications").json()["notifications"]
        assert listed[0]["body"] == "Tu código es ••••••"
        assert client.post("/v1/system/notifications/7", json={"action": "open"}).json() == {
            "done": True
        }
        bad = client.post("/v1/system/notifications/7", json={"action": "responder"})
        assert bad.status_code == 422
        fake = client.post(
            "/v1/events",
            json={"type": "system.notification", "data": {"id": 1, "app": "x", "time": 1.0}},
        )
        assert fake.status_code == 422  # Solo las publica el núcleo
        ws.send_json({"type": "user.notification", "data": {"id": 7, "action": "dismiss"}})
        removed = ws.receive_json()
    assert removed == {"type": "system.notification_removed", "data": {"id": 7}}
    assert source.opened == ["WhatsApp.App"] and source.dismissed == [7]
