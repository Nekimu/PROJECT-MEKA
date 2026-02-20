import asyncio
import edge_tts

async def list_voices():
    voices = await edge_tts.VoicesManager.create()
    all_voices = voices.find(Language="es")
    for v in all_voices:
        print(f"Locale: {v['Locale']}, ShortName: {v['ShortName']}, Gender: {v['Gender']}")

if __name__ == "__main__":
    asyncio.run(list_voices())
