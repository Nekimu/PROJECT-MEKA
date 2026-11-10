"""Genera un audio de prueba con el motor TTS configurado en config.yml.

Uso (desde la raíz del proyecto):  python -m scripts.tts_smoke_test ["texto opcional"]
"""

import asyncio
import sys

from ai.tts import TTSService
from core.config import settings
from core.persona import load_active_persona

persona = load_active_persona()
tts_service = TTSService(settings, voice=persona.voice)


async def try_voice(text: str):
    print(f"--- Probando la voz de {persona.name} con {tts_service.engine} ---")
    print(f"Generando audio para: '{text}'...")
    audio_path = await tts_service.generate_audio(text)
    tts_service.release()

    if audio_path and audio_path.exists():
        print(f"✅ Audio generado en: {audio_path}")
        print("Puedes abrir este archivo para escuchar la voz.")
    else:
        print("❌ Error: No se pudo generar el audio.")


if __name__ == "__main__":
    sample = " ".join(sys.argv[1:]) or f"¡Hola! Soy {persona.name}. ¿Te gusta cómo suena mi voz?"
    asyncio.run(try_voice(sample))
