"""Dobles de prueba compartidos: simulan Ollama, Whisper y el TTS sin cargar modelos."""

from types import SimpleNamespace

from ollama import Image, Message


class FakeClient:
    """Imita ollama.Client: registra las llamadas y devuelve respuestas programadas."""

    def __init__(self, *replies, fail=False):
        self.replies = list(replies)
        self.fail = fail
        self.calls = []

    def chat(self, **kwargs):
        # Igual que el cliente real: serializa los mensajes, lo que lee del disco cada imagen
        for message in kwargs["messages"]:
            images = [Image(value=image) for image in message.get("images") or []]
            Message(**{**message, "images": images or None}).model_dump()
        self.calls.append(kwargs)
        if self.fail:
            raise ConnectionError("Ollama caído")
        if not kwargs["messages"]:  # unload_model()
            return SimpleNamespace(message=SimpleNamespace(content=""))
        return SimpleNamespace(message=SimpleNamespace(content=self.replies.pop(0)))

    def show(self, model):
        return {}


class FakeSTT:
    def __init__(self, text="hola desde la voz"):
        self.text = text
        self.released = 0

    def transcribe(self, path):
        return self.text

    def release(self):
        self.released += 1

    def unload_model(self):
        return False

    def check_health(self):
        return True


class FakeTTS:
    def __init__(self, folder):
        self.folder = folder
        self.generated = []
        self.released = 0

    async def generate_audio(self, text):
        path = self.folder / f"audio_{len(self.generated)}.ogg"
        path.write_bytes(b"OggS" + text.encode())
        self.generated.append(text)
        return path

    def release(self):
        self.released += 1

    def unload_qwen(self):
        return False

    def check_health(self):
        return True


class FakeProvider:
    """Un proveedor de IA (Claude, Gemini...) con respuestas programadas."""

    def __init__(self, name, *replies, error=None, local=False):
        self.name = name
        self.model = f"{name}-test"
        self.local = local
        self.replies = list(replies)
        self.error = error
        self.calls = []

    async def chat(self, system, messages, *, vision=False):
        self.calls.append({"system": system, "messages": messages, "vision": vision})
        if self.error:
            raise self.error
        return self.replies.pop(0)

    def check_health(self):
        return True

    def unload(self):
        pass
