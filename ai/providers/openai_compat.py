"""Servidores compatibles con la API de OpenAI: llama.cpp (llama-server), LM Studio, vLLM...

Un solo adaptador abre cualquier servidor local que hable `/v1/chat/completions`. Con
llama.cpp, Gemma 4 (E2B/E4B/12B) entiende **audio nativo** (`input_audio`), algo que Ollama
todavía no pasa de forma fiable (T-054).

    ai:
      providers:
        openai_compat:
          base_url: "http://127.0.0.1:8080"   # llama-server
          model: "gemma-4-e4b"
          capabilities: [text, vision, audio]  # Lo que entiende TU modelo
          thinking: false   # Gemma 4 / Qwen: sin razonamiento previo (más rápido y sin vaciar la respuesta)

Privacidad: el servidor solo cuenta como local si su dirección es de este equipo. Uno en
otra máquina se trata como nube, salvo que declares `local: true` (p. ej. tu PC en la LAN).
"""

import base64
import os
from urllib.parse import urlparse

import httpx

from ai.providers.base import ProviderError, ProviderReply, file_bytes, image_bytes
from core.config import is_loopback
from core.logger import setup_logger

logger = setup_logger("OpenAICompat")


class OpenAICompatProvider:
    name = "openai_compat"
    capabilities = frozenset({"text"})  # Depende del modelo: declara las suyas en config.yml

    def __init__(self, settings: dict, client: httpx.AsyncClient | None = None):
        self.base_url = str(settings.get("base_url", "http://127.0.0.1:8080")).rstrip("/")
        self.model = settings.get("model", "local")
        host = urlparse(self.base_url).hostname or ""
        self.local = bool(settings.get("local", is_loopback(host)))
        self.temperature = settings.get("temperature", 0.8)
        self.max_tokens = int(settings.get("max_tokens", 1024))
        self.thinking = settings.get("thinking")  # None: lo que decida el servidor
        key = os.getenv(settings["api_key_env"]) if settings.get("api_key_env") else None
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        self.client = client or httpx.AsyncClient(
            base_url=self.base_url, headers=headers, timeout=float(settings.get("timeout", 300))
        )
        where = "local" if self.local else "REMOTO (se trata como nube)"
        logger.info(f"Servidor compatible con OpenAI en {self.base_url} ({where}): {self.model}")

    @staticmethod
    def _content(message: dict):
        if not (message.get("images") or message.get("audio")):
            return message["content"]
        parts = []
        for path in message.get("images") or []:
            data, mime = image_bytes(path)
            url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            parts.append({"type": "image_url", "image_url": {"url": url}})
        for path in message.get("audio") or []:
            data, mime = file_bytes(path, "audio/wav")
            audio_format = "mp3" if "mp" in mime else "wav"
            parts.append({
                "type": "input_audio",
                "input_audio": {"data": base64.b64encode(data).decode(), "format": audio_format},
            })  # fmt: skip
        parts.append({"type": "text", "text": message["content"]})
        return parts

    async def chat(
        self, system: str, messages: list[dict], *, vision: bool = False
    ) -> ProviderReply:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}]
            + [{"role": m["role"], "content": self._content(m)} for m in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.thinking is not None:  # llama.cpp y vLLM lo pasan a la plantilla del modelo
            payload["chat_template_kwargs"] = {"enable_thinking": bool(self.thinking)}
        try:
            response = await self.client.post("/v1/chat/completions", json=payload)
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.name}: no responde en {self.base_url} ({e})") from e
        if response.status_code != 200:
            raise ProviderError(f"{self.name}: HTTP {response.status_code} {response.text[:200]}")
        body = response.json()
        try:
            message = body["choices"][0]["message"]
            text = message.get("content") or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"{self.name}: respuesta inesperada") from e
        if not text.strip() and message.get("reasoning_content"):
            # Se le fueron los tokens pensando: mejor que otra ruta conteste
            raise ProviderError(
                f"{self.name}: solo razonó, sin respuesta (prueba `thinking: false`)"
            )
        usage = body.get("usage") or {}
        return ProviderReply(
            text=text.strip(),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    def check_health(self) -> bool:
        """¿Responde el servidor? (sin cargar nada: GET /v1/models)."""
        try:
            response = httpx.get(f"{self.base_url}/v1/models", timeout=5)
        except httpx.HTTPError as e:
            logger.critical(f"No responde el servidor en {self.base_url}: {e}")
            return False
        if response.status_code != 200:
            logger.critical(f"El servidor en {self.base_url} devolvió HTTP {response.status_code}")
            return False
        return True

    def unload(self):
        pass  # El servidor gestiona su propia memoria
