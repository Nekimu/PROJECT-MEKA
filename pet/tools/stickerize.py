"""Convierte stickers con fondo liso (p. ej. generados con Gemini) en WebP con transparencia.

Recorta el fondo conectado con los bordes de la imagen, suaviza el contorno sin halos
oscuros y reduce el tamaño para usarlos como sprites de la mascota.

Uso:
    pip install pillow numpy
    python pet/tools/stickerize.py entrada.jpg salida.webp [--size 512]
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HARD = 28  # Distancia de color por debajo de la cual el píxel es fondo seguro
SOFT = 90  # A partir de esta distancia el píxel es 100 % sticker


def stickerize(src: Path, dst: Path, size: int = 512) -> tuple[int, int]:
    rgb = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32)
    border = np.concatenate([rgb[:4].reshape(-1, 3), rgb[-4:].reshape(-1, 3),
                             rgb[:, :4].reshape(-1, 3), rgb[:, -4:].reshape(-1, 3)])  # fmt: skip
    background = np.median(border, axis=0)
    distance = np.linalg.norm(rgb - background, axis=2)

    # Región de fondo: píxeles parecidos al fondo *conectados con el borde*
    # (un píxel oscuro dentro del sticker, como el pelo, no se toca).
    candidate = Image.fromarray(np.where(distance < SOFT, 255, 0).astype(np.uint8))
    padded = Image.new("L", (candidate.width + 2, candidate.height + 2), 255)
    padded.paste(candidate, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    region = np.asarray(padded)[1:-1, 1:-1] == 128

    alpha = np.ones(distance.shape, dtype=np.float32)
    ramp = np.clip((distance - HARD) / (SOFT - HARD), 0.0, 1.0)
    alpha[region] = ramp[region]

    # Quitar el tinte del fondo en el contorno semitransparente (evita halos oscuros)
    edge = (alpha > 0) & (alpha < 1)
    a = alpha[edge][:, None]
    rgb[edge] = np.clip((rgb[edge] - (1 - a) * background) / a, 0, 255)

    rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    image = Image.fromarray(rgba, "RGBA")
    image = image.crop(image.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
    image.thumbnail((size, size), Image.LANCZOS)  # Pillow premultiplica el alfa al escalar
    dst.parent.mkdir(parents=True, exist_ok=True)
    image.save(dst, "WEBP", quality=88, method=6)
    return image.size


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    parser.add_argument("--size", type=int, default=512, help="Lado máximo en píxeles")
    args = parser.parse_args()
    width, height = stickerize(args.src, args.dst, args.size)
    print(f"{args.dst} ({width}x{height})")


if __name__ == "__main__":
    main()
