import subprocess
import os
import uuid
import asyncio
from core.config import settings
from core.logger import setup_logger

logger = setup_logger("TTS_Service")

class TTSService:
    def __init__(self):
        tts_config = settings.get("tts", {})
        self.enabled = tts_config.get("enabled", False)
        self.engine = tts_config.get("engine", "piper")
        
        # Piper config
        self.piper_path = tts_config.get("piper_path", "piper")
        self.model_path = tts_config.get("model_path", "")
        self.length_scale = tts_config.get("length_scale", 1.0)
        self.noise_scale = tts_config.get("noise_scale", 0.667)
        self.noise_w = tts_config.get("noise_w", 0.8)
        
        # Edge-TTS config
        self.voice = tts_config.get("voice", "es-MX-DaliaNeural")
        self.rate = tts_config.get("rate", "+0%")
        self.pitch = tts_config.get("pitch", "+0Hz")
        
        # Qwen-TTS config
        self.qwen_config = tts_config.get("qwen", {})
        self.qwen_model = None
        
        if self.enabled:
            logger.info(f"TTS Service cargado con el motor: {self.engine}")
            # No cargamos Qwen aquí para ahorrar RAM al inicio
            
    def check_health(self):
        """Verifica que el motor TTS seleccionado esté operativo."""
        if not self.enabled: return True
        
        try:
            if self.engine == "piper":
                if not os.path.exists(self.piper_path):
                     logger.critical(f"Piper binary not found at {self.piper_path}")
                     return False
                if not os.path.exists(self.model_path):
                     logger.critical(f"Piper model not found at {self.model_path}")
                     return False
            elif self.engine == "qwen-tts":
                # Verificar dependencias crÃ­ticas
                try:
                    import torch
                    import qwen_tts
                except ImportError as e:
                    logger.critical(f"Dependencias de Qwen-TTS faltantes: {e}")
                    return False
            elif self.engine == "edge-tts":
                try:
                    import edge_tts
                except ImportError as e:
                    logger.critical(f"Librería edge-tts faltante: {e}")
                    return False
            
            return True
        except Exception as e:
            logger.critical(f"TTS Health Check Fallido: {e}")
            return False

    async def generate_audio(self, text, output_dir="temp_audio"):
        """Genera un archivo de audio (.wav o .mp3) a partir de un texto."""
        if not self.enabled:
            return None
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Limpiar texto: 
        # 1. Removemos los tags multimedia
        import re
        text_no_tags = re.sub(r'\[STICKER\]|\[GIF\]|\[AUDIO\]', '', text, flags=re.IGNORECASE).strip()
        
        # 2. Removemos descripciones de rol entre paréntesis o asteriscos (ej: (nerviosa) o *sonríe*)
        text_no_desc = re.sub(r'\(.*?\)', '', text_no_tags) # Quita (...)
        text_no_desc = re.sub(r'\*.*?\*', '', text_no_desc) # Quita *...*
        
        # 3. Removemos Emojis y caracteres especiales, mantenemos puntuación expresiva
        clean_text = re.sub(r'[^\w\s.,!¡?¿áéíóúÁÉÍÓÚñÑüÜ:;\-\(\)\"\']', '', text_no_desc)
        
        # 4. Normalizar espacios
        clean_text = " ".join(clean_text.split()).strip()

        if not clean_text:
            return None

        if self.engine == "edge-tts":
            return await self._generate_edge_tts(clean_text, output_dir)
        elif self.engine == "qwen-tts":
            return await self._generate_qwen_tts(clean_text, output_dir)
        else:
            return await self._generate_piper(clean_text, output_dir)

    def _init_qwen(self):
        """Inicializa el modelo Qwen-TTS con gestión de memoria."""
        if self.qwen_model: return True
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
            import gc

            model_id = self.qwen_config.get("model_id", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
            device = self.qwen_config.get("device", "cpu")
            
            logger.info(f"Cargando modelo Qwen-TTS ({model_id}) en {device} por primera vez...")
            
            self.qwen_model = Qwen3TTSModel.from_pretrained(
                model_id,
                device_map=device,
                dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            logger.info("Modelo Qwen-TTS cargado correctamente.")
            return True
        except Exception as e:
            logger.error(f"Error cargando Qwen-TTS: {e}")
            return False

    def unload_qwen(self):
        """Descarga el modelo Qwen-TTS de la memoria RAM."""
        if self.qwen_model:
            import torch
            import gc
            logger.info("Descargando Qwen-TTS de la memoria para liberar espacio...")
            del self.qwen_model
            self.qwen_model = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return True
        return False

    async def _generate_qwen_tts(self, text, output_dir):
        """Genera audio usando Qwen-TTS (Local, voz personalizada)."""
        if not self.qwen_model:
            self._init_qwen()
            if not self.qwen_model: return None

        import soundfile as sf
        import gc
        import torch

        filename = f"marin_qwen_{uuid.uuid4().hex}.wav"
        output_path = os.path.join(output_dir, filename)

        try:
            # Ejecutar en un thread para no bloquear el bot (operación pesada en CPU)
            def _generate():
                ref_audio = [self.qwen_config.get("ref_audio", "")]
                ref_text = [self.qwen_config.get("ref_text", "")]
                
                # Tuning básico para estabilidad
                gen_kwargs = dict(
                    max_new_tokens=2048,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95,
                    temperature=0.8,
                    repetition_penalty=1.1,
                )

                wavs, sr = self.qwen_model.generate_voice_clone(
                    text=text,
                    language=self.qwen_config.get("language", "Spanish"),
                    ref_audio=ref_audio,
                    ref_text=ref_text,
                    x_vector_only_mode=False,
                    **gen_kwargs
                )
                sf.write(output_path, wavs[0], sr)
                
                # Limpieza agresiva de memoria (importante para 16GB RAM)
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
            await asyncio.to_thread(_generate)
            logger.info(f"Audio generado con Qwen-TTS: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error en Qwen-TTS: {e}")
            return None

    async def _generate_edge_tts(self, text, output_dir):
        """Genera audio usando Edge-TTS (Online, alta calidad)."""
        import edge_tts
        
        filename = f"marin_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(output_dir, filename)
        
        try:
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
            await communicate.save(output_path)
            logger.info(f"Audio generado con Edge-TTS: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error en Edge-TTS: {e}")
            return None

    async def _generate_piper(self, text, output_dir):
        """Genera audio usando Piper (Local)."""
        filename = f"marin_{uuid.uuid4().hex}.wav"
        output_path = os.path.join(output_dir, filename)
        
        try:
            # Usar asyncio para no bloquear el loop del bot
            command = [
                self.piper_path,
                "--model", self.model_path,
                "--output_file", output_path,
                "--length_scale", str(self.length_scale),
                "--noise_scale", str(self.noise_scale),
                "--noise_w", str(self.noise_w)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode('utf-8'))
            
            if process.returncode != 0:
                logger.error(f"Error en Piper: {stderr.decode()}")
                return None
            
            return output_path
        except Exception as e:
            logger.error(f"Error en Piper: {e}")
            return None

# Instancia global
tts_service = TTSService()
