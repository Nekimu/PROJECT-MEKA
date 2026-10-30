"""Valida el manifiesto de personajes de la mascota (pet/web/skins/manifest.js)."""

import json
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parent.parent / "pet" / "web"
REQUIRED_LINES = {"greet", "idle", "happy", "working", "thinking", "sleeping", "wake",
                  "eating", "full", "error", "celebrate", "sad", "hungry", "tired", "broke", "chat"}  # fmt: skip


def load_manifest() -> dict:
    source = (WEB / "skins" / "manifest.js").read_text(encoding="utf-8")
    body = source.split("window.MEKA_SKINS =", 1)[1].strip()
    return json.loads(body.removesuffix(";"))


MANIFEST = load_manifest()
SKINS = MANIFEST["skins"]


def test_default_skin_exists_and_is_unlocked():
    assert SKINS[MANIFEST["default"]]["unlockAt"] == 0


@pytest.mark.parametrize("skin_id", SKINS)
def test_every_state_has_existing_sprites(skin_id):
    skin = SKINS[skin_id]
    assert set(skin["states"]) == set(MANIFEST["states"]), "faltan o sobran estados"
    for state, sprite_keys in skin["states"].items():
        assert sprite_keys, f"el estado {state} no tiene sprites"
        for key in sprite_keys:
            assert key in skin["sprites"], f"{state} usa el sprite inexistente {key!r}"
    for path in skin["sprites"].values():
        assert (WEB / path).is_file(), f"no existe {path}"


@pytest.mark.parametrize("skin_id", SKINS)
def test_every_skin_has_all_lines_and_food(skin_id):
    skin = SKINS[skin_id]
    missing = REQUIRED_LINES - set(skin["lines"])
    assert not missing, f"faltan frases: {sorted(missing)}"
    assert all(skin["lines"][kind] for kind in REQUIRED_LINES)
    assert skin["food"]


def test_no_orphan_sprite_files():
    referenced = {path for skin in SKINS.values() for path in skin["sprites"].values()}
    on_disk = {p.relative_to(WEB).as_posix() for p in (WEB / "skins").rglob("*.webp")}
    assert on_disk == referenced
