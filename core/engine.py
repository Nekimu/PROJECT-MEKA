"""MEKA Core: el cerebro y el alma, independientes de cualquier canal.

Telegram, MCP, la mascota de escritorio o una futura app móvil no cargan modelos ni
tocan la memoria: llaman a este motor a través del servidor local (`server/app.py`).
Aquí viven el personaje, la memoria, la IA, la voz y el bus de eventos.
"""

import asyncio
import contextlib
import gc
import sys

from ai.service import AIService
from ai.stt import STTService
from ai.tts import TTSService
from core.audio_store import AudioStore
from core.config import resolve_path
from core.confirmations import ConfirmationRegistry
from core.events import EventBus
from core.focus import FocusMode
from core.hands import Hands
from core.hands.restore import RestorePoints
from core.logger import setup_logger
from core.media import MediaMixin
from core.memory import MemoryStore
from core.persona import Persona, load_active_persona
from core.replies import Reply, UnsupportedFileError
from core.runs import RunLog
from core.semantic import SemanticMemory
from core.system import SystemMonitor
from core.tasks.mixin import AgendaMixin

__all__ = ["MekaEngine", "Reply", "UnsupportedFileError"]

logger = setup_logger("Engine")


class MekaEngine(MediaMixin, AgendaMixin):
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
        # Registro de ejecución (sin contenido) en la misma base que la memoria
        self.runs = RunLog(self.memory.db_path)
        self.ai = ai or AIService(
            config,
            memory=self.memory,
            persona=self.persona,
            semantic=self.semantic,
            runs=self.runs,
        )
        if self.ai.runs is None:
            self.ai.runs = self.runs
        self.stt = stt or STTService(config)
        # auto: si el cerebro entiende audio, la nota de voz va tal cual (T-053) | always: transcribir
        self.stt_mode = config.get("stt", {}).get("mode", "auto")
        self.tts = tts or TTSService(config, voice=self.persona.voice)
        self.bus = bus or EventBus()
        # Permisos antes de acciones delicadas (agent.confirm → user.confirm)
        self.confirmations = ConfirmationRegistry(
            self.bus, config.get("server", {}).get("confirm_timeout_seconds", 120)
        )
        # Modo concentración: retiene lo que distrae (core/focus.py)
        self.focus = FocusMode(config, self.bus)
        # Música y batería para la Dynamic Island (core/system/); arranca con el servidor
        self.system = SystemMonitor(config, self.bus)
        # Manos (fase 3): carpetas autorizadas; los cambios piden permiso y dejan un punto de
        # restauración en data/hands/ (core/hands/)
        self.hands = Hands(
            config,
            self.bus,
            self.runs,
            confirmations=self.confirmations,
            restore_points=RestorePoints(
                resolve_path(config.get("paths", {}).get("hands_dir", "data/hands")),
                self.memory.db_path,
            ),
        )

        server = config.get("server", {})
        self.broadcast = server.get("broadcast_messages", True)
        self.max_doc_chars = config.get("documents", {}).get("max_chars", 4000)
        self.temp_dir = resolve_path(paths.get("temp_dir", "temp"))
        self.uploads_dir = self.temp_dir / "uploads"

        # Un solo proceso pesado a la vez (Ollama, Whisper, Qwen-TTS) para no agotar la RAM
        self.lock = asyncio.Lock()
        self.audio = AudioStore(server.get("audio_ttl_seconds", 300))
        # Tareas, recordatorios y la vigilancia proactiva (core/tasks/); arranca con el servidor
        self._setup_agenda(config)

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
            self.runs.close()
        with contextlib.suppress(Exception):
            self.hands.restore_points.close()
        with contextlib.suppress(Exception):
            self._close_agenda()
        with contextlib.suppress(Exception):
            self.memory.close()
        self.tts.unload()
        self.audio.clear()
        self.confirmations.cancel_all()
        self.focus.close()
        gc.collect()

    # ------------------------------------------------------------------ eventos

    def _say(self, replies: list[Reply], emotion: str = "happy"):
        """La mascota dice lo mismo que el canal (si `server.broadcast_messages`)."""
        if self.broadcast and replies:
            self.bus.publish("message", text=" ".join(r.text for r in replies), emotion=emotion)

    def _emotion(self, emotion: str):
        if self.broadcast:
            self.bus.publish("emotion", emotion=emotion)

    @contextlib.asynccontextmanager
    async def _busy(self):
        """La mascota piensa mientras el núcleo trabaja; si algo revienta, se agobia
        (antes se quedaba en "thinking" para siempre)."""
        self._emotion("thinking")
        try:
            yield
        except Exception:
            self._emotion("error")
            raise

    # ------------------------------------------------------------------ conversación

    async def chat(
        self,
        session: str,
        user: str,
        text: str,
        *,
        audio: bool = True,
        use_memory: bool = True,
        private: bool = False,
        remote: bool = False,
    ) -> list[Reply]:
        """Responde a un mensaje de texto. Con `audio`, sintetiza las frases marcadas con [AUDIO].
        Con `private`, solo responden proveedores locales (ai/routing.py). Con `remote`, la
        respuesta sale del equipo (Telegram, MCP): ni tareas ni recuerdos privados en el prompt."""
        async with self._busy(), self.lock:
            parsed, answer = await self._answer_with_agenda(
                session, user, text, private=private, use_memory=use_memory, remote=remote
            )
            replies = await self._build_replies(parsed, with_audio=audio, private=answer.private)
        self._say(replies, "happy" if answer.ok else "error")
        return replies

    def reset(self, session: str):
        self.ai.reset_conversation(session)

    # ------------------------------------------------------------------ memoria

    # `include_private=False` para quien lleva los datos fuera del equipo (MCP, Telegram)

    def memories(self, user: str, *, include_private: bool = True) -> list[str]:
        return self.memory.get_facts(user, include_private=include_private)

    async def search_memories(
        self, user: str, query: str, *, include_private: bool = True
    ) -> list[str]:
        """Búsqueda por significado y por palabras (la usan la API y MCP)."""
        return await self.ai.recall(user, query, include_private=include_private)

    def remember(self, user: str, fact: str, *, private: bool = False) -> bool:
        return self.memory.add_fact(user, fact, private=private)

    def forget(self, user: str) -> int:
        return self.memory.clear(user)
