"""Manos de MEKA (T-004): solo carpetas autorizadas, sin escapes y sin tocar lo protegido."""

import asyncio
import sqlite3

import pytest

from core.events import EventBus
from core.hands import Hands, HandsError
from core.runs import RunLog
from tests.test_server import make_client, make_engine


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def tree(tmp_path):
    """Una carpeta autorizada con documentos, secretos y una carpeta de fuera."""
    root = tmp_path / "autorizada"
    (root / "facturas").mkdir(parents=True)
    (root / "facturas" / "enero.txt").write_text("Total: 200 € (IVA incluido)\n", encoding="utf-8")
    (root / "notas.md").write_text("# Ideas\nComprar comida para Toby\n", encoding="utf-8")
    (root / "largo.txt").write_text("x" * 5000, encoding="utf-8")
    (root / "foto.bin").write_bytes(b"\x00\x01\x02binario")
    (root / ".env").write_text("TOKEN=Toby-secreto", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("Toby", encoding="utf-8")
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "node_modules" / "pkg" / "Toby.js").write_text("Toby", encoding="utf-8")
    (root / "privada").mkdir()
    (root / "privada" / "diario.txt").write_text("querido diario", encoding="utf-8")
    outside = tmp_path / "fuera"
    outside.mkdir()
    (outside / "secreto.txt").write_text("Toby fuera de la carpeta", encoding="utf-8")
    return tmp_path


def make_hands(tree, **extra):
    config = {
        "hands": {
            "folders": {
                "docs": str(tree / "autorizada"),
                "diario": {"path": str(tree / "autorizada" / "privada"), "private": True},
            },
            "max_read_chars": 1000,
            **extra,
        }
    }
    bus = EventBus()
    return Hands(config, bus, RunLog(tree / "meka.db")), bus


# ---------------------------------------------------------------------- seguridad


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("../fuera/secreto.txt", 403),  # Escapar con ..
        ("facturas/../../fuera/secreto.txt", 403),
        ("/etc/passwd", 400),  # Rutas absolutas
        ("C:/Windows/win.ini", 400),
        (".env", 403),  # Protegidos aunque estén dentro
        (".git/config", 403),
        ("no-existe.txt", 404),
    ],
)
def test_reads_are_confined(tree, path, status):
    hands, _ = make_hands(tree)
    with pytest.raises(HandsError) as error:
        run(hands.read("docs", path))
    assert error.value.status == status


def test_symlinks_cannot_escape(tree):
    hands, _ = make_hands(tree)
    link = tree / "autorizada" / "atajo"
    try:
        link.symlink_to(tree / "fuera", target_is_directory=True)
    except OSError:
        # Windows sin privilegios: una "junction" de carpeta hace lo mismo y no los pide
        try:
            import _winapi

            _winapi.CreateJunction(str(tree / "fuera"), str(link))
        except (ImportError, OSError):
            pytest.skip("Este sistema no permite crear enlaces sin privilegios")
    with pytest.raises(HandsError):
        run(hands.read("docs", "atajo/secreto.txt"))
    names = [e["name"] for e in run(hands.list("docs"))["entries"]]
    assert "atajo" not in names
    assert run(hands.search("docs", "fuera de la carpeta"))["matches"] == []


def test_unknown_and_private_folders(tree):
    hands, _ = make_hands(tree)
    assert {f["name"] for f in hands.list_folders()} == {"docs", "diario"}
    assert [f["name"] for f in hands.list_folders(include_private=False)] == ["docs"]
    assert run(hands.read("diario", "diario.txt"))["text"] == "querido diario"
    with pytest.raises(HandsError) as error:
        run(hands.read("diario", "diario.txt", include_private=False))  # Como el MCP
    assert error.value.status == 404
    with pytest.raises(HandsError):
        run(hands.list("descargas"))


def test_extra_denied_patterns(tree):
    hands, _ = make_hands(tree, deny=["facturas"])
    with pytest.raises(HandsError):
        run(hands.read("docs", "facturas/enero.txt"))


# ---------------------------------------------------------------------- lectura


def test_list_hides_protected_and_filters(tree):
    hands, _ = make_hands(tree)
    listing = run(hands.list("docs"))
    names = [e["name"] for e in listing["entries"]]
    assert names[:3] == ["facturas", "node_modules", "privada"]  # Carpetas primero
    assert ".env" not in names and ".git" not in names
    assert [e["name"] for e in run(hands.list("docs", pattern="*.md"))["entries"]] == ["notas.md"]


def test_read_text_truncation_and_binary(tree):
    hands, _ = make_hands(tree)
    invoice = run(hands.read("docs", "facturas/enero.txt"))
    assert invoice["text"].startswith("Total: 200 €") and not invoice["truncated"]
    long = run(hands.read("docs", "largo.txt"))
    assert len(long["text"]) == 1000 and long["truncated"]
    with pytest.raises(HandsError) as error:
        run(hands.read("docs", "foto.bin"))
    assert error.value.status == 415


def test_reads_documents(tree):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph("Contrato de alquiler de Toby")
    document.save(tree / "autorizada" / "contrato.docx")
    hands, _ = make_hands(tree)
    assert "alquiler de Toby" in run(hands.read("docs", "contrato.docx"))["text"]


def test_search_by_name_and_content(tree):
    hands, bus = make_hands(tree)
    events = bus.subscribe()
    result = run(hands.search("docs", "toby"))
    paths = {m["path"]: m["line"] for m in result["matches"]}
    # Ni .env, ni .git, ni node_modules, ni la carpeta de fuera
    assert paths == {"notas.md": "Comprar comida para Toby"}
    assert run(hands.search("docs", "enero", content=False))["matches"] == [
        {"path": "facturas/enero.txt", "line": None}
    ]
    types = [events.get_nowait()["type"] for _ in range(events.qsize())]
    assert types[:2] == ["agent.working", "agent.done"]


def test_actions_are_logged_without_paths_or_content(tree):
    hands, _ = make_hands(tree)
    run(hands.read("docs", "notas.md"))
    with pytest.raises(HandsError):
        run(hands.read("docs", ".env"))
    rows = sqlite3.connect(tree / "meka.db").execute("SELECT * FROM runs").fetchall()
    assert [(r[2], r[3], r[4], r[5]) for r in rows] == [
        ("hands.read", "hands", "docs", 1),
        ("hands.read", "hands", "docs", 0),
    ]
    assert "notas" not in str(rows) and "Toby" not in str(rows)


# ---------------------------------------------------------------------- API


def test_api(tree):
    engine = make_engine(tree)
    engine.hands, _ = make_hands(tree)
    with make_client(engine) as client:
        assert [f["name"] for f in client.get("/v1/hands").json()["folders"]] == ["docs", "diario"]
        read = client.get("/v1/hands/docs/read", params={"path": "notas.md"})
        assert read.status_code == 200 and "Toby" in read.json()["text"]
        escape = client.get("/v1/hands/docs/read", params={"path": "../fuera/secreto.txt"})
        assert escape.status_code == 403 and "sale de la carpeta" in escape.json()["detail"]
        private = client.get(
            "/v1/hands/diario/list", params={"include_private": "false"}
        ).status_code
        assert private == 404
        found = client.get("/v1/hands/docs/search", params={"q": "200 €"}).json()
        assert found["matches"][0]["path"] == "facturas/enero.txt"
