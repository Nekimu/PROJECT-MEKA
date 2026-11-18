"""Estudio de procesamiento de avatares Chibi HD animados para MEKA.

Procesa los paquetes de 12 fotogramas PNG (512x512) en `assets/`:
- Limpia el canal alfa y recorta el borde blanco/gris tipo die-cut sticker mediante
  detección cromática e inundación conectada al borde (`ImageDraw.floodfill`),
  preservando los detalles blancos internos y los accesorios flotantes (corazones, destellos).
- Suaviza el contorno alfa con anti-aliasing Gaussiano y descontamina el halo blanco.
- Realza la nitidez del trazo anime con `UnsharpMask` y reescalado `LANCZOS`.
- Genera los 16 estados WebP animados (`idle`, `standby`, `greet`, `happy`, `love`,
  `surprise`, `sad`, `sigh`, `working`, `thinking`, `sleeping`, `eating`, `eating2`,
  `error`, `celebrate`, `dance`) en `pet/web/skins/<id>/`.

Uso:
    python pet/tools/chibi_studio.py [--size 320] [--skin hana]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = ROOT / "assets"
SKINS_DIR = ROOT / "pet" / "web" / "skins"

CHARACTER_PACKS: dict[str, tuple[str, str]] = {
    "hana": ("Hana_Song_DVa_Chibi_12Frames_Web_Go", "Hana"),
    "2b": ("2B_NieR_Automata_Chibi_12Frames_Web_Go", "2B"),
    "kiriko": ("Kiriko_Overwatch2_Chibi_12Frames_Web_Go", "Kiriko"),
    "marin": ("Marin_Kitagawa_Chibi_12Frames_Web_Go", "Marin"),
    "yotsuba": ("Yotsuba_Nakano_Chibi_12Frames_Web_Go", "Yotsuba"),
}


@dataclass(frozen=True)
class FrameStep:
    """Fotograma dentro de una secuencia de estado con micro-transformación cinemática."""

    index: int
    dx: int = 0
    dy: int = 0
    angle: float = 0.0


@dataclass(frozen=True)
class StateSpec:
    """Especificación de animación para un estado de la mascota."""

    duration: int
    steps: tuple[FrameStep, ...]


STATE_SPECS: dict[str, StateSpec] = {
    "idle": StateSpec(
        duration=220,
        steps=(
            FrameStep(0, 0, 0, 0.0),
            FrameStep(0, 0, 0, 0.15),
            FrameStep(0, 0, -1, 0.25),
            FrameStep(0, 0, -2, 0.25),
            FrameStep(0, 0, -1, 0.15),
            FrameStep(0, 0, 0, 0.0),
            FrameStep(2, 0, 0, 0.0),
            FrameStep(11, 0, 0, 0.0),
            FrameStep(11, 0, -1, -0.15),
            FrameStep(11, 0, -2, -0.25),
            FrameStep(11, 0, -2, -0.15),
            FrameStep(11, 0, -1, 0.0),
            FrameStep(11, 0, 0, 0.0),
            FrameStep(0, 0, -1, 0.15),
            FrameStep(0, 0, -1, 0.0),
            FrameStep(0, 0, 0, 0.0),
        ),
    ),
    "standby": StateSpec(
        duration=240,
        steps=(
            FrameStep(11, 0, 0, 0.0),
            FrameStep(11, 0, 0, 0.2),
            FrameStep(11, 0, -1, 0.25),
            FrameStep(11, 0, -2, 0.2),
            FrameStep(11, 0, -1, 0.0),
            FrameStep(11, 0, 0, 0.0),
            FrameStep(2, 0, 0, 0.0),
            FrameStep(8, 0, 0, 0.0),
            FrameStep(8, 0, -1, -0.2),
            FrameStep(8, 0, -2, -0.25),
            FrameStep(8, 0, -1, -0.2),
            FrameStep(8, 0, 0, 0.0),
            FrameStep(11, 0, 0, 0.0),
            FrameStep(11, 0, -1, 0.15),
            FrameStep(11, 0, -1, 0.0),
            FrameStep(11, 0, 0, 0.0),
        ),
    ),
    "greet": StateSpec(
        duration=200,
        steps=(
            FrameStep(4, 0, 0, -0.3),
            FrameStep(4, 0, -1, -0.5),
            FrameStep(4, 0, -2, 0.0),
            FrameStep(4, 0, -1, 0.5),
            FrameStep(4, 0, 0, 0.2),
            FrameStep(5, 0, 0, 0.2),
            FrameStep(5, 0, -1, 0.5),
            FrameStep(5, 0, -2, 0.25),
            FrameStep(5, 0, -1, 0.0),
            FrameStep(5, 0, 0, 0.0),
            FrameStep(0, 0, 0, 0.0),
            FrameStep(0, 0, -1, -0.2),
            FrameStep(0, 0, -1, 0.0),
            FrameStep(0, 0, 0, 0.0),
        ),
    ),
    "happy": StateSpec(
        duration=200,
        steps=(
            FrameStep(3, 0, 0, -0.3),
            FrameStep(3, 0, -1, -0.5),
            FrameStep(3, 0, -2, 0.0),
            FrameStep(3, 0, -3, 0.4),
            FrameStep(3, 0, -2, 0.5),
            FrameStep(3, 0, -1, 0.2),
            FrameStep(3, 0, 0, 0.0),
            FrameStep(8, 0, 0, 0.2),
            FrameStep(8, 0, -1, 0.4),
            FrameStep(8, 0, -2, 0.0),
            FrameStep(8, 0, -2, -0.4),
            FrameStep(8, 0, -1, -0.5),
            FrameStep(8, 0, 0, -0.2),
            FrameStep(8, 0, 0, 0.0),
        ),
    ),
    "love": StateSpec(
        duration=210,
        steps=(
            FrameStep(1, 0, 0, 0.0),
            FrameStep(1, 0, -1, -0.3),
            FrameStep(1, 0, -2, -0.4),
            FrameStep(1, 0, -2, 0.0),
            FrameStep(1, 0, -1, 0.3),
            FrameStep(1, 0, 0, 0.2),
            FrameStep(5, 0, 0, 0.0),
            FrameStep(5, 0, -1, 0.3),
            FrameStep(5, 0, -2, 0.4),
            FrameStep(5, 0, -2, 0.0),
            FrameStep(5, 0, -1, -0.3),
            FrameStep(5, 0, 0, 0.0),
        ),
    ),
    "surprise": StateSpec(
        duration=190,
        steps=(
            FrameStep(9, 0, -3, -0.4),
            FrameStep(9, 0, -4, 0.3),
            FrameStep(9, 0, -2, 0.0),
            FrameStep(9, 0, -1, -0.2),
            FrameStep(9, 0, 0, 0.0),
            FrameStep(9, 0, -1, 0.2),
            FrameStep(7, 0, -2, -0.5),
            FrameStep(7, 0, -3, 0.4),
            FrameStep(7, 0, -2, 0.0),
            FrameStep(7, 0, -1, -0.2),
            FrameStep(9, 0, -1, 0.2),
            FrameStep(9, 0, -2, 0.0),
            FrameStep(9, 0, -1, -0.2),
            FrameStep(9, 0, 0, 0.0),
        ),
    ),
    "sad": StateSpec(
        duration=260,
        steps=(
            FrameStep(10, 0, 2, 0.0),
            FrameStep(10, 0, 2, -0.25),
            FrameStep(10, 0, 3, -0.4),
            FrameStep(10, 0, 4, -0.25),
            FrameStep(10, 0, 4, 0.0),
            FrameStep(10, 0, 3, 0.25),
            FrameStep(10, 0, 3, 0.0),
            FrameStep(2, 0, 3, 0.25),
            FrameStep(2, 0, 4, 0.3),
            FrameStep(2, 0, 4, 0.0),
            FrameStep(2, 0, 3, -0.2),
            FrameStep(2, 0, 2, 0.0),
        ),
    ),
    "sigh": StateSpec(
        duration=280,
        steps=(
            FrameStep(2, 0, 0, 0.0),
            FrameStep(2, 0, -1, -0.25),
            FrameStep(2, 0, 0, -0.2),
            FrameStep(2, 0, 1, 0.0),
            FrameStep(2, 0, 2, 0.2),
            FrameStep(2, 0, 3, 0.25),
            FrameStep(2, 0, 2, 0.0),
            FrameStep(10, 0, 2, 0.0),
            FrameStep(10, 0, 2, -0.25),
            FrameStep(10, 0, 1, -0.2),
            FrameStep(10, 0, 1, 0.0),
            FrameStep(10, 0, 0, 0.0),
        ),
    ),
    "working": StateSpec(
        duration=190,
        steps=(
            FrameStep(0, 0, 0, 0.0),
            FrameStep(0, 0, -1, -0.25),
            FrameStep(0, 0, -1, -0.35),
            FrameStep(0, 0, 0, -0.2),
            FrameStep(0, 0, 0, 0.0),
            FrameStep(11, 0, 0, 0.0),
            FrameStep(11, 0, -1, 0.25),
            FrameStep(11, 0, -2, 0.35),
            FrameStep(11, 0, -1, 0.2),
            FrameStep(7, 0, -1, -0.3),
            FrameStep(7, 0, -2, -0.4),
            FrameStep(7, 0, -2, 0.0),
            FrameStep(7, 0, -1, 0.3),
            FrameStep(7, 0, 0, 0.0),
        ),
    ),
    "thinking": StateSpec(
        duration=250,
        steps=(
            FrameStep(10, 0, 0, -0.3),
            FrameStep(10, 0, 0, -0.5),
            FrameStep(10, 0, 1, -0.6),
            FrameStep(10, 0, 1, -0.5),
            FrameStep(10, 0, 0, -0.25),
            FrameStep(10, 0, 0, 0.0),
            FrameStep(2, 0, 0, 0.0),
            FrameStep(2, 0, 1, 0.25),
            FrameStep(2, 0, 1, 0.3),
            FrameStep(2, 0, 0, 0.15),
            FrameStep(1, 0, 0, 0.25),
            FrameStep(1, 0, -1, 0.4),
            FrameStep(1, 0, -1, 0.2),
            FrameStep(1, 0, 0, 0.0),
        ),
    ),
    "sleeping": StateSpec(
        duration=310,
        steps=(
            FrameStep(2, 0, 0, -0.3),
            FrameStep(2, 0, -1, -0.4),
            FrameStep(2, 0, -2, -0.3),
            FrameStep(2, 0, -2, 0.0),
            FrameStep(2, 0, -1, 0.2),
            FrameStep(2, 0, 0, 0.3),
            FrameStep(2, 0, 1, 0.4),
            FrameStep(2, 0, 2, 0.3),
            FrameStep(2, 0, 3, 0.1),
            FrameStep(2, 0, 3, -0.1),
            FrameStep(2, 0, 2, -0.25),
            FrameStep(2, 0, 1, -0.3),
        ),
    ),
    "eating": StateSpec(
        duration=195,
        steps=(
            FrameStep(9, 0, 0, -0.3),
            FrameStep(9, 0, -2, -0.5),
            FrameStep(9, 0, -2, 0.0),
            FrameStep(9, 0, -1, 0.4),
            FrameStep(9, 0, 0, 0.2),
            FrameStep(3, 0, 0, 0.0),
            FrameStep(3, 0, -1, -0.4),
            FrameStep(3, 0, -2, 0.4),
            FrameStep(3, 0, -1, 0.2),
            FrameStep(8, 0, 0, 0.0),
            FrameStep(8, 0, 1, -0.25),
            FrameStep(8, 0, 0, 0.25),
            FrameStep(8, 0, -1, 0.0),
            FrameStep(8, 0, 0, 0.0),
        ),
    ),
    "eating2": StateSpec(
        duration=200,
        steps=(
            FrameStep(1, 0, 0, -0.25),
            FrameStep(1, 0, -1, -0.4),
            FrameStep(1, 0, -2, -0.2),
            FrameStep(1, 0, -1, 0.2),
            FrameStep(1, 0, 0, 0.0),
            FrameStep(9, 0, 0, 0.25),
            FrameStep(9, 0, -2, 0.5),
            FrameStep(9, 0, -3, 0.0),
            FrameStep(9, 0, -1, -0.3),
            FrameStep(9, 0, 0, 0.0),
            FrameStep(8, 0, 0, 0.0),
            FrameStep(8, 0, -1, 0.3),
            FrameStep(8, 0, -1, -0.2),
            FrameStep(8, 0, 0, 0.0),
        ),
    ),
    "error": StateSpec(
        duration=185,
        steps=(
            FrameStep(9, 0, 0, -0.8),
            FrameStep(9, -1, -2, 0.8),
            FrameStep(9, 1, -1, -0.6),
            FrameStep(9, -1, 0, 0.5),
            FrameStep(9, 0, 0, 0.0),
            FrameStep(7, -1, -1, -0.6),
            FrameStep(7, 1, -2, 0.6),
            FrameStep(7, 0, -1, -0.4),
            FrameStep(7, 0, 0, 0.0),
            FrameStep(10, 0, 0, -0.3),
            FrameStep(10, 0, 1, -0.4),
            FrameStep(10, 0, 2, -0.2),
            FrameStep(10, 0, 1, 0.2),
            FrameStep(10, 0, 0, 0.0),
        ),
    ),
    "celebrate": StateSpec(
        duration=190,
        steps=(
            FrameStep(6, 0, 0, -0.5),
            FrameStep(6, 0, -2, -0.8),
            FrameStep(6, 0, -4, 0.0),
            FrameStep(6, 0, -3, 0.8),
            FrameStep(6, 0, -1, 0.4),
            FrameStep(7, 0, -1, 0.4),
            FrameStep(7, 0, -3, 0.7),
            FrameStep(7, 0, -4, 0.0),
            FrameStep(7, 0, -2, -0.7),
            FrameStep(7, 0, 0, -0.3),
            FrameStep(5, 0, 0, -0.3),
            FrameStep(5, 0, -2, 0.3),
            FrameStep(5, 0, -2, 0.2),
            FrameStep(5, 0, 0, 0.0),
        ),
    ),
    "dance": StateSpec(
        duration=200,
        steps=(
            FrameStep(3, -1, 0, -0.6),
            FrameStep(3, -1, -2, -0.4),
            FrameStep(3, 0, -3, 0.3),
            FrameStep(3, 1, -1, 0.6),
            FrameStep(5, 1, 0, 0.6),
            FrameStep(5, 1, -2, 0.3),
            FrameStep(5, 0, -3, -0.3),
            FrameStep(5, -1, -1, -0.6),
            FrameStep(6, -1, -1, -0.7),
            FrameStep(6, 0, -3, -0.3),
            FrameStep(6, 1, -4, 0.4),
            FrameStep(6, 1, -1, 0.7),
            FrameStep(8, 0, 0, 0.4),
            FrameStep(8, 0, -2, 0.0),
            FrameStep(8, -1, -2, -0.4),
            FrameStep(8, 0, 0, -0.3),
        ),
    ),
}


def refine_chibi_frame(im: Image.Image, target_size: int = 320) -> Image.Image:
    """Limpia el borde die-cut blanco/gris, suaviza el contorno alfa y realza nitidez RGB."""
    rgba = im.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.float32)
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]

    chroma = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    luma = np.min(rgb, axis=2)

    # 1. Candidatos a fondo transparente o margen die-cut acromático (blanco/gris de corte)
    candidate = (alpha < 48.0) | ((chroma < 22.0) & (luma > 90.0))
    cand_img = Image.fromarray(np.where(candidate, 255, 0).astype(np.uint8), mode="L")
    padded = Image.new("L", (cand_img.width + 2, cand_img.height + 2), 255)
    padded.paste(cand_img, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    bg_mask = np.asarray(padded)[1:-1, 1:-1] == 128

    # 2. Erosión morfológica de 1px + anti-aliasing Gaussiano para eliminar el borde blanco
    fg_mask = (~bg_mask).astype(np.uint8) * 255
    fg_img = Image.fromarray(fg_mask, mode="L")
    eroded = fg_img.filter(ImageFilter.MinFilter(3))
    blurred = eroded.filter(ImageFilter.GaussianBlur(radius=0.65))
    smooth_a = np.asarray(blurred, dtype=np.float32) / 255.0
    smooth_a = np.where(smooth_a < 0.08, 0.0, np.clip(smooth_a * 1.15, 0.0, 1.0))

    # 3. Descontaminación de halo blanco en el borde semitransparente
    clean_rgb = rgb.copy()
    edge = (smooth_a > 0.0) & (smooth_a < 0.95)
    alpha_edge = np.maximum(smooth_a[edge][:, None], 0.25)
    clean_rgb[edge] = np.clip(
        (clean_rgb[edge] - (1.0 - alpha_edge) * 255.0) / alpha_edge,
        0.0,
        255.0,
    )

    # 4. Realce de nitidez sobre trazos anime (UnsharpMask)
    rgb_img = Image.fromarray(clean_rgb.astype(np.uint8), mode="RGB")
    sharpened_rgb = rgb_img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3))

    out = np.dstack(
        [np.asarray(sharpened_rgb, dtype=np.uint8), (smooth_a * 255.0).astype(np.uint8)]
    )
    out[smooth_a == 0.0] = (0, 0, 0, 0)
    result = Image.fromarray(out, mode="RGBA")

    if target_size != result.width or target_size != result.height:
        result = result.resize((target_size, target_size), resample=Image.Resampling.LANCZOS)
    return result


def transform_frame(frame: Image.Image, step: FrameStep) -> Image.Image:
    """Aplica micro-rotación y traslación sub-píxel manteniendo el lienzo transparente."""
    work = frame
    if abs(step.angle) > 0.01:
        work = work.rotate(
            step.angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=(0, 0, 0, 0),
        )
    if step.dx == 0 and step.dy == 0:
        return work
    canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    canvas.alpha_composite(work, (step.dx, step.dy))
    return canvas


def load_character_frames(pack_dir: Path, target_size: int = 320) -> list[Image.Image]:
    """Lee y refina los 12 fotogramas PNG de un paquete Chibi."""
    frames_dir = pack_dir / "Frames_PNG_512x512"
    if not frames_dir.is_dir():
        raise FileNotFoundError(f"No existe el directorio de fotogramas: {frames_dir}")

    frames: list[Image.Image] = []
    for idx in range(1, 13):
        frame_path = frames_dir / f"frame_{idx:02d}.png"
        if not frame_path.is_file():
            raise FileNotFoundError(f"Falta el fotograma requerido: {frame_path}")
        with Image.open(frame_path) as raw:
            frames.append(refine_chibi_frame(raw, target_size=target_size))
    return frames


def build_character_skin(
    skin_id: str,
    pack_folder: str,
    target_size: int = 320,
    assets_dir: Path = ASSETS_DIR,
    skins_dir: Path = SKINS_DIR,
) -> dict[str, Path]:
    """Genera los 16 archivos WebP animados para `skin_id` en `pet/web/skins/<skin_id>/`."""
    pack_dir = assets_dir / pack_folder
    base_frames = load_character_frames(pack_dir, target_size=target_size)
    out_dir = skins_dir / skin_id
    out_dir.mkdir(parents=True, exist_ok=True)

    generated: dict[str, Path] = {}
    for state_name, spec in STATE_SPECS.items():
        seq = [transform_frame(base_frames[step.index], step) for step in spec.steps]
        dst = out_dir / f"{state_name}.webp"
        seq[0].save(
            dst,
            format="WEBP",
            save_all=True,
            append_images=seq[1:],
            duration=spec.duration,
            loop=0,
            quality=90,
            method=4,
            minimize_size=True,
        )
        generated[state_name] = dst
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--skin",
        choices=sorted(CHARACTER_PACKS.keys()),
        help="Procesar solo un personaje específico (por defecto procesa los 5)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=320,
        help="Resolución cuadrada de salida en píxeles (por defecto 320)",
    )
    args = parser.parse_args()

    selected = [args.skin] if args.skin else list(CHARACTER_PACKS.keys())
    for skin_id in selected:
        folder, display_name = CHARACTER_PACKS[skin_id]
        outputs = build_character_skin(skin_id, folder, target_size=args.size)
        total_kb = sum(p.stat().st_size for p in outputs.values()) / 1024.0
        print(
            f"[chibi_studio] {display_name} ({skin_id}): "
            f"{len(outputs)} estados WebP generados ({total_kb:.1f} KB total)"
        )


if __name__ == "__main__":
    main()
