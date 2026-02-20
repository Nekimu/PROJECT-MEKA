import asyncio
import edge_tts

async def list_voices():
    voices = await edge_tts.VoicesManager.create()
    mx_voices = voices.find(Locale="es-MX")
    for v in mx_voices:
        print(f"Name: {v['Name']}, ShortName: {v['ShortName']}, Gender: {v['Gender']}")

if __name__ == "__main__":
    asyncio.run(list_voices())
