"""Qwen3-TTS: clonación local de una voz propia (pesado: PyTorch). requirements-qwen.txt"""

import asyncio
import gc
import importlib.util
import sys
from pathlib import Path

from ai.tts.base import new_output_path
from core.config import resolve_path
from core.logger import setup_logger

logger = setup_logger("TTS_Service")

# Parámetros de generación (tuning básico para estabilidad)
DEFAULT_GENERATION = {
    "max_new_tokens": 2048,
    "do_sample": True,
    "top_k": 50,
    "top_p": 0.95,
    "temperature": 0.8,
    "repetition_penalty": 1.1,
}


class QwenEngine:
    name = "qwen-tts"

    def __init__(self, settings: dict):
        self.config = settings.get("qwen") or {}
        self.unload_after_use = self.config.get("unload_after_use", True)
        self.generation = {**DEFAULT_GENERATION, **(self.config.get("generation") or {})}
        self.model = None
        self.voice_prompt = None

    @property
    def ref_audio(self) -> str:
        return str(resolve_path(self.config.get("ref_audio", "")))

    def check_health(self) -> bool:
        # Comprobar las dependencias sin importarlas (importar torch consume RAM)
        missing = [m for m in ("torch", "qwen_tts", "soundfile") if not importlib.util.find_spec(m)]
        if missing:
            logger.critical(
                f"Dependencias de Qwen-TTS faltantes: {', '.join(missing)} "
                "(pip install -r requirements-qwen.txt)"
            )
            return False
        ref_audio = self.config.get("ref_audio", "")
        if not ref_audio or not resolve_path(ref_audio).is_file():
            logger.critical(f"Audio de referencia de Qwen-TTS no encontrado: {ref_audio!r}")
            return False
        return True

    # ------------------------------------------------------------------ modelo

    def load(self) -> bool:
        """Carga el modelo y precalcula el prompt de la voz de referencia (una vez por carga)."""
        if self.model:
            return True
        try:
            import torch
            from qwen_tts import Qwen3TTSModel

            model_id = self.config.get("model_id", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
            device = self.config.get("device", "cpu")
            logger.info(f"Cargando modelo Qwen-TTS ({model_id}) en {device}...")
            self.model = Qwen3TTSModel.from_pretrained(
                model_id, device_map=device, dtype=torch.float32, low_cpu_mem_usage=True
            )
            logger.info("Modelo Qwen-TTS cargado correctamente.")
        except Exception as e:
            logger.error(f"Error cargando Qwen-TTS: {e}")
            self.model = None
            return False

        # Las características de la voz se reutilizan en todos los audios de la carga
        try:
            self.voice_prompt = self.model.create_voice_clone_prompt(
                ref_audio=self.ref_audio,
                ref_text=self.config.get("ref_text", ""),
                x_vector_only_mode=False,
            )
        except Exception as e:
            logger.warning(f"No se pudo precalcular la voz de referencia: {e}")
            self.voice_prompt = None
        return True

    def unload(self):
        """Descarga el modelo de la RAM (y de la GPU si la hay)."""
        if not self.model:
            return
        logger.info("Descargando Qwen-TTS de la memoria para liberar espacio...")
        self.model = None
        self.voice_prompt = None
        gc.collect()
        torch = sys.modules.get("torch")
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()

    def release(self):
        if self.unload_after_use:
            self.unload()

    # ------------------------------------------------------------------ generación

    def _generate(self, text: str, output_path: Path):
        import soundfile as sf

        if self.voice_prompt is not None:
            voice = {"voice_clone_prompt": self.voice_prompt}
        else:
            voice = {
                "ref_audio": self.ref_audio,
                "ref_text": self.config.get("ref_text", ""),
                "x_vector_only_mode": False,
            }
        wavs, sample_rate = self.model.generate_voice_clone(
            text=text, language=self.config.get("language", "Spanish"), **voice, **self.generation
        )
        sf.write(str(output_path), wavs[0], sample_rate)

    async def synthesize(self, text: str, output_dir: Path) -> Path | None:
        # Cargar y generar en un hilo: es una operación pesada en CPU
        if not await asyncio.to_thread(self.load):
            return None
        output_path = new_output_path(output_dir, "meka_qwen", ".wav")
        try:
            await asyncio.to_thread(self._generate, text, output_path)
            logger.info(f"Audio generado con Qwen-TTS: {output_path.name}")
            return output_path
        except Exception as e:
            logger.error(f"Error en Qwen-TTS: {e}")
            output_path.unlink(missing_ok=True)
            return None
