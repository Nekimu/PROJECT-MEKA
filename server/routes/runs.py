"""Registro de ejecución del cerebro (sin contenido de las conversaciones)."""

import time

from fastapi import APIRouter, Query, Request

from server.deps import AUTH, get_engine

router = APIRouter(prefix="/v1", tags=["estado"], dependencies=AUTH)


@router.get("/runs")
def runs(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    days: float = Query(30, gt=0, le=365, description="Ventana del resumen por proveedor"),
):
    """Últimas llamadas a los proveedores de IA y un resumen por proveedor: llamadas,
    fallos, tokens y latencia media. Nunca incluye el texto de las conversaciones."""
    log = get_engine(request).runs
    return {
        "runs": log.recent(limit),
        "summary": log.summary(since=time.time() - days * 86_400),
    }
