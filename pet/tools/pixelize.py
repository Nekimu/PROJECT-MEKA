"""Convierte sprites o stickers en Pixel Art nítido (64x64 -> WebP lossless con contorno blanco).

Basado en el pipeline de referencia de `Stickers e Imagenes` (D.Va & Clawd Pixel Packs):
- Reduce a rejilla lógica (p. ej. 64x64 px) con cuantización de paleta para máximo rendimiento.
- Añade contorno blanco pixel-art de 1 px alrededor del canal alfa.
- Escala con `Resampling.NEAREST` a 256x256 o 512x512 manteniendo bordes de píxel exactos.
- Soporta tanto imágenes estáticas como WebP/GIF animados fotograma a fotograma.

Uso:
    python pet/tools/pixelize.py entrada.webp salida.webp [--grid 64] [--scale 256] [--colors 24]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

WHITE = (255, 255, 255, 255)


def add_white_outline(canvas: np.ndarray, thickness: int = 1) -> np.ndarray:
    """Agrega un contorno blanco de `thickness` píxeles alrededor de los píxeles opacos."""
    alpha = canvas[:, :, 3] > 0
    dilated = alpha.copy()
    for _ in range(thickness):
        up = np.pad(dilated[1:, :], ((0, 1), (0, 0)), mode="constant")
        down = np.pad(dilated[:-1, :], ((1, 0), (0, 0)), mode="constant")
        left = np.pad(dilated[:, 1:], ((0, 0), (0, 1)), mode="constant")
        right = np.pad(dilated[:, :-1], ((0, 0), (1, 0)), mode="constant")
        ul = np.pad(dilated[1:, 1:], ((0, 1), (0, 1)), mode="constant")
        ur = np.pad(dilated[1:, :-1], ((0, 1), (1, 0)), mode="constant")
        dl = np.pad(dilated[:-1, 1:], ((1, 0), (0, 1)), mode="constant")
        dr = np.pad(dilated[:-1, :-1], ((1, 0), (1, 0)), mode="constant")
        dilated = dilated | up | down | left | right | ul | ur | dl | dr

    outline_mask = dilated & (~alpha)
    out = canvas.copy()
    out[outline_mask] = WHITE
    return out


def pixelize_frame(
    frame: Image.Image, grid: int = 64, scale: int = 256, step: int = 32, outline: int = 1
) -> Image.Image:
    rgba = frame.convert("RGBA")
    small = rgba.resize((grid, grid), resample=Image.Resampling.BILINEAR)
    arr = np.asarray(small, dtype=np.uint8).copy()

    # Umbral de alfa nítido y reducción de paleta RGB
    alpha = arr[:, :, 3] >= 110
    arr[:, :, 3] = np.where(alpha, 255, 0)
    arr[:, :, :3] = np.clip(
        np.round(arr[:, :, :3].astype(np.float32) / step) * step, 0, 255
    ).astype(np.uint8)
    arr[~alpha] = (0, 0, 0, 0)

    if outline > 0:
        arr = add_white_outline(arr, thickness=outline)

    pixel_img = Image.fromarray(arr, mode="RGBA")
    return pixel_img.resize((scale, scale), resample=Image.Resampling.NEAREST)


def pixelize(
    src: Path, dst: Path, grid: int = 64, scale: int = 256, step: int = 32, outline: int = 1
) -> tuple[int, int, int]:
    im = Image.open(src)
    frames = [
        pixelize_frame(f.copy(), grid=grid, scale=scale, step=step, outline=outline)
        for f in ImageSequence.Iterator(im)
    ]
    duration = im.info.get("duration", 110)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if len(frames) > 1:
        frames[0].save(
            dst,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            lossless=True,
            quality=100,
            method=4,
        )
    else:
        frames[0].save(dst, format="WEBP", lossless=True, quality=100, method=6)
    return scale, scale, len(frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("src", type=Path, help="Imagen o WebP/GIF de entrada")
    parser.add_argument("dst", type=Path, help="Ruta de salida (.webp)")
    parser.add_argument("--grid", type=int, default=64, help="Resolución lógica del pixel art")
    parser.add_argument("--scale", type=int, default=256, help="Tamaño final en píxeles")
    parser.add_argument("--step", type=int, default=32, help="Paso de cuantización RGB")
    parser.add_argument("--outline", type=int, default=1, help="Grosor del borde blanco en píxeles")
    args = parser.parse_args()
    w, h, n = pixelize(args.src, args.dst, args.grid, args.scale, args.step, args.outline)
    print(f"{args.dst} ({w}x{h}, {n} frame(s))")


if __name__ == "__main__":
    main()
