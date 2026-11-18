"""Guardia de modularidad: ningún módulo del backend crece hasta ser difícil de mantener.

Si este test falla, divide el módulo por responsabilidades (como server/routes/ o ai/tts/)
en lugar de subir el límite.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ("core", "ai", "server", "channels", "scripts")
MAX_LINES = 300


def backend_modules() -> list[Path]:
    files = [ROOT / "run.py"]
    for folder in BACKEND:
        files += sorted((ROOT / folder).rglob("*.py"))
    return files


@pytest.mark.parametrize("path", backend_modules(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_modulo_no_supera_el_limite(path):
    lines = len(path.read_text(encoding="utf-8").splitlines())
    assert lines <= MAX_LINES, f"{path.name} tiene {lines} líneas (máximo {MAX_LINES}): divídelo"
