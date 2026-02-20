import ollama
from ollama import Client
from core.config import settings
from core.logger import setup_logger, log_conversation
from ai.prompts import MARIN_KITAGAWA_PROMPT
import re
from core.memory import memory_system

logger = setup_logger("AI_Service")

class AIService:
    def __init__(self):
        ai_config = settings.get("ai", {})
        self.model = ai_config.get("model", "llama3")
        self.host = ai_config.get("base_url", "http://localhost:11434")
        self.system_prompt = MARIN_KITAGAWA_PROMPT
        self.history = [] # Memoria simple en tiempo de ejecución
        
        # Inicializar el cliente con el host específico
        try:
            self.client = Client(host=self.host)
            logger.info(f"Conectado a Ollama en {self.host} con el modelo {self.model}")
        except Exception as e:
            logger.error(f"Error inicializando cliente de Ollama: {e}")
            self.client = None

    def _check_model(self):
        if not self.client: return
        try:
            self.client.show(self.model)
        except ollama.ResponseError:
            logger.warning(f"Modelo {self.model} no encontrado. Intentando descargar...")
            try:
                self.client.pull(self.model)
                logger.info(f"Modelo {self.model} descargado correctamente.")
            except Exception as e:
                logger.error(f"Error descargando el modelo: {e}")

    def check_health(self):
        """Verifica la conectividad con Ollama y el modelo."""
        if not self.client:
            return False
        try:
            self.client.show(self.model)
            return True
        except Exception as e:
            logger.critical(f"Health Check Fallido (Ollama): {e}")
            return False

    def generate_response(self, user_text: str):
        """Genera una respuesta utilizando el cliente de Ollama y la divide en múltiples mensajes."""
        if not self.client:
            return ["¡Waaa! 😵 No puedo conectarme con mi cerebro (Ollama no está disponible)."]

        # Registrar mensaje del usuario en logs y memoria
        log_conversation("User", user_text)
        self.history.append({"role": "user", "content": user_text})
        
        # 1. Detección de persistencia de memoria ("Recuerda esto:")
        memory_trigger = "recuerda esto:"
        if memory_trigger in user_text.lower():
            fact = re.split(memory_trigger, user_text, flags=re.IGNORECASE)[-1].strip()
            if fact:
                memory_system.add_fact(fact)
        
        # 2. Búsqueda de recuerdos relevantes si el usuario pregunta
        retrieval_triggers = ["recuerdas", "te acuerdas", "sabes algo de", "que me dijiste de"]
        relevant_context = ""
        if any(t in user_text.lower() for t in retrieval_triggers):
            memories = memory_system.search_memories(user_text)
            if memories:
                relevant_context = "\n\n[SISTEMA: Recuerdos relevantes encontrados en tu memoria persistente:\n" + \
                                  "\n".join([f"- {m}" for m in memories]) + "]"

        messages = [{"role": "system", "content": self.system_prompt + relevant_context}] + self.history

        try:
            # Optimización de latencia y parámetros
            options = {
                "temperature": 0.8,
                "num_predict": 512, 
                "top_k": 40,
                "top_p": 0.9,
                "repeat_penalty": 1.2, # Penaliza la repetición de palabras/frases
                "repeat_last_n": 64,   # Cuánto atrás mirar para penalizar
            }

            import time
            start_time = time.time()

            response = self.client.chat(
                model=self.model, 
                messages=messages,
                options=options,
                keep_alive=0 # Liberar RAM inmediatamente después de responder
            )
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            raw_text = response['message']['content']
            
            # Registrar respuesta completa en memoria
            self.history.append({"role": "assistant", "content": raw_text})
            
            # Dividir respuesta en múltiples mensajes según el delimitador --- o saltos de línea
            bot_messages = [msg.strip() for msg in raw_text.split("---") if msg.strip()]
            
            # Si no usó ---, intentar dividir por saltos de línea o puntos si es muy largo
            if len(bot_messages) == 1 and len(raw_text) > 100:
                # Intentar dividir por saltos de línea primero
                parts = [msg.strip() for msg in raw_text.split("\n") if msg.strip()]
                if len(parts) > 1:
                    bot_messages = parts
                else:
                    # Si sigue siendo un solo bloque, intentar dividir por puntos seguidos de espacio
                    bot_messages = [msg.strip() for msg in re.split(r'(?<=[.!?])\s+', raw_text) if msg.strip()]

            # Log de la respuesta y latencia
            logger.info(f"Respuesta generada en {latency_ms}ms | Modelo: {self.model}")
            log_conversation("Marin", f"({latency_ms}ms) " + " | ".join(bot_messages))
            
            # Limitar historial
            if len(self.history) > 20:
                self.history = self.history[-20:]
                
            return bot_messages

        except Exception as e:
            logger.error(f"Error generando respuesta con Ollama: {e}")
            return [f"¡Waaa! 😵 Algo pasó... {str(e)}"]

    def unload_model(self):
        """Descarga el modelo de la memoria de Ollama."""
        if not self.client: return
        try:
            logger.info(f"Descargando modelo {self.model} de memoria...")
            # Enviar keep_alive: 0 descarga el modelo
            self.client.chat(model=self.model, messages=[], keep_alive=0)
        except Exception as e:
            logger.error(f"Error al descargar el modelo: {e}")


    def generate_multimodal_response(self, user_text: str, image_path: str):
        """Analiza una imagen o documento utilizando la capacidad multimodal de Gemma 3."""
        if not self.client:
            return "¡Waaa! 😵 No puedo ver nada porque mi cerebro (Ollama) está desconectado."

        # Registrar mensaje multimodal
        log_conversation("User (Multimodal)", f"{user_text} [Image: {image_path}]")
        self.history.append({"role": "user", "content": user_text, "images": [image_path]})

        # Prompt específico para análisis de documentos/imágenes
        # Forzamos que NO pida audio ni nada extra, solo análisis.
        system_instruction = (
            "Eres Marin Kitagawa. El usuario te ha enviado una imagen o documento para que lo analices. "
            "Describe lo que ves con tu personalidad alegre y coqueta, pero sé útil y precisa con la información. "
            "NO uses herramientas de audio ni generes tags como [AUDIO], solo texto."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_text, "images": [image_path]}
        ]

        try:
            import time
            start_time = time.time()
            
            logger.info("Enviando imagen a Gemma 3 para análisis...")
            
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.6, "num_predict": 1024}, # Menor temperatura para precisión
                keep_alive=0 # IMPORTANTE: Liberar recursos inmediatamente
            )

            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            raw_text = response['message']['content']
            
            # Registrar respuesta completa para logs
            self.history.append({"role": "assistant", "content": raw_text})
            
            logger.info(f"Análisis multimodal completado en {latency_ms}ms")
            log_conversation("Marin (Vision)", f"({latency_ms}ms) {raw_text}")
            
            # Dividir respuesta en burbujas por párrafos
            # Usamos doble salto de línea como separador natural
            bot_messages = [msg.strip() for msg in raw_text.split("\n\n") if msg.strip()]
            
            # Si no hay párrafos claros, intentar dividir por oraciones largas si excede ciertos caracteres,
            # pero por ahora, una burbuja por párrafo es lo estándar.
            if not bot_messages:
                bot_messages = [raw_text] if raw_text.strip() else ["¡Ups! No se me ocurre nada..."]

            # Limpieza de historial
            if len(self.history) > 10:
                self.history = self.history[-10:]

            return bot_messages

        except Exception as e:
            logger.error(f"Error en análisis multimodal: {e}")
            return [f"¡Uy! No pude ver bien la imagen... me dio un error: {str(e)}"]

# Instancia global
ai_service = AIService()
