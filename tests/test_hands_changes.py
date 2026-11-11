"""Cambios de las manos (T-005): permiso, punto de restauración y deshacer."""

import asyncio
import threading
import time

import pytest

from core.confirmations import ConfirmationRegistry
from core.events import EventBus
from core.hands import Hands, HandsError
from core.hands.restore import RestorePoints
from tests.test_server import make_client, make_engine

pytestmark = pytest.mark.skipif(not RestorePoints(".", ":memory:").git, reason="requiere git")


@pytest.fixture
def setup(tmp_path):
    folder = tmp_path / "ordenar"
    (folder / "docs").mkdir(parents=True)
    (folder / "docs" / "nota.txt").write_bytes(b"version original\r\ncon CRLF\n")
    (folder / "factura.pdf.txt").write_text("factura", encoding="utf-8")
    (folder / "solo-lectura").mkdir()
    (tmp_path / "fuera.txt").write_text("fuera", encoding="utf-8")
    bus = EventBus()
    config = {
        "hands": {
            "folders": {
                "ordenar": {"path": str(folder), "writable": True},
                "leer": str(folder / "solo-lectura"),
            }
        }
    }
    hands = Hands(
        config,
        bus,
        confirmations=ConfirmationRegistry(bus, default_timeout=5),
        restore_points=RestorePoints(tmp_path / "data" / "hands", tmp_path / "meka.db"),
    )
    return hands, folder, tmp_path


def answer(hands, coro, approve: bool | None = True):
    """Ejecuta un cambio mientras el "usuario" responde en la mascota (None = no responde)."""

    async def scenario():
        task = asyncio.create_task(coro)
        for _ in range(500):
            await asyncio.sleep(0.01)
            pending = hands.confirmations.pending()
            if pending or task.done():
                break
        if pending and approve is not None:
            hands.confirmations.resolve(pending[0]["id"], approve, by="pet")
        return await task

    return asyncio.run(scenario())


# ---------------------------------------------------------------------- operaciones y deshacer


def test_write_new_file_and_undo(setup):
    hands, folder, _ = setup
    result = answer(hands, hands.write("ordenar", "notas/nueva.md", "# Hola"))
    assert (folder / "notas" / "nueva.md").read_text(encoding="utf-8") == "# Hola"
    assert result["op"] == "write" and result["paths"] == ["notas/nueva.md"]
    answer(hands, hands.undo("ordenar"))
    assert not (folder / "notas" / "nueva.md").exists()


def test_overwrite_and_undo_is_byte_exact(setup):
    hands, folder, _ = setup
    original = (folder / "docs" / "nota.txt").read_bytes()
    answer(hands, hands.write("ordenar", "docs/nota.txt", "nueva", overwrite=True))
    assert (folder / "docs" / "nota.txt").read_text(encoding="utf-8") == "nueva"
    answer(hands, hands.undo("ordenar"))
    assert (folder / "docs" / "nota.txt").read_bytes() == original  # CRLF incluido


def test_move_delete_mkdir_and_undo(setup):
    hands, folder, _ = setup
    answer(hands, hands.move("ordenar", "factura.pdf.txt", "facturas/enero.txt"))
    assert (
        not (folder / "factura.pdf.txt").exists() and (folder / "facturas" / "enero.txt").exists()
    )
    answer(hands, hands.undo("ordenar"))
    assert (folder / "factura.pdf.txt").read_text(encoding="utf-8") == "factura"
    assert not (folder / "facturas" / "enero.txt").exists()

    answer(hands, hands.delete("ordenar", "docs/nota.txt"))
    assert not (folder / "docs" / "nota.txt").exists()
    answer(hands, hands.undo("ordenar"))
    assert (folder / "docs" / "nota.txt").exists()

    answer(hands, hands.mkdir("ordenar", "archivo/2026"))
    assert (folder / "archivo" / "2026").is_dir()
    answer(hands, hands.undo("ordenar"))
    assert not (folder / "archivo" / "2026").exists()


def test_undo_is_a_stack(setup):
    hands, folder, _ = setup
    answer(hands, hands.write("ordenar", "a.txt", "a"))
    answer(hands, hands.write("ordenar", "b.txt", "b"))
    assert [op["paths"][0] for op in hands.history("ordenar")] == ["b.txt", "a.txt"]
    answer(hands, hands.undo("ordenar"))
    assert not (folder / "b.txt").exists() and (folder / "a.txt").exists()
    answer(hands, hands.undo("ordenar"))
    assert not (folder / "a.txt").exists()
    with pytest.raises(HandsError) as error:
        answer(hands, hands.undo("ordenar"))
    assert error.value.status == 404


def test_user_gitignore_does_not_block_backups(setup):
    hands, folder, _ = setup
    (folder / ".gitignore").write_text("*.txt\n", encoding="utf-8")
    answer(hands, hands.write("ordenar", "docs/nota.txt", "x", overwrite=True))
    answer(hands, hands.undo("ordenar"))
    assert b"version original" in (folder / "docs" / "nota.txt").read_bytes()


def test_shadow_repo_lives_outside_the_folder(setup):
    hands, folder, tmp_path = setup
    answer(hands, hands.write("ordenar", "a.txt", "a"))
    assert not (folder / ".git").exists()
    assert (tmp_path / "data" / "hands" / "ordenar.git").is_dir()


# ---------------------------------------------------------------------- permiso


@pytest.mark.parametrize("approve", [False, None])  # Rechazado o sin respuesta
def test_without_permission_nothing_changes(setup, approve):
    hands, folder, _ = setup
    hands.confirmations.default_timeout = 0.3
    with pytest.raises(HandsError) as error:
        answer(hands, hands.delete("ordenar", "docs/nota.txt"), approve=approve)
    assert error.value.status == 403
    assert (folder / "docs" / "nota.txt").exists()
    assert hands.history("ordenar") == []  # Ni siquiera hay punto de restauración


def test_permission_dialog_and_pet_events(setup):
    hands, _, _ = setup
    events = hands.bus.subscribe()
    answer(hands, hands.move("ordenar", "factura.pdf.txt", "facturas/enero.txt"))
    emitted = [events.get_nowait() for _ in range(events.qsize())]
    confirm = next(e for e in emitted if e["type"] == "agent.confirm")
    assert confirm["data"]["action"] == "Mover factura.pdf.txt → facturas/enero.txt en ordenar"
    assert confirm["data"]["details"] == {
        "folder": "ordenar",
        "op": "move",
        "paths": ["factura.pdf.txt", "facturas/enero.txt"],
    }
    assert [e["type"] for e in emitted][-2:] == ["agent.working", "agent.done"]


# ---------------------------------------------------------------------- límites (sin preguntar)


@pytest.mark.parametrize(
    ("operation", "status"),
    [
        (lambda h: h.write("leer", "a.txt", "x"), 403),  # Carpeta de solo lectura
        (lambda h: h.write("ordenar", ".env", "TOKEN=1"), 403),  # Protegido
        (lambda h: h.write("ordenar", "../fuera.txt", "x", overwrite=True), 403),  # Escape
        (lambda h: h.write("ordenar", "docs/nota.txt", "x"), 409),  # Ya existe
        (lambda h: h.delete("ordenar", "docs"), 400),  # Nunca carpetas enteras
        (lambda h: h.move("ordenar", "docs/nota.txt", "factura.pdf.txt"), 409),  # Sin sobrescribir
        (lambda h: h.write("ordenar", "a.txt", "x" * 300_000), 413),
    ],
)
def test_limits_are_checked_before_asking(setup, operation, status):
    hands, _, tmp_path = setup
    with pytest.raises(HandsError) as error:
        answer(hands, operation(hands))
    assert error.value.status == status
    assert hands.confirmations.pending() == []
    assert (tmp_path / "fuera.txt").read_text(encoding="utf-8") == "fuera"


# ---------------------------------------------------------------------- API


def test_api_change_with_permission_from_another_client(setup):
    hands, folder, _ = setup
    engine = make_engine(setup[2])
    engine.hands = hands
    hands.confirmations = engine.confirmations
    with make_client(engine) as client:
        result = {}

        def agent():
            result["write"] = client.post(
                "/v1/hands/ordenar/write", json={"path": "hola.txt", "content": "hola"}
            )

        thread = threading.Thread(target=agent)
        thread.start()
        for _ in range(200):
            pending = client.get("/v1/confirmations").json()["pending"]
            if pending:
                break
            time.sleep(0.02)
        assert client.post(f"/v1/confirmations/{pending[0]['id']}", json={"approved": True}).json()
        thread.join(timeout=10)
        assert result["write"].status_code == 200
        assert (folder / "hola.txt").read_text(encoding="utf-8") == "hola"
        history = client.get("/v1/hands/ordenar/history").json()["operations"]
        assert history[0]["op"] == "write" and history[0]["undone"] is False
        readonly = client.post("/v1/hands/leer/write", json={"path": "a.txt", "content": "x"})
        assert readonly.status_code == 403 and "solo lectura" in readonly.json()["detail"]
