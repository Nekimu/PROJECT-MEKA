"""Carátula de lo que suena (Spotify, el navegador...): la que el reproductor entrega a Windows.

Se lee **solo cuando cambia la canción** (unos 40 ms, ~150 KB) y se guarda en memoria; la isla
la pide a `GET /v1/system/media/artwork?v=<versión>`. La versión cambia con cada carátula, así
que el cliente puede cachearla sin miedo. Nunca sale del equipo ni se guarda en disco.
"""

import hashlib

from core.logger import setup_logger

logger = setup_logger("System")

MAX_BYTES = 2 * 1024 * 1024  # Una carátula más grande no es una carátula
URL = "/v1/system/media/artwork"


class ArtworkCache:
    def __init__(self):
        self.key: tuple | None = None
        self.data: bytes | None = None
        self.mime = "image/png"
        self.version: str | None = None

    async def update(self, key: tuple, reader) -> str | None:
        """`key` identifica la canción; `reader` es una corrutina que devuelve (bytes, mime).
        Devuelve la URL de la carátula actual (o None si no hay)."""
        if key != self.key:
            self.key, self.data, self.version = key, None, None
            try:
                data, mime = await reader()
            except Exception as e:  # Sin carátula o el reproductor no la da: no pasa nada
                logger.debug(f"Sin carátula: {e}")
                data, mime = None, None
            if data and len(data) <= MAX_BYTES:
                self.data, self.mime = data, mime or "image/png"
                self.version = hashlib.sha1(data).hexdigest()[:12]
        return f"{URL}?v={self.version}" if self.version else None

    def get(self) -> tuple[bytes, str] | None:
        return (self.data, self.mime) if self.data else None


async def read_thumbnail(thumbnail) -> tuple[bytes | None, str | None]:
    """Lee una `IRandomAccessStreamReference` de WinRT (la carátula de SMTC) a bytes."""
    if thumbnail is None:
        return None, None
    from winrt.windows.storage.streams import Buffer, DataReader, InputStreamOptions

    stream = await thumbnail.open_read_async()
    size = min(int(stream.size), MAX_BYTES + 1)
    buffer = Buffer(size)
    await stream.read_async(buffer, size, InputStreamOptions.READ_AHEAD)
    data = bytearray(buffer.length)
    DataReader.from_buffer(buffer).read_bytes(data)
    return bytes(data), stream.content_type or "image/png"
