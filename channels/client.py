"""Cliente HTTP de MEKA Core: lo usan todos los canales (Telegram, MCP...)."""

import asyncio
from urllib.parse import quote

import httpx

from core.config import core_url
from core.logger import setup_logger
from core.persona import Persona

logger = setup_logger("CoreClient")


class CoreUnavailableError(RuntimeError):
    """MEKA Core no responde."""


class CoreClient:
    def __init__(
        self,
        base_url: str,
        token: str = "",
        *,
        timeout: float = 300.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        # Los modelos locales pueden tardar minutos en responder (sobre todo con keep_alive=0)
        self.http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout, transport=transport
        )

    @classmethod
    def from_config(cls, config: dict, **kwargs) -> "CoreClient":
        server = config.get("server", {})
        return cls(core_url(config), str(server.get("token") or ""), **kwargs)

    async def close(self):
        await self.http.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = await self.http.request(method, path, **kwargs)
        except httpx.TransportError as e:
            raise CoreUnavailableError(f"MEKA Core no responde en {self.http.base_url}: {e}") from e
        response.raise_for_status()
        return response

    async def _json(self, method: str, path: str, **kwargs) -> dict:
        return (await self._request(method, path, **kwargs)).json()

    # ------------------------------------------------------------------ estado

    async def health(self) -> dict:
        return await self._json("GET", "/v1/health")

    async def persona(self) -> Persona:
        return Persona.from_dict(await self._json("GET", "/v1/persona"))

    async def wait_ready(self, attempts: int = 30, delay: float = 1.0) -> Persona:
        """Espera a que el núcleo arranque (p. ej. con `python run.py all`) y trae el personaje."""
        for attempt in range(1, attempts + 1):
            try:
                await self.health()
                return await self.persona()
            except CoreUnavailableError:
                if attempt == attempts:
                    raise
                if attempt == 1:
                    logger.info(f"Esperando a MEKA Core en {self.http.base_url}...")
                await asyncio.sleep(delay)
        raise CoreUnavailableError("MEKA Core no arrancó")  # pragma: no cover

    # ------------------------------------------------------------------ conversación

    async def chat(self, session: str, user: str, text: str, **options) -> list[dict]:
        body = {"session": session, "user": user, "text": text, **options}
        return (await self._json("POST", "/v1/chat", json=body))["replies"]

    async def voice(
        self, session: str, user: str, audio: bytes, filename: str = "voz.ogg", audio_reply=True
    ) -> tuple[str | None, list[dict]]:
        data = await self._json(
            "POST",
            "/v1/voice",
            data={"session": session, "user": user, "audio": str(audio_reply).lower()},
            files={"file": (filename, audio)},
        )
        return data["transcription"], data["replies"]

    async def analyze_file(
        self, session: str, user: str, content: bytes, filename: str, caption: str | None = None
    ) -> list[dict]:
        data = {"session": session, "user": user}
        if caption:
            data["caption"] = caption
        result = await self._json(
            "POST", "/v1/files", data=data, files={"file": (filename, content)}
        )
        return result["replies"]

    async def reset(self, session: str):
        await self._request("POST", f"/v1/sessions/{quote(session, safe='')}/reset")

    # ------------------------------------------------------------------ voz

    async def speech(self, text: str) -> str | None:
        return (await self._json("POST", "/v1/speech", json={"text": text}))["audio"]

    async def audio(self, audio_id: str) -> bytes:
        return (await self._request("GET", f"/v1/audio/{quote(audio_id, safe='')}")).content

    # ------------------------------------------------------------------ memoria

    async def memories(self, user: str) -> list[str]:
        return (await self._json("GET", f"/v1/users/{quote(user, safe='')}/memories"))["memories"]

    async def remember(self, user: str, fact: str) -> bool:
        return (
            await self._json(
                "POST", f"/v1/users/{quote(user, safe='')}/memories", json={"fact": fact}
            )
        )["added"]

    async def forget(self, user: str) -> int:
        return (await self._json("DELETE", f"/v1/users/{quote(user, safe='')}/memories"))["removed"]

    # ------------------------------------------------------------------ eventos

    async def publish(self, type_: str, **data) -> int:
        """Envía un evento a la mascota (agent.working, agent.done, emotion...)."""
        return (await self._json("POST", "/v1/events", json={"type": type_, "data": data}))[
            "delivered"
        ]
