"""MEKA Core: el cerebro y el alma, independientes de cualquier canal.

Telegram, MCP, la mascota de escritorio o una futura app móvil no cargan modelos ni
tocan la memoria: llaman a este motor a través del servidor local (`server/app.py`).
Aquí viven el personaje, la memoria, la IA, la voz y el bus de eventos.
"""

import asyncio
import contextlib
import gc
import shutil
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from ai.prompts import build_document_prompt
from ai.service import AIService
from ai.stt import STTService
from ai.text_utils import ParsedMessage, parse_message
from ai.tts import TTSService
from core.config import resolve_path
from core.documents import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, extract_text
from core.events import EventBus
from core.logger import setup_logger
from core.memory import MemoryStore
from core.persona import Persona, load_active_persona
from core.semantic import SemanticMemory

logger = setup_logger("Engine")


class UnsupportedFileError(ValueError):
    """El tipo de archivo no se puede analizar."""


@dataclass
class Reply:
    """Un mensaje de respuesta listo para cualquier canal."""

    text: str
    audio: str | None = None  # Identificador del audio en GET /v1/audio/{id}
    sticker: bool = False
    gif: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _Audio:
    path: Path
    created: float


class MekaEngine:
    def __init__(
        self,
        config: dict,
        *,
        persona: Persona | None = None,
        memory: MemoryStore | None = None,
        ai: AIService | None = None,
        stt: STTService | None = None,
        tts: TTSService | None = None,
        bus: EventBus | None = None,
    ):
        self.config = config
        self.persona = persona or load_active_persona(config)
        paths = config.get("paths", {})
        allowed = config.get("telegram", {}).get("allowed_user_ids") or []
        # La primera vez se importa el antiguo memory.json (y se renombra a .migrated)
        self.memory = memory or MemoryStore(
            resolve_path(paths.get("memory_db", "data/meka.db")),
            legacy_json=resolve_path("memory.json"),
            legacy_owner=allowed[0] if allowed else None,
        )
        self.semantic = SemanticMemory.from_config(self.memory, config)
        self.ai = ai or AIService(
            config, memory=self.memory, persona=self.persona, semantic=self.semantic
        )
        self.stt = stt or STTService(config)
        self.tts = tts or TTSService(config, voice=self.persona.voice)
        self.bus = bus or EventBus()

        server = config.get("server", {})
        self.broadcast = server.get("broadcast_messages", True)
        self.audio_ttl = server.get("audio_ttl_seconds", 300)
        self.max_doc_chars = config.get("documents", {}).get("max_chars", 4000)
        self.temp_dir = resolve_path(paths.get("temp_dir", "temp"))
        self.uploads_dir = self.temp_dir / "uploads"

        # Un solo proceso pesado a la vez (Ollama, Whisper, Qwen-TTS) para no agotar la RAM
        self.lock = asyncio.Lock()
        self._audio: dict[str, _Audio] = {}

    # ------------------------------------------------------------------ ciclo de vida

    def check_health(self) -> dict[str, bool]:
        """Diagnóstico de arranque: no bloquea, solo avisa."""
        status = {
            "ai": self.ai.check_health(),
            "tts": self.tts.check_health(),
            "stt": self.stt.check_health(),
        }
        if self.semantic is not None:
            status["memoria semántica"] = self.semantic.check_health()
        for name, ok in status.items():
            if not ok:
                logger.error(f"ADVERTENCIA: '{name}' no está listo; esa función podría fallar.")
        return status

    def close(self):
        """Libera modelos y archivos temporales al apagar."""
        logger.info("Liberando recursos de IA y voz...")
        # Resetear torch._dynamo (solo si torch llegó a cargarse) para evitar el error en atexit
        torch = sys.modules.get("torch")
        if torch is not None:
            with contextlib.suppress(Exception):
                torch._dynamo.reset()
        self.ai.unload_model()
        self.stt.unload_model()
        with contextlib.suppress(Exception):
            self.memory.close()
        self.tts.unload_qwen()
        for audio_id in list(self._audio):
            self._drop_audio(audio_id)
        gc.collect()

    # ------------------------------------------------------------------ eventos

    def _say(self, replies: list[Reply], emotion: str = "happy"):
        """La mascota dice lo mismo que el canal (si `server.broadcast_messages`)."""
        if self.broadcast and replies:
            self.bus.publish("message", text=" ".join(r.text for r in replies), emotion=emotion)

    def _thinking(self):
        if self.broadcast:
            self.bus.publish("emotion", emotion="thinking")

    # ------------------------------------------------------------------ conversación

    async def chat(
        self,
        session: str,
        user: str,
        text: str,
        *,
        audio: bool = True,
        use_memory: bool = True,
    ) -> list[Reply]:
        """Responde a un mensaje de texto. Con `audio`, sintetiza las frases marcadas con [AUDIO]."""
        self._thinking()
        async with self.lock:
            raw = await self.ai.generate_response(session, user, text, use_memory=use_memory)
            replies = await self._build_replies([parse_message(m) for m in raw], with_audio=audio)
        self._say(replies)
        return replies

    async def voice(
        self, session: str, user: str, audio_path: Path, *, audio: bool = True
    ) -> tuple[str | None, list[Reply]]:
        """Transcribe una nota de voz y responde. Devuelve (transcripción, respuestas)."""
        self._thinking()
        # STT y LLM dentro del mismo lock: Whisper nunca coincide en RAM con Ollama/Qwen
        async with self.lock:
            try:
                transcription = await asyncio.to_thread(self.stt.transcribe, audio_path)
            finally:
                self.stt.release()
                gc.collect()
            if not transcription:
                return None, []
            raw = await self.ai.generate_response(session, user, transcription)
            replies = await self._build_replies([parse_message(m) for m in raw], with_audio=audio)
        self._say(replies)
        return transcription, replies

    async def analyze_file(
        self, session: str, user: str, path: Path, file_name: str, request: str | None = None
    ) -> list[Reply]:
        """Analiza una imagen (visión) o un documento (texto extraído)."""
        ext = Path(file_name).suffix.lower()
        if ext not in IMAGE_EXTENSIONS and ext not in DOCUMENT_EXTENSIONS:
            raise UnsupportedFileError(ext or file_name)

        self._thinking()
        async with self.lock:
            if ext in IMAGE_EXTENSIONS:
                request = request or self.persona.line("analyze_image")
                raw = await self.ai.generate_multimodal_response(session, request, path)
            else:
                request = request or self.persona.line("analyze_document")
                extracted = await asyncio.to_thread(extract_text, path, self.max_doc_chars)
                prompt = build_document_prompt(
                    file_name, extracted.text, request, extracted.truncated
                )
                raw = await self.ai.generate_response(session, user, prompt, use_memory=False)
        # Los análisis conservan los paréntesis ("200 € (IVA incluido)") y no llevan audio
        replies = [self._to_reply(parse_message(m, remove_roleplay=False), None) for m in raw if m]
        self._say(replies)
        return replies

    def reset(self, session: str):
        self.ai.reset_conversation(session)

    # ------------------------------------------------------------------ memoria

    def memories(self, user: str) -> list[str]:
        return self.memory.get_facts(user)

    async def search_memories(self, user: str, query: str) -> list[str]:
        """Búsqueda por significado y por palabras (la usan la API y MCP)."""
        return await self.ai.recall(user, query)

    def remember(self, user: str, fact: str) -> bool:
        return self.memory.add_fact(user, fact)

    def forget(self, user: str) -> int:
        return self.memory.clear(user)

    # ------------------------------------------------------------------ voz

    async def speak(self, text: str) -> str | None:
        """Sintetiza un texto suelto con la voz del personaje y devuelve el id del audio."""
        async with self.lock:
            try:
                return self._store_audio(await self.tts.generate_audio(text))
            finally:
                self.tts.release()
                gc.collect()

    async def _build_replies(self, parsed: list[ParsedMessage], *, with_audio: bool) -> list[Reply]:
        """Genera todos los audios de una tanda y libera el TTS una sola vez al final."""
        replies = []
        try:
            for message in parsed:
                audio_id = None
                if with_audio and message.wants_audio and message.text:
                    audio_id = self._store_audio(await self.tts.generate_audio(message.text))
                replies.append(self._to_reply(message, audio_id))
        finally:
            if with_audio:
                self.tts.release()
                gc.collect()
        return replies

    @staticmethod
    def _to_reply(message: ParsedMessage, audio_id: str | None) -> Reply:
        return Reply(
            text=message.text, audio=audio_id, sticker=message.wants_sticker, gif=message.wants_gif
        )

    def _store_audio(self, path: Path | None) -> str | None:
        self.purge_audio()
        if path is None:
            return None
        audio_id = uuid.uuid4().hex
        self._audio[audio_id] = _Audio(Path(path), time.monotonic())
        return audio_id

    def take_audio(self, audio_id: str) -> Path | None:
        """Entrega un audio una sola vez: el canal lo descarga y el núcleo lo olvida."""
        audio = self._audio.pop(audio_id, None)
        return audio.path if audio and audio.path.is_file() else None

    def _drop_audio(self, audio_id: str):
        audio = self._audio.pop(audio_id, None)
        if audio:
            audio.path.unlink(missing_ok=True)

    def purge_audio(self):
        """Borra los audios que ningún canal pidió a tiempo (`server.audio_ttl_seconds`)."""
        limit = time.monotonic() - self.audio_ttl
        for audio_id, audio in list(self._audio.items()):
            if audio.created < limit:
                self._drop_audio(audio_id)

    # ------------------------------------------------------------------ archivos subidos

    def new_upload_path(self, suffix: str) -> Path:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        return self.uploads_dir / f"{uuid.uuid4().hex}{suffix.lower()}"

    def clear_temp(self):
        """Archivos de una ejecución anterior que se interrumpió."""
        with contextlib.suppress(OSError):
            shutil.rmtree(self.uploads_dir)
