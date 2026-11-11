"""Eventos: publicación por REST y canal en tiempo real (WebSocket) de la mascota y las apps.

Contrato en docs/VISION.md («Contrato de eventos») y coordinacion/README.md.
"""

import asyncio
import contextlib
import json

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from core import contract
from core.engine import MekaEngine
from core.events import CORE_ONLY_EVENTS, OUTBOUND_EVENTS
from core.logger import setup_logger
from server.deps import AUTH, get_engine
from server.schemas import EventRequest
from server.security import websocket_authorized

logger = setup_logger("Server")

router = APIRouter(prefix="/v1", tags=["eventos"])


def validate_event(type_: str, data: dict) -> dict:
    if type_ in CORE_ONLY_EVENTS:
        raise ValueError(
            f"{type_} lo emite el núcleo: para pedir permiso usa POST /v1/confirmations"
        )
    errors = contract.validate(type_, data)
    if errors:
        raise ValueError(
            "; ".join(errors)
            + f". Contrato en GET /v1/contract (eventos: {sorted(OUTBOUND_EVENTS)})"
        )
    return data


@router.post("/events", dependencies=AUTH, status_code=status.HTTP_202_ACCEPTED)
def publish(body: EventRequest, request: Request):
    """Un agente externo (MCP, scripts) avisa a la mascota: agent.working, agent.done..."""
    try:
        data = validate_event(body.type, body.data)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    engine = get_engine(request)
    engine.bus.publish(body.type, **data)
    return {"delivered": engine.bus.subscribers}


class ClientSession:
    """Un cliente conectado al WebSocket: recibe los eventos del bus y envía los suyos."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.engine: MekaEngine = websocket.app.state.engine
        self.local_user: str = websocket.app.state.local_user
        self.name = "cliente"

    async def handle(self, type_: str, data: dict):
        if type_ == "client.hello":
            self.name = str(data.get("client") or self.name)[:50]
            logger.info(f"Cliente conectado: {self.name}")
        elif type_ == "user.message" and str(data.get("text") or "").strip():
            replies = await self.engine.chat(
                f"ws:{self.name}",
                self.local_user,
                str(data["text"])[:20_000],
                audio=False,
                private=bool(data.get("private")),
            )
            # Si no se difunde (o el modo concentración retiene la difusión), se le envía a quien habló
            focused = self.engine.focus.active
            if not self.engine.broadcast or focused:
                text = " ".join(r.text for r in replies)
                await self.websocket.send_json(
                    {"type": "message", "data": {"text": text, "emotion": "happy"}}
                )
                if focused and self.engine.broadcast:
                    self.engine.focus.delivered("message")  # La respuesta sí te llegó
        elif type_ == "user.focus":
            try:
                if data.get("action") == "stop":
                    self.engine.focus.stop("user")
                else:
                    await self.engine.focus.start(data.get("minutes"))
            except (ValueError, TypeError) as e:
                logger.info(f"user.focus no válido: {e}")
        elif type_ == "user.notification" and data.get("id") is not None:
            try:
                await self.engine.system.notification_action(
                    int(data["id"]), str(data.get("action"))
                )
            except (ValueError, TypeError) as e:
                logger.info(f"user.notification no válido: {e}")
        elif type_ == "user.media":
            try:
                await self.engine.system.media_control(str(data.get("action")))
            except ValueError as e:
                logger.info(f"user.media no válido: {e}")
        elif type_ == "user.confirm" and data.get("id"):
            if not self.engine.confirmations.resolve(
                str(data["id"]), bool(data.get("approved")), by=self.name
            ):
                logger.info(f"user.confirm para un permiso que ya no está pendiente: {data['id']}")
        else:
            logger.debug(f"Mensaje de cliente sin manejar: {type_}")

    async def run(self):
        queue = self.engine.bus.subscribe()

        async def pump():
            while True:
                await self.websocket.send_json(await queue.get())

        sender = asyncio.create_task(pump())
        try:
            while True:
                try:
                    message = json.loads(await self.websocket.receive_text())
                    type_, data = message["type"], message.get("data") or {}
                except (ValueError, KeyError, TypeError):
                    logger.warning("Mensaje WebSocket no válido; se ignora")
                    continue
                await self.handle(type_, data)
        except WebSocketDisconnect:
            pass
        finally:
            self.engine.bus.unsubscribe(queue)
            sender.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await sender
            logger.info(f"Cliente desconectado: {self.name}")


@router.websocket("/events")
async def events(websocket: WebSocket):
    """Canal en tiempo real de la mascota y las apps."""
    if not websocket_authorized(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    await ClientSession(websocket).run()
