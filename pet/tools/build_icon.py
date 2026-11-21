"""Diseña el icono oficial de MEKA Companion y genera el recurso COFF (.syso) para Windows.

Produce:
- `pet/desktop/icons/icon.png` (512x512)
- `pet/desktop/icons/128x128@2x.png` (256x256)
- `pet/desktop/icons/128x128.png` (128x128)
- `pet/desktop/icons/32x32.png` (32x32)
- `pet/desktop/icons/icon.ico` (multi-resolución 16, 24, 32, 48, 64, 128, 256)
- `pet/web/favicon.ico` (16, 32, 48)
- `pet/desktop/rsrc_windows_amd64.syso` (recurso nativo RT_ICON + RT_GROUP_ICON para `go build`)

Uso:
    python pet/tools/build_icon.py
"""

from __future__ import annotations

import io
import math
import struct
from pathlib import Path

import numpy as np
from chibi_studio import refine_chibi_frame
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent.parent
HERO_FRAME = ROOT / "assets" / "Hana_Song_DVa_Chibi_12Frames_Web_Go" / "Frames_PNG_512x512" / "frame_06.png"
ICONS_DIR = ROOT / "pet" / "desktop" / "icons"
WEB_FAVICON = ROOT / "pet" / "web" / "favicon.ico"
SYSO_PATH = ROOT / "pet" / "desktop" / "rsrc_windows_amd64.syso"

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
FAVICON_SIZES = [16, 32, 48]


def _squircle_mask(size: int, margin: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=radius,
        fill=255,
    )
    return mask


def _add_radial_glow(
    base: Image.Image,
    center: tuple[float, float],
    radius: float,
    color: tuple[int, int, int],
    max_alpha: int,
) -> Image.Image:
    w, h = base.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2)
    falloff = np.clip(1.0 - (dist / radius), 0.0, 1.0) ** 2.1
    layer = np.zeros((h, w, 4), dtype=np.uint8)
    layer[:, :, 0] = color[0]
    layer[:, :, 1] = color[1]
    layer[:, :, 2] = color[2]
    layer[:, :, 3] = (falloff * max_alpha).astype(np.uint8)
    return Image.alpha_composite(base, Image.fromarray(layer, mode="RGBA"))


def _crop_to_content(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    if bbox is None:
        return im
    return im.crop(bbox)


def render_meka_app_icon(output_size: int = 512) -> Image.Image:
    """Renderiza el icono cuadrado Liquid Glass + Dynamic Island de MEKA en alta resolución."""
    canvas_size = 1024
    margin = 48
    radius = 224

    # 1. Base degradada oscura con ambientación violeta/cian
    yy, xx = np.mgrid[0:canvas_size, 0:canvas_size].astype(np.float32)
    t = np.clip((xx * 0.45 + yy * 0.85) / (canvas_size * 1.25), 0.0, 1.0)
    r = (11 + (28 - 11) * t).astype(np.uint8)
    g = (12 + (19 - 12) * t).astype(np.uint8)
    b = (26 + (54 - 26) * t).astype(np.uint8)
    a = np.full((canvas_size, canvas_size), 255, dtype=np.uint8)
    base = Image.fromarray(np.dstack([r, g, b, a]), mode="RGBA")

    # Resplandores Liquid Glass internos
    base = _add_radial_glow(base, (canvas_size * 0.25, canvas_size * 0.22), 540, (56, 189, 248), 115)
    base = _add_radial_glow(base, (canvas_size * 0.78, canvas_size * 0.30), 520, (168, 85, 247), 130)
    base = _add_radial_glow(base, (canvas_size * 0.52, canvas_size * 0.62), 480, (236, 72, 153), 120)

    # 2. Aro HUD tech sutil detrás de Hana
    ring_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring_layer)
    cx, cy = canvas_size // 2, int(canvas_size * 0.55)
    for ring_r, col in ((345, (34, 211, 238, 64)), (295, (168, 85, 247, 54))):
        ring_draw.ellipse(
            (cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r),
            outline=col,
            width=6,
        )
    ring_layer = ring_layer.filter(ImageFilter.GaussianBlur(radius=1.5))
    base = Image.alpha_composite(base, ring_layer)

    # 3. Cápsula Dynamic Island en la parte superior del emblema
    island_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    island_draw = ImageDraw.Draw(island_layer)
    pill_w, pill_h = 336, 70
    px0 = (canvas_size - pill_w) // 2
    py0 = margin + 46
    island_draw.rounded_rectangle(
        (px0, py0, px0 + pill_w, py0 + pill_h),
        radius=pill_h // 2,
        fill=(6, 7, 15, 228),
        outline=(190, 225, 255, 85),
        width=4,
    )
    # Puntos de estado activos dentro de la isla
    island_draw.ellipse((px0 + 26, py0 + 23, px0 + 50, py0 + 47), fill=(52, 211, 153, 255))
    island_draw.rounded_rectangle(
        (px0 + pill_w - 86, py0 + 28, px0 + pill_w - 28, py0 + 42),
        radius=7,
        fill=(56, 189, 248, 220),
    )
    base = Image.alpha_composite(base, island_layer)

    # 4. Retrato protagonista de Hana Chibi limpio (sin borde sticker blanco)
    if HERO_FRAME.is_file():
        hero_raw = Image.open(HERO_FRAME).convert("RGBA")
        hero = refine_chibi_frame(hero_raw, target_size=820)
    else:
        hero = Image.new("RGBA", (620, 620), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hero)
        hd.ellipse((120, 120, 500, 500), fill=(244, 114, 182, 255))

    hero_cropped = _crop_to_content(hero)
    max_w, max_h = 710, 710
    scale = min(max_w / max(hero_cropped.width, 1), max_h / max(hero_cropped.height, 1))
    target_w = max(1, round(hero_cropped.width * scale))
    target_h = max(1, round(hero_cropped.height * scale))
    hero_scaled = hero_cropped.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)

    hx = (canvas_size - target_w) // 2 + 12
    hy = int(canvas_size * 0.535 - target_h * 0.48)

    # 4b. Onda de audio Liquid Glass luminosa detrás de los pies de Hana
    wave_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wave_layer)
    pts_primary: list[tuple[float, float]] = []
    pts_secondary: list[tuple[float, float]] = []
    x_start, x_end = margin + 40, canvas_size - margin - 40
    base_y = canvas_size - margin - 92
    for px in range(x_start, x_end + 1, 8):
        prog = (px - x_start) / max(1, (x_end - x_start))
        env = math.sin(prog * math.pi)
        y1 = base_y + math.sin(prog * math.tau * 2.5) * 20.0 * env
        y2 = base_y + math.cos(prog * math.tau * 2.0 + 0.8) * 14.0 * env
        pts_primary.append((px, y1))
        pts_secondary.append((px, y2))
    wd.line(pts_secondary, fill=(168, 85, 247, 175), width=10, joint="curve")
    wd.line(pts_primary, fill=(56, 232, 255, 230), width=12, joint="curve")
    wave_glow = wave_layer.filter(ImageFilter.GaussianBlur(radius=6))
    base = Image.alpha_composite(base, wave_glow)
    base = Image.alpha_composite(base, wave_layer)

    # Sombra suave detrás del personaje para separarlo del fondo oscuro
    alpha_mask = hero_scaled.getchannel("A")
    shadow_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    black_sil = Image.new("RGBA", hero_scaled.size, (5, 4, 18, 175))
    shadow_img.paste(black_sil, (hx, hy + 18), alpha_mask)
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=22))
    base = Image.alpha_composite(base, shadow_img)

    fg_hero = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    fg_hero.paste(hero_scaled, (hx, hy), hero_scaled)
    base = Image.alpha_composite(base, fg_hero)

    # 6. Recorte squircle y bisel especular Liquid Glass
    squircle = _squircle_mask(canvas_size, margin=margin, radius=radius)

    # Reflejo vítreo superior sutil
    sheen = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.pieslice(
        (margin - 140, margin - 320, canvas_size - margin + 140, margin + 360),
        start=10,
        end=170,
        fill=(255, 255, 255, 34),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=10))
    base = Image.alpha_composite(base, sheen)

    # Borde luminoso estilo Liquid Glass
    border_layer = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border_layer)
    bd.rounded_rectangle(
        (margin + 3, margin + 3, canvas_size - margin - 3, canvas_size - margin - 3),
        radius=radius - 2,
        outline=(210, 238, 255, 118),
        width=8,
    )
    bd.rounded_rectangle(
        (margin + 10, margin + 10, canvas_size - margin - 10, canvas_size - margin - 10),
        radius=radius - 8,
        outline=(168, 85, 247, 92),
        width=4,
    )
    base = Image.alpha_composite(base, border_layer)

    # Aplicar máscara squircle final manteniendo fondo 100% transparente fuera del icono
    clipped_alpha = ImageChops.multiply(base.getchannel("A"), squircle)
    base.putalpha(clipped_alpha)

    if output_size != canvas_size:
        return base.resize((output_size, output_size), resample=Image.Resampling.LANCZOS)
    return base


def _encode_ico_images(master: Image.Image, sizes: list[int]) -> tuple[bytes, list[tuple[int, int, bytes]]]:
    """Genera un archivo .ico multi-resolución (PNG >=128px y DIB RGBA <=64px) y retorna sus entradas."""
    entries: list[tuple[int, int, bytes]] = []
    for sz in sizes:
        frame = master.resize((sz, sz), resample=Image.Resampling.LANCZOS)
        if sz >= 128:
            buf = io.BytesIO()
            frame.save(buf, format="PNG")
            payload = buf.getvalue()
        else:
            # DIB clásico (BITMAPINFOHEADER de 40 bytes + BGRA bottom-up + máscara AND)
            arr = np.asarray(frame.convert("RGBA"), dtype=np.uint8)
            bgra = arr[::-1, :, [2, 1, 0, 3]].tobytes()
            and_stride = ((sz + 31) // 32) * 4
            and_mask = b"\x00" * (and_stride * sz)
            bih = struct.pack(
                "<IIIHHIIIIII",
                40,          # biSize
                sz,          # biWidth
                sz * 2,      # biHeight (XOR + AND)
                1,           # biPlanes
                32,          # biBitCount
                0,           # biCompression (BI_RGB)
                len(bgra) + len(and_mask),
                0,
                0,
                0,
                0,
            )
            payload = bih + bgra + and_mask
        entries.append((sz, sz, payload))

    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    dir_bytes = bytearray()
    blob_bytes = bytearray()
    for w, h, payload in entries:
        bw = 0 if w >= 256 else w
        bh = 0 if h >= 256 else h
        dir_bytes.extend(struct.pack("<BBBBHHII", bw, bh, 0, 0, 1, 32, len(payload), offset))
        blob_bytes.extend(payload)
        offset += len(payload)
    return header + bytes(dir_bytes) + bytes(blob_bytes), entries


def build_coff_syso(entries: list[tuple[int, int, bytes]], syso_path: Path) -> None:
    """Empaqueta las entradas RT_ICON (3) y RT_GROUP_ICON (14) en un objeto COFF x86_64 `.syso`."""
    # Construir estructura GRPICONDIR para RT_GROUP_ICON (ID 1)
    grp_buf = bytearray(struct.pack("<HHH", 0, 1, len(entries)))
    for idx, (w, h, payload) in enumerate(entries, start=1):
        bw = 0 if w >= 256 else w
        bh = 0 if h >= 256 else h
        grp_buf.extend(struct.pack("<BBBBHHIH", bw, bh, 0, 0, 1, 32, len(payload), idx))
    grp_bytes = bytes(grp_buf)

    # Recursos totales: N entradas RT_ICON (IDs 1..N) + 1 entrada RT_GROUP_ICON (ID 1)
    num_icons = len(entries)
    # Directorio raíz (2 entradas: RT_ICON=3, RT_GROUP_ICON=14)
    # Cada directorio = 16 bytes + M * 8 bytes
    root_dir_off = 0
    root_dir_size = 16 + 2 * 8  # 32

    type_icon_dir_off = root_dir_off + root_dir_size
    type_icon_dir_size = 16 + num_icons * 8

    type_grp_dir_off = type_icon_dir_off + type_icon_dir_size
    type_grp_dir_size = 16 + 1 * 8

    lang_dirs_off = type_grp_dir_off + type_grp_dir_size
    lang_dir_size = 16 + 1 * 8  # 24 bytes cada uno
    total_lang_dirs = num_icons + 1

    data_entries_off = lang_dirs_off + total_lang_dirs * lang_dir_size
    data_entry_size = 16
    total_data_entries = num_icons + 1

    raw_blobs_off = data_entries_off + total_data_entries * data_entry_size
    if raw_blobs_off % 4 != 0:
        raw_blobs_off += 4 - (raw_blobs_off % 4)

    rsrc = bytearray(raw_blobs_off)
    relocs: list[tuple[int, int, int]] = []  # (VirtualAddress, SymbolTableIndex, Type)

    def write_dir(offset: int, id_entries: list[tuple[int, int, bool]]) -> None:
        struct.pack_into("<IIHHHH", rsrc, offset, 0, 0, 0, 0, 0, len(id_entries))
        pos = offset + 16
        for name_id, target_off, is_subdir in id_entries:
            val = target_off | (0x80000000 if is_subdir else 0)
            struct.pack_into("<II", rsrc, pos, name_id, val)
            pos += 8

    # 1. Raíz (RT_ICON=3, RT_GROUP_ICON=14)
    write_dir(
        root_dir_off,
        [
            (3, type_icon_dir_off, True),
            (14, type_grp_dir_off, True),
        ],
    )

    # 2. Subdirectorio RT_ICON -> N idiomas
    icon_name_entries = []
    for i in range(num_icons):
        lang_off = lang_dirs_off + i * lang_dir_size
        icon_name_entries.append((i + 1, lang_off, True))
        data_off = data_entries_off + i * data_entry_size
        write_dir(lang_off, [(0x0409, data_off, False)])
    write_dir(type_icon_dir_off, icon_name_entries)

    # 3. Subdirectorio RT_GROUP_ICON -> idioma 0x0409
    grp_lang_off = lang_dirs_off + num_icons * lang_dir_size
    grp_data_off = data_entries_off + num_icons * data_entry_size
    write_dir(type_grp_dir_off, [(1, grp_lang_off, True)])
    write_dir(grp_lang_off, [(0x0409, grp_data_off, False)])

    # 4. Escribir DATA_ENTRY + blobs alineados a 4 bytes
    def append_blob(data_entry_off: int, payload: bytes) -> None:
        while len(rsrc) % 4 != 0:
            rsrc.append(0)
        blob_rva = len(rsrc)
        rsrc.extend(payload)
        struct.pack_into("<IIII", rsrc, data_entry_off, blob_rva, len(payload), 0, 0)
        # IMAGE_REL_AMD64_ADDR32NB = 0x0003 sobre symbol 0 (.rsrc)
        relocs.append((data_entry_off, 0, 0x0003))

    for i, (_w, _h, payload) in enumerate(entries):
        append_blob(data_entries_off + i * data_entry_size, payload)
    append_blob(grp_data_off, grp_bytes)

    while len(rsrc) % 8 != 0:
        rsrc.append(0)

    # 5. Ensamblar COFF Header + Section Header + .rsrc + Relocations + Symbol Table + String Table
    coff_header_size = 20
    sec_header_size = 40
    ptr_raw_data = coff_header_size + sec_header_size
    ptr_relocs = ptr_raw_data + len(rsrc)
    ptr_symtab = ptr_relocs + len(relocs) * 10

    coff_hdr = struct.pack(
        "<HHIIIHH",
        0x8664,      # IMAGE_FILE_MACHINE_AMD64
        1,           # NumberOfSections
        0,           # TimeDateStamp
        ptr_symtab,  # PointerToSymbolTable
        1,           # NumberOfSymbols
        0,           # SizeOfOptionalHeader
        0,           # Characteristics
    )
    sec_hdr = struct.pack(
        "<8sIIIIIIHHI",
        b".rsrc\x00\x00\x00",
        0,            # VirtualSize
        0,            # VirtualAddress
        len(rsrc),    # SizeOfRawData
        ptr_raw_data, # PointerToRawData
        ptr_relocs,   # PointerToRelocations
        0,            # PointerToLinenumbers
        len(relocs),  # NumberOfRelocations
        0,            # NumberOfLinenumbers
        0x40000040,   # IMAGE_SCN_CNT_INITIALIZED_DATA | IMAGE_SCN_MEM_READ
    )
    reloc_bytes = b"".join(struct.pack("<IIH", va, sym, rtype) for va, sym, rtype in relocs)
    # IMAGE_SYMBOL (18 bytes): .rsrc section symbol, StorageClass=3 (STATIC)
    sym_bytes = struct.pack("<8sIhBB", b".rsrc\x00\x00\x00", 0, 1, 0, 3) + b"\x00\x00"
    strtab_bytes = struct.pack("<I", 4)

    syso_path.parent.mkdir(parents=True, exist_ok=True)
    syso_path.write_bytes(coff_hdr + sec_hdr + bytes(rsrc) + reloc_bytes + sym_bytes + strtab_bytes)


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    master = render_meka_app_icon(output_size=512)

    master.save(ICONS_DIR / "icon.png", format="PNG")
    master.resize((256, 256), resample=Image.Resampling.LANCZOS).save(
        ICONS_DIR / "128x128@2x.png", format="PNG"
    )
    master.resize((128, 128), resample=Image.Resampling.LANCZOS).save(
        ICONS_DIR / "128x128.png", format="PNG"
    )
    master.resize((32, 32), resample=Image.Resampling.LANCZOS).save(
        ICONS_DIR / "32x32.png", format="PNG"
    )

    ico_bytes, entries = _encode_ico_images(master, ICO_SIZES)
    (ICONS_DIR / "icon.ico").write_bytes(ico_bytes)

    fav_bytes, _ = _encode_ico_images(master, FAVICON_SIZES)
    WEB_FAVICON.write_bytes(fav_bytes)

    build_coff_syso(entries, SYSO_PATH)

    print(f"OK icon.png + icon.ico ({len(entries)} tamaños) -> {ICONS_DIR}")
    print(f"OK favicon.ico -> {WEB_FAVICON}")
    print(f"OK recurso COFF -> {SYSO_PATH} ({SYSO_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
