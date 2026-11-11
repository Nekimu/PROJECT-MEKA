"""Voz y archivos del motor: notas de voz, imágenes, documentos, audios y subidas.

`MediaMixin` es parte de `MekaEngine` (core/engine.py); vive aparte para que el motor no
crezca. Usa del motor: lock, ai, stt, tts, audio, persona, max_doc_chars, uploads_dir,
_busy(), _say() y _emotion().
"""

import asyncio
import contextlib
import gc
import shutil
import uuid
from pathlib import Path

from ai.prompts import build_document_prompt
from ai.stt.base import to_wav
from ai.text_utils import ParsedMessage, parse_message
from core.documents import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, extract_text
from core.logger import setup_logger
from core.replies import Reply, UnsupportedFileError

logger = setup_logger("Engine")


class MediaMixin:
    # ------------------------------------------------------------------ voz

    async def voice(
        self, session: str, user: str, audio_path: Path, *, audio: bool = True, private=False
    ) -> tuple[str | None, list[Reply]]:
        """Responde a una nota de voz. Devuelve (transcripción, respuestas).

        Si el cerebro entiende audio (T-053) la nota va tal cual y la transcripción es None;
        si no, o si esa ruta falla, se transcribe con faster-whisper como siempre."""
        # STT y LLM dentro del mismo lock: Whisper nunca coincide en RAM con Ollama/Qwen
        async with self._busy(), self.lock:
            transcription = None
            answer = await self._native_voice(session, user, audio_path, private)
            if answer is None:
                try:
                    transcription = await asyncio.to_thread(self.stt.transcribe, audio_path)
                finally:
                    self.stt.release()
                    gc.collect()
                if not transcription:
                    self._emotion("sad")  # No entendió el audio
                    return None, []
                answer = await self.ai.answer(session, user, transcription, private=private)
            replies = await self._build_replies(
                [parse_message(m) for m in answer.messages],
                with_audio=audio,
                private=answer.private,
            )
        self._say(replies, "happy" if answer.ok else "error")
        return transcription, replies

    async def _native_voice(self, session, user, audio_path: Path, private):
        """La nota de voz tal cual al cerebro, si la entiende. None = transcribir."""
        if self.stt_mode != "auto" or not self.ai.hears_natively(private=private):
            return None
        wav = self.new_upload_path(".wav")
        try:
            await asyncio.to_thread(to_wav, audio_path, wav)
            return await self.ai.answer_audio(session, user, wav, private=private)
        except Exception as e:
            logger.warning(f"Audio nativo no disponible ({e}); se transcribe")
            return None
        finally:
            wav.unlink(missing_ok=True)

    async def speak(self, text: str) -> str | None:
        """Sintetiza un texto suelto con la voz del personaje y devuelve el id del audio."""
        async with self.lock:
            try:
                return self.audio.store(await self.tts.generate_audio(text))
            finally:
                self.tts.release()
                gc.collect()

    async def _build_replies(
        self, parsed: list[ParsedMessage], *, with_audio: bool, private: bool = False
    ) -> list[Reply]:
        """Genera todos los audios de una tanda y libera el TTS una sola vez al final."""
        replies = []
        try:
            for message in parsed:
                audio_id = None
                if with_audio and message.wants_audio and message.text:
                    audio_id = self.audio.store(await self.tts.generate_audio(message.text))
                replies.append(Reply.from_message(message, audio_id, private=private))
        finally:
            if with_audio:
                self.tts.release()
                gc.collect()
        return replies

    def take_audio(self, audio_id: str) -> Path | None:
        """Entrega un audio una sola vez: el canal lo descarga y el núcleo lo olvida."""
        return self.audio.take(audio_id)

    # ------------------------------------------------------------------ archivos

    async def analyze_file(
        self,
        session: str,
        user: str,
        path: Path,
        file_name: str,
        request: str | None = None,
        *,
        private: bool = False,
    ) -> list[Reply]:
        """Analiza una imagen (visión) o un documento (texto extraído)."""
        ext = Path(file_name).suffix.lower()
        if ext not in IMAGE_EXTENSIONS and ext not in DOCUMENT_EXTENSIONS:
            raise UnsupportedFileError(ext or file_name)

        async with self._busy(), self.lock:
            if ext in IMAGE_EXTENSIONS:
                request = request or self.persona.line("analyze_image")
                answer = await self.ai.answer_image(session, request, path, private=private)
            else:
                request = request or self.persona.line("analyze_document")
                answer = None
                if ext == ".pdf":  # El PDF entero (tablas, maquetación) si el cerebro lo lee
                    answer = await self.ai.answer_pdf(session, user, path, request, private=private)
                if answer is None:  # Si no: se extrae el texto (recortado a max_chars)
                    extracted = await asyncio.to_thread(extract_text, path, self.max_doc_chars)
                    prompt = build_document_prompt(
                        file_name, extracted.text, request, extracted.truncated
                    )
                    answer = await self.ai.answer(
                        session, user, prompt, use_memory=False, task="document", private=private
                    )
        # Los análisis conservan los paréntesis ("200 € (IVA incluido)") y no llevan audio
        replies = [
            Reply.from_message(parse_message(m, remove_roleplay=False), private=answer.private)
            for m in answer.messages
            if m
        ]
        self._say(replies, "happy" if answer.ok else "error")
        return replies

    def new_upload_path(self, suffix: str) -> Path:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        return self.uploads_dir / f"{uuid.uuid4().hex}{suffix.lower()}"

    def clear_temp(self):
        """Archivos de una ejecución anterior que se interrumpió."""
        with contextlib.suppress(OSError):
            shutil.rmtree(self.uploads_dir)
