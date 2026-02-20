import asyncio
from ai.tts import tts_service
import os

async def test_marin_voice():
    engine = tts_service.engine
    print(f"--- Probando Voz de Marin con {engine} ---")
    test_text = "¡Hola! Soy Marin. ¿Te gusta cómo suena mi voz?"
    
    print(f"Generando audio para: '{test_text}'...")
    audio_path = await tts_service.generate_audio(test_text)
    
    if audio_path and os.path.exists(audio_path):
        print(f"EXITO: Audio generado en: {audio_path}")
        print("Puedes abrir este archivo para escuchar la voz.")
    else:
        print("❌ Error: No se pudo generar el audio.")

if __name__ == "__main__":
    asyncio.run(test_marin_voice())
