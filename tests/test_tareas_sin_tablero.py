"""Sin tablero local (clon nuevo, CI): los hooks no bloquean nada."""

from scripts import tareas

datos = tareas.datos


def test_hooks_do_nothing_without_a_board(tmp_path, monkeypatch):
    """En un clon sin coordinacion/, los hooks no deben rechazar commits ni herramientas."""
    monkeypatch.setattr(datos, "RUTAS", datos.Rutas(tmp_path))
    msg = tmp_path / "MSG"
    msg.write_text("feat: algo", encoding="utf-8")
    assert tareas.main(["check-commit", str(msg)]) == 0
    assert tareas.main(["sync"]) == 0
    assert tareas.main(["lista"]) == 1  # Pedir datos sin tablero sí es un error (con mensaje)
