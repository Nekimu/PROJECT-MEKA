"""Lista las voces disponibles de edge-tts para elegir `tts.voice` en config.yml.

Uso:  python -m scripts.list_edge_voices          # todas las voces en español
      python -m scripts.list_edge_voices es-MX    # solo un locale concreto
"""

import asyncio
import sys

import edge_tts


async def list_voices(locale: str | None):
    voices = await edge_tts.VoicesManager.create()
    found = voices.find(Locale=locale) if locale else voices.find(Language="es")
    for v in sorted(found, key=lambda v: v["ShortName"]):
        print(f"Locale: {v['Locale']:7}  ShortName: {v['ShortName']:28}  Gender: {v['Gender']}")


if __name__ == "__main__":
    asyncio.run(list_voices(sys.argv[1] if len(sys.argv) > 1 else None))
