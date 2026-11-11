"""Tests del tablero compartido de tareas (scripts/tareas.py y scripts/tablero/)."""

import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import tareas

datos, gitsync, hooks = tareas.datos, tareas.gitsync, tareas.hooks

REAL_DATA = Path(__file__).resolve().parent.parent / "coordinacion" / "tareas.json"


@pytest.fixture
def board(tmp_path, monkeypatch):
    """Copia el tablero real a un repositorio git temporal."""
    (tmp_path / "coordinacion").mkdir()
    shutil.copy(REAL_DATA, tmp_path / "coordinacion" / "tareas.json")
    monkeypatch.setattr(datos, "RUTAS", datos.Rutas(tmp_path))
    for args in (["init", "-q"], ["config", "user.name", "t"], ["config", "user.email", "t@t"]):
        subprocess.run(["git", *args], cwd=tmp_path, check=True)
    return tmp_path


def commit(repo: Path, path: str, message: str):
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(message, encoding="utf-8")
    subprocess.run(["git", "add", path], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)


def test_el_tablero_real_es_valido():
    db = json.loads(REAL_DATA.read_text(encoding="utf-8"))
    ids = [t["id"] for t in db["tareas"]]
    assert len(ids) == len(set(ids))
    for t in db["tareas"]:
        assert t["responsable"] in db["agentes"]
        assert t["estado"] in datos.ESTADOS
        assert t["prioridad"] in datos.PRIORIDADES
        assert set(t["depende_de"]) <= set(ids)


@pytest.mark.parametrize(
    ("ruta", "dueño"),
    [
        ("pet/web/pet.js", "antigravity"),
        ("pet/src-tauri/tauri.conf.json", "antigravity"),
        ("tests/test_pet_skins.py", "antigravity"),  # Excepción dentro de tests/**
        ("tests/test_server.py", "claude"),
        ("server/app.py", "claude"),
        ("config.yml", "claude"),
        ("README.md", "compartido"),
        ("coordinacion/tareas.json", "compartido"),
    ],
)
def test_propietario(ruta, dueño):
    db = json.loads(REAL_DATA.read_text(encoding="utf-8"))
    assert datos.owner(db, ruta) == dueño


def test_hook_bloquea_archivos_del_otro_agente(board, monkeypatch, capsys):
    db = datos.load()
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"tool_input": {"file_path": "pet/web/pet.js"}}))
    )
    hooks.pretooluse(db, "claude")
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"tool_input": {"file_path": "core/engine.py"}}))
    )
    hooks.pretooluse(db, "claude")
    assert capsys.readouterr().out == ""


def test_sync_actualiza_estados_desde_los_commits(board):
    # Estado inicial fijo: el test no puede depender del tablero real
    db = datos.load()
    for task_id in ("T-003", "T-004"):
        datos.find(db, task_id).update(estado="pendiente", commits=[])
    datos.save(db)
    commit(board, "core/a.py", "feat: empiezo la confirmación (T-003)")
    commit(board, "core/b.py", "feat: manos de solo lectura, cierra T-004")
    db = datos.load()
    cambios = gitsync.sync(db)
    assert sorted(cambios) == ["T-003 -> en_progreso", "T-004 -> hecha"]
    assert len(datos.find(db, "T-003")["commits"]) == 1
    assert gitsync.sync(db) == []  # Idempotente


def test_commit_que_mezcla_areas_se_rechaza(board, capsys):
    db = datos.load()
    for path in ("pet/web/pet.js", "server/app.py"):
        (board / path).parent.mkdir(parents=True, exist_ok=True)
        (board / path).write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=board, check=True)
    msg = board / "MSG"
    msg.write_text("cambios (T-003)", encoding="utf-8")
    assert gitsync.check_commit(db, str(msg)) == 1

    subprocess.run(["git", "reset", "-q", "pet/web/pet.js"], cwd=board, check=True)
    assert gitsync.check_commit(db, str(msg)) == 0


def test_cli_nueva_y_estado(board, capsys):
    assert (
        tareas.main(
            [
                "nueva",
                "--agente",
                "antigravity",
                "--titulo",
                "Menú",
                "--archivos",
                "pet/web/pet.css",
            ]
        )
        == 0
    )
    db = datos.load()
    nueva = db["tareas"][-1]
    assert nueva["responsable"] == "antigravity" and nueva["estado"] == "pendiente"
    tareas.main(
        ["estado", nueva["id"], "en_revision", "--agente", "antigravity", "--nota", "listo"]
    )
    assert datos.find(datos.load(), nueva["id"])["estado"] == "en_revision"
    assert "Menú" in (board / "coordinacion" / "TABLERO.md").read_text(encoding="utf-8")

    with pytest.raises(SystemExit):  # Archivos de otra área
        tareas.main(
            ["nueva", "--agente", "claude", "--titulo", "x", "--archivos", "pet/web/pet.js"]
        )
