import whisper
import os
from core.logger import setup_logger

logger = setup_logger("STT_Service")

class STTService:
    def __init__(self, model_size="base"):
        """
        Inicializa el servicio de STT.
        El modelo se cargará la primera vez que se necesite (Lazy Loading).
        Modelos disponibles: tiny, base, small, medium, large
        """
        self.model_size = model_size
        self.model = None
        logger.info(f"Servicio STT inicializado (Lazy Loading: '{model_size}')")

    def _load_model(self):
        """Carga el modelo de Whisper bajo demanda."""
        if self.model: return True
        try:
            logger.info(f"Cargando modelo Whisper '{self.model_size}' en memoria...")
            self.model = whisper.load_model(self.model_size)
            logger.info("Modelo Whisper cargado correctamente.")
            return True
        except Exception as e:
            logger.critical(f"Error fatal cargando Whisper: {e}")
            self.model = None
            return False

    def check_health(self):
        """Verifica si el servicio está listo para cargar (no carga el modelo aún)."""
        # En lazy loading, asumimos salud ok si no ha fallado antes, 
        # o podríamos intentar un import simple.
        return True

    def transcribe(self, audio_path):
        """Transcribe un archivo de audio a texto."""
        if not self.model:
            if not self._load_model():
                return "Error: No se pudo cargar el modelo de transcripción."
            
        try:
            logger.info(f"Transcribiendo audio: {audio_path}")
            result = self.model.transcribe(audio_path, language="es")
            text = result.get("text", "").strip()
            logger.info(f"Transcripción completada: {text}")
            return text
        except Exception as e:
            logger.error(f"Error en la transcripción: {e}")
            return f"Error al transcribir: {str(e)}"

    def unload_model(self):
        """Libera el modelo de Whisper de la RAM."""
        if self.model:
            import gc
            import torch
            logger.info("Descargando Whisper de la memoria...")
            del self.model
            self.model = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return True
        return False

# Instancia global (usamos 'base' para un equilibrio entre velocidad y precisión)
stt_service = STTService(model_size="base")
