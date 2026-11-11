"""El contrato publicado: eventos, emociones y rutas REST, generado desde el código."""

from fastapi import APIRouter
from fastapi.routing import APIRoute, APIWebSocketRoute

from core import contract
from server.security import require_token

router = APIRouter(prefix="/v1", tags=["estado"])


def _needs_token(*dependency_lists) -> bool:
    return any(dep.dependency is require_token for deps in dependency_lists for dep in deps)


def rest_routes() -> list[dict]:
    """Las rutas que existen de verdad, leídas de los routers registrados (nunca se
    desactualiza). Solo usa atributos públicos de APIRouter/APIRoute."""
    from server.routes import ROUTERS  # Import diferido: este módulo forma parte de ROUTERS

    routes = []
    for api_router in ROUTERS:
        for route in api_router.routes:
            if isinstance(route, APIRoute):
                auth = _needs_token(api_router.dependencies, route.dependencies)
                for method in sorted(route.methods - {"HEAD"}):
                    routes.append({"method": method, "path": route.path, "auth": auth})
            elif isinstance(route, APIWebSocketRoute):
                # Token por ?token= o Authorization (server/security.py)
                routes.append({"method": "WEBSOCKET", "path": route.path, "auth": True})
    return sorted(routes, key=lambda r: (r["path"], r["method"]))


@router.get("/contract")
def get_contract():
    """Versión del contrato, eventos (con sus campos), emociones y rutas REST.
    Público, como /v1/health: no contiene datos del usuario."""
    return {**contract.describe(), "rest": rest_routes()}
