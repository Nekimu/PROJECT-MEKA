"""Entradas que no son texto: imágenes, notas de voz y PDF (T-053).

El objetivo es siempre el mismo (entender y responder), pero la ruta depende de lo que
entiende cada cerebro:

| Entrada | Si el cerebro lo entiende (capabilities) | Si no |
|---|---|---|
| Imagen | `vision`: se le envía la imagen | Error de visión del personaje |
| Audio  | `audio`: se le envía la nota y se omite la transcripción | faster-whisper → texto |
| PDF    | `pdf`: se le envía el documento | Se extrae el texto (core/documents.py) |

Si la ruta nativa falla, estos métodos devuelven None y el motor usa la ruta clásica.
El audio no pasa por el detector de datos sensibles (no hay texto que revisar), así que
solo va a cerebros locales salvo que `ai.privacy.audio_to_cloud` lo permita.

`MultimodalMixin` es parte de `AIService` (ai/service.py).
"""

from ai.answer import Answer
from ai.text_utils import split_into_messages, split_paragraphs
from core.logger import setup_logger

logger = setup_logger("AI_Service")

VOICE_NOTE = (
    "(El usuario te envió esta nota de voz. Escúchala y respóndele como a cualquier mensaje, "
    "con tu personalidad de siempre.)"
)


class MultimodalMixin:
    async def _native(self, chat_id, messages, *, system, task, need, private, history_text):
        """Llama a la ruta nativa. None si no hay cerebro capaz o si falla (habrá respaldo)."""
        try:
            reply, latency_ms, used = await self._chat(
                system, messages, task=task, private=private, need=need
            )
        except Exception as e:
            logger.warning(f"Ruta nativa de '{need}' no disponible ({e}); se usa la clásica")
            return None
        if not reply.text:
            return None
        self.history.add_exchange(chat_id, history_text, reply.text)
        logger.info(f"Respuesta con {need} nativo en {latency_ms}ms | {used}")
        self._log(f"{self.persona.name} ({need})", f"({latency_ms}ms) {reply.text}")
        return Answer(
            split_into_messages(reply.text), True, used, self.providers[used].model,
            latency_ms, private,
        )  # fmt: skip

    def hears_natively(self, *, private: bool = False) -> bool:
        """¿Puede ir la nota de voz tal cual al cerebro de la conversación?"""
        return self.router.can("chat", "audio", private=private, local_only=not self.audio_to_cloud)

    async def answer_audio(self, chat_id, user_id, audio_path, *, private=False) -> Answer | None:
        """Responde a una nota de voz sin transcribirla. None = usa faster-whisper."""
        private = self._privacy(chat_id, "", private)
        if not self.hears_natively(private=private):
            return None
        self._log("User (voz)", "[Nota de voz enviada al cerebro tal cual]")
        messages = [
            *self.history.get(chat_id),
            {"role": "user", "content": VOICE_NOTE, "audio": [str(audio_path)]},
        ]
        return await self._native(
            chat_id, messages, system=self.system_prompt, task="chat", need="audio",
            private=private, history_text="[Te envié una nota de voz]",
        )  # fmt: skip

    async def answer_pdf(self, chat_id, user_id, pdf_path, request, *, private=False):
        """Analiza un PDF entero (tablas y maquetación incluidas). None = extraer el texto."""
        private = self._privacy(chat_id, request, private or self.private_documents)
        if not self.router.can("document", "pdf", private=private):
            return None
        self._log("User (PDF)", f"{request} [PDF]")
        messages = [
            *self.history.get(chat_id),
            {"role": "user", "content": request, "documents": [str(pdf_path)]},
        ]
        return await self._native(
            chat_id, messages, system=self.system_prompt, task="document", need="pdf",
            private=private, history_text=f"[Te envié un PDF] {request}",
        )  # fmt: skip

    async def answer_image(self, chat_id, user_text: str, image_path, *, private=False) -> Answer:
        """Analiza una imagen con el cerebro de visión."""
        self._log("User (Multimodal)", f"{user_text} [Imagen]")
        private = self._privacy(chat_id, user_text, private)
        messages = [{"role": "user", "content": user_text, "images": [str(image_path)]}]
        try:
            logger.info("Enviando imagen al modelo para análisis...")
            reply, latency_ms, used = await self._chat(
                self.vision_prompt, messages, task="vision", private=private, need="vision"
            )
        except Exception as e:
            logger.error(f"Error en análisis multimodal: {e}")
            return Answer([self.persona.line("vision_error")], ok=False, private=private)

        # El archivo de la imagen se borra tras procesarse: en el historial guardamos solo
        # texto. Guardar la ruta hacía fallar todas las respuestas posteriores del chat.
        self.history.add_exchange(chat_id, f"[Te envié una imagen] {user_text}", reply.text)
        logger.info(f"Análisis multimodal completado en {latency_ms}ms | {used}")
        self._log(f"{self.persona.name} (visión)", f"({latency_ms}ms) {reply.text}")
        paragraphs = split_paragraphs(reply.text)
        if not paragraphs:
            return Answer([self.persona.line("empty_reply")], False, used, private=private)
        return Answer(paragraphs, True, used, self.providers[used].model, latency_ms, private)
