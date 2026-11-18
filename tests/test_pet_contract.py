"""La isla (pet/web/pet.js) y el núcleo hablan el mismo contrato.

Solo lee el JavaScript de la isla (no lo ejecuta ni lo cambia). Si falla al juntar el trabajo
del frontend, la isla usa una ruta o un evento que el núcleo no tiene, o al revés.
"""

import re
from pathlib import Path

import pytest

from core import contract
from tests.test_server import make_client, make_engine

PET = Path(__file__).resolve().parent.parent / "pet" / "web" / "pet.js"
pytestmark = pytest.mark.skipif(not PET.exists(), reason="sin la isla (pet/web/pet.js)")


def source() -> str:
    return PET.read_text(encoding="utf-8")


def rest_patterns(tmp_path) -> list[re.Pattern]:
    with make_client(make_engine(tmp_path)) as client:
        routes = client.get("/v1/contract").json()["rest"]
    return [re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", r["path"]) + "$") for r in routes]


def test_every_rest_path_the_island_calls_exists(tmp_path):
    patterns = rest_patterns(tmp_path)
    # Rutas literales completas; las que la isla construye con variables acaban en "/"
    used = set(re.findall(r"""["'`](/v1/[A-Za-z0-9_/%.-]+)""", source()))
    used |= {
        f"/v1/users/x/{rest}" for rest in re.findall(r"/v1/users/\$\{[^}]+\}/([a-z/]+)", source())
    }
    missing = []
    for path in sorted(used):
        path = path.split("?")[0].replace("%3A", ":").rstrip("/")
        if path.endswith(("/v1/users", "/v1/audio", "/v1/system/notifications")):
            continue  # Prefijos que se completan en tiempo de ejecución
        if path == "/v1/system/media/cover":
            continue  # Respaldo antiguo de la isla: solo con `has_cover`, que el núcleo no envía
        if not any(p.match(path) for p in patterns):
            missing.append(path)
    assert missing == [], f"La isla llama a rutas que el núcleo no tiene: {missing}"


def test_the_island_only_sends_events_the_core_accepts():
    sent = set(re.findall(r"""type:\s*["'](user\.[a-z_]+|client\.[a-z_]+)["']""", source()))
    assert sent, "No se encontraron eventos enviados por la isla"
    assert sent <= set(contract.INBOUND), (
        f"Eventos desconocidos: {sorted(sent - set(contract.INBOUND))}"
    )


def test_the_island_handles_every_core_event():
    js = source()
    handled = set(re.findall(r"""["']([a-z]+\.[a-z_]+)["']\s*:\s*(?:\(|async|function)""", js))
    handled |= set(re.findall(r"""^\s+([a-z]+)\s*:\s*(?:\(|async|function)""", js, re.M))
    missing = sorted(set(contract.OUTBOUND) - handled)
    assert missing == [], f"Eventos del núcleo que la isla no maneja: {missing}"
