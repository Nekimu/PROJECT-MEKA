import asyncio
import gc
import importlib.util
import shutil
import sys
import uuid
from pathlib import Path

from ai.text_utils import clean_for_speech
from core.config import resolve_path, settings
from core.logger import setup_logger
from core.persona import persona as active_persona

logger = setup_logger("TTS_Service")

ENGINES = ("qwen-tts", "edge-tts", "piper")

# Parámetros de generación de Qwen-TTS (tuning básico para estabilidad)
DEFAULT_QWEN_GENERATION = {
    "max_new_tokens": 2048,
    "do_sample": True,
    "top_k": 50,
    "top_p": 0.95,
    "temperature": 0.8,
    "repetition_penalty": 1.1,
}


class TTSService:
    def __init__(self, config: dict | None = None, voice: dict | None = None):
        tts_config = (settings if config is None else config).get("tts", {})
        # La voz (edge-tts) la define el personaje activo y tiene prioridad sobre config.yml
        voice = active_persona.voice if voice is None else voice
        tts_config = {**tts_config, **voice}
        self.enabled = tts_config.get("enabled", False)
        self.engine = tts_config.get("engine", "edge-tts")
        self.fallback_engine = tts_config.get("fallback_engine")
        self.output_dir = resolve_path(tts_config.get("output_dir", "temp_audio"))
        # Telegram solo muestra como nota de voz OGG/Opus (y MP3/M4A); el WAV llega como archivo
        self.convert_to_ogg = tts_config.get("convert_to_ogg", True)

        # Edge-TTS config
        self.voice = tts_config.get("voice", "es-MX-DaliaNeural")
        self.rate = tts_config.get("rate", "+0%")
        self.pitch = tts_config.get("pitch", "+0Hz")

        # Piper config (se aceptan también las claves antiguas en la raíz de `tts`)
        piper_config = tts_config.get("piper") or {}
        self.piper_path = piper_config.get("path", tts_config.get("piper_path", "piper"))
        self.model_path = piper_config.get("model_path", tts_config.get("model_path", ""))
        self.length_scale = piper_config.get("length_scale", 1.0)
        self.noise_scale = piper_config.get("noise_scale", 0.667)
        self.noise_w = piper_config.get("noise_w", 0.8)

        # Qwen-TTS config
        self.qwen_config = tts_config.get("qwen", {})
        self.qwen_unload_after_use = self.qwen_config.get("unload_after_use", True)
        self.qwen_generation = {
            **DEFAULT_QWEN_GENERATION,
            **(self.qwen_config.get("generation") or {}),
        }
        self.qwen_model = None
        self._qwen_voice_prompt = None

        if self.enabled:
            logger.info(f"TTS Service cargado con el motor: {self.engine}")
            # No cargamos Qwen aquí para ahorrar RAM al inicio

    # ------------------------------------------------------------------ diagnóstico

    def check_health(self) -> bool:
        """Verifica que el motor TTS seleccionado esté operativo (sin cargar modelos)."""
        if not self.enabled:
            return True
        healthy = self._check_engine(self.engine)
        if not healthy and self.fallback_engine and self.fallback_engine != self.engine:
            logger.warning(f"Se usará el motor de respaldo '{self.fallback_engine}'")
            healthy = self._check_engine(self.fallback_engine)
        if self.convert_to_ogg and shutil.which("ffmpeg") is None:
            logger.warning("FFmpeg no está en el PATH: los audios no se convertirán a OGG/Opus")
        return healthy

    def _check_engine(self, engine: str) -> bool:
        if engine == "piper":
            if shutil.which(self.piper_path) is None and not Path(self.piper_path).exists():
                logger.critical(f"No se encontró el ejecutable de Piper en {self.piper_path}")
                return False
            if not Path(self.model_path).exists():
                logger.critical(f"No se encontró el modelo de Piper en {self.model_path}")
                return False
        elif engine == "qwen-tts":
            # Verificar dependencias críticas sin importarlas (importar torch consume RAM)
            missing = [
                m for m in ("torch", "qwen_tts", "soundfile") if not importlib.util.find_spec(m)
            ]
            if missing:
                logger.critical(
                    f"Dependencias de Qwen-TTS faltantes: {', '.join(missing)} "
                    "(pip install -r requirements-qwen.txt)"
                )
                return False
            ref_audio = self.qwen_config.get("ref_audio", "")
            if not ref_audio or not resolve_path(ref_audio).is_file():
                logger.critical(f"Audio de referencia de Qwen-TTS no encontrado: {ref_audio!r}")
                return False
        elif engine == "edge-tts":
            if importlib.util.find_spec("edge_tts") is None:
                logger.critical("Librería edge-tts faltante")
                return False
        else:
            logger.critical(f"Motor TTS desconocido: {engine!r}. Opciones: {', '.join(ENGINES)}")
            return False
        return True

    # ------------------------------------------------------------------ generación

    async def generate_audio(self, text: str) -> Path | None:
        """Genera un archivo de audio (OGG/Opus si hay FFmpeg) a partir de un texto."""
        if not self.enabled:
            return None

        clean_text = clean_for_speech(text)
        if not clean_text:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = await self._synthesize(self.engine, clean_text)
        if output_path is None and self.fallback_engine and self.fallback_engine != self.engine:
            logger.warning(f"Fallo en '{self.engine}', probando con '{self.fallback_engine}'")
            output_path = await self._synthesize(self.fallback_engine, clean_text)

        if output_path and self.convert_to_ogg:
            output_path = await self._to_ogg_opus(output_path)
        return output_path

    async def _synthesize(self, engine: str, text: str) -> Path | None:
        generators = {
            "edge-tts": self._generate_edge_tts,
            "qwen-tts": self._generate_qwen_tts,
            "piper": self._generate_piper,
        }
        generator = generators.get(engine)
        if generator is None:
            logger.error(f"Motor TTS desconocido: {engine!r}")
            return None
        return await generator(text)

    def _new_output_path(self, prefix: str, suffix: str) -> Path:
        return self.output_dir / f"{prefix}_{uuid.uuid4().hex}{suffix}"

    async def _to_ogg_opus(self, path: Path) -> Path:
        """Convierte el audio a OGG/Opus mono con FFmpeg. Si no se puede, devuelve el original."""
        if path.suffix == ".ogg":
            return path
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            return path

        ogg_path = path.with_suffix(".ogg")
        try:
            process = await asyncio.create_subprocess_exec(
                ffmpeg, "-y", "-loglevel", "error", "-i", str(path),
                "-ac", "1", "-c:a", "libopus", "-b:a", "48k", str(ogg_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )  # fmt: skip
            _, stderr = await process.communicate()
        except Exception as e:
            logger.warning(f"No se pudo convertir el audio a OGG/Opus: {e}")
            return path

        if process.returncode != 0:
            logger.warning(f"FFmpeg no pudo convertir el audio: {stderr.decode(errors='ignore')}")
            ogg_path.unlink(missing_ok=True)
            return path
        path.unlink(missing_ok=True)
        return ogg_path

    # ------------------------------------------------------------------ Qwen-TTS

    def _init_qwen(self) -> bool:
        """Inicializa el modelo Qwen-TTS y precalcula el prompt de la voz de referencia."""
        if self.qwen_model:
            return True
        try:
            import torch
            from qwen_tts import Qwen3TTSModel

            model_id = self.qwen_config.get("model_id", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
            device = self.qwen_config.get("device", "cpu")

            logger.info(f"Cargando modelo Qwen-TTS ({model_id}) en {device}...")
            self.qwen_model = Qwen3TTSModel.from_pretrained(
                model_id,
                device_map=device,
                dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            logger.info("Modelo Qwen-TTS cargado correctamente.")
        except Exception as e:
            logger.error(f"Error cargando Qwen-TTS: {e}")
            self.qwen_model = None
            return False

        # Las características de la voz de referencia se calculan una vez por carga del
        # modelo y se reutilizan en todos los audios (antes se recalculaban en cada frase).
        try:
            self._qwen_voice_prompt = self.qwen_model.create_voice_clone_prompt(
                ref_audio=str(resolve_path(self.qwen_config.get("ref_audio", ""))),
                ref_text=self.qwen_config.get("ref_text", ""),
                x_vector_only_mode=False,
            )
        except Exception as e:
            logger.warning(f"No se pudo precalcular la voz de referencia: {e}")
            self._qwen_voice_prompt = None
        return True

    def unload_qwen(self) -> bool:
        """Descarga el modelo Qwen-TTS de la memoria RAM."""
        if not self.qwen_model:
            return False
        logger.info("Descargando Qwen-TTS de la memoria para liberar espacio...")
        self.qwen_model = None
        self._qwen_voice_prompt = None
        gc.collect()
        torch = sys.modules.get("torch")
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
        return True

    def release(self):
        """Libera recursos tras una interacción si así está configurado."""
        if self.qwen_unload_after_use:
            self.unload_qwen()

    def _qwen_generate(self, text: str, output_path: Path):
        import soundfile as sf

        if self._qwen_voice_prompt is not None:
            voice_kwargs = {"voice_clone_prompt": self._qwen_voice_prompt}
        else:
            voice_kwargs = {
                "ref_audio": str(resolve_path(self.qwen_config.get("ref_audio", ""))),
                "ref_text": self.qwen_config.get("ref_text", ""),
                "x_vector_only_mode": False,
            }
        wavs, sample_rate = self.qwen_model.generate_voice_clone(
            text=text,
            language=self.qwen_config.get("language", "Spanish"),
            **voice_kwargs,
            **self.qwen_generation,
        )
        sf.write(str(output_path), wavs[0], sample_rate)

    async def _generate_qwen_tts(self, text: str) -> Path | None:
        """Genera audio usando Qwen-TTS (Local, voz personalizada)."""
        # Cargar y generar en un hilo para no bloquear el bot (operación pesada en CPU)
        if not await asyncio.to_thread(self._init_qwen):
            return None

        output_path = self._new_output_path("meka_qwen", ".wav")
        try:
            await asyncio.to_thread(self._qwen_generate, text, output_path)
            logger.info(f"Audio generado con Qwen-TTS: {output_path.name}")
            return output_path
        except Exception as e:
            logger.error(f"Error en Qwen-TTS: {e}")
            output_path.unlink(missing_ok=True)
            return None

    # ------------------------------------------------------------------ Edge-TTS / Piper

    async def _generate_edge_tts(self, text: str) -> Path | None:
        """Genera audio usando Edge-TTS (Online, alta calidad)."""
        output_path = self._new_output_path("meka", ".mp3")
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
            await communicate.save(str(output_path))
            logger.info(f"Audio generado con Edge-TTS: {output_path.name}")
            return output_path
        except Exception as e:
            logger.error(f"Error en Edge-TTS: {e}")
            output_path.unlink(missing_ok=True)
            return None

    async def _generate_piper(self, text: str) -> Path | None:
        """Genera audio usando Piper (Local)."""
        output_path = self._new_output_path("meka", ".wav")
        command = [
            self.piper_path,
            "--model", self.model_path,
            "--output_file", str(output_path),
            "--length_scale", str(self.length_scale),
            "--noise_scale", str(self.noise_scale),
            "--noise_w", str(self.noise_w),
        ]  # fmt: skip
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate(input=text.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error en Piper: {e}")
            return None

        if process.returncode != 0:
            logger.error(f"Error en Piper: {stderr.decode(errors='ignore')}")
            output_path.unlink(missing_ok=True)
            return None
        return output_path


# Instancia global
tts_service = TTSService()
