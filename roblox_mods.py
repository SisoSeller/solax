"""Mod locali: cielo (skybox) e icona shift lock da PNG."""

from __future__ import annotations

import shutil
import struct
import sys
from pathlib import Path

from PIL import Image

import roblox_fonts as rf

SKY_DIR = Path("PlatformContent") / "pc" / "textures" / "sky"
SHIFT_LOCK_REL = Path("content") / "textures" / "MouseLockedCursor.png"
SKY_FACES = ("bk", "dn", "ft", "lf", "rt", "up")


def _copy_backup(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    shutil.copy2(src, dest)


def _restore_backup(backup: Path, dest: Path) -> None:
    if not backup.is_file():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    rf.make_writable(dest)
    shutil.copy2(backup, dest)


def sky_folder(install: rf.RobloxInstall) -> Path:
    return install.version_dir / SKY_DIR


def shift_lock_file(install: rf.RobloxInstall) -> Path:
    return install.version_dir / SHIFT_LOCK_REL


def backup_root(install: rf.RobloxInstall) -> Path:
    return rf.app_data_dir() / "backups" / install.version_id


def rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _encode_dxt1_block(block: list[tuple[int, int, int]]) -> bytes:
    lo = min(block, key=lambda p: p[0] + p[1] + p[2])
    hi = max(block, key=lambda p: p[0] + p[1] + p[2])
    c0 = rgb565(*hi)
    c1 = rgb565(*lo)
    if c0 == c1:
        return struct.pack("<HHI", c0, c1, 0)
    if c0 < c1:
        c0, c1 = c1, c0
        hi, lo = lo, hi
    palette = (
        hi,
        lo,
        (
            (2 * hi[0] + lo[0]) // 3,
            (2 * hi[1] + lo[1]) // 3,
            (2 * hi[2] + lo[2]) // 3,
        ),
        (
            (hi[0] + 2 * lo[0]) // 3,
            (hi[1] + 2 * lo[1]) // 3,
            (hi[2] + 2 * lo[2]) // 3,
        ),
    )
    lookup = 0
    for i, px in enumerate(block):
        best_i = 0
        best_d = 1 << 30
        for j, col in enumerate(palette):
            dr = px[0] - col[0]
            dg = px[1] - col[1]
            db = px[2] - col[2]
            dist = dr * dr + dg * dg + db * db
            if dist < best_d:
                best_d = dist
                best_i = j
        lookup |= best_i << (i * 2)
    return struct.pack("<HHI", c0, c1, lookup)


def encode_dxt1_image(image: Image.Image) -> bytes:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    bw = max(1, (width + 3) // 4)
    bh = max(1, (height + 3) // 4)
    out = bytearray()
    for by in range(bh):
        for bx in range(bw):
            block = []
            for j in range(4):
                for i in range(4):
                    x = min(width - 1, bx * 4 + i)
                    y = min(height - 1, by * 4 + j)
                    block.append(pixels[x, y])
            out.extend(_encode_dxt1_block(block))
    return bytes(out)


def _dds_header(size: int, mip_count: int) -> bytes:
    linear_size = max(8, size * size // 2)
    header = struct.pack(
        "<4sIIIIIII",
        b"DDS ",
        124,
        0xA1007,
        size,
        size,
        linear_size,
        0,
        mip_count,
    )
    header += b"\x00" * 28
    header += b"UVER" + b"\x00" * 4 + b"NVTT" + struct.pack("<I", 0x00020100)
    header += struct.pack("<II4sIIIII", 32, 0x4, b"DXT1", 0, 0, 0, 0, 0)
    header += struct.pack("<IIIII", 0x401008, 0, 0, 0, 0)
    return header


def png_to_sky_tex(
    png_path: Path,
    size: int,
    mip_count: int,
    template: Path | None = None,
) -> bytes:
    source = Image.open(png_path).convert("RGB")
    current = source.resize((size, size), Image.Resampling.LANCZOS)
    mip_blobs: list[bytes] = []
    for _ in range(mip_count):
        mip_blobs.append(encode_dxt1_image(current))
        next_size = max(1, current.size[0] // 2)
        current = current.resize((next_size, next_size), Image.Resampling.LANCZOS)
    body = b"".join(mip_blobs)

    if template is not None and template.is_file():
        original = template.read_bytes()
        if original.startswith(b"DDS ") and len(original) >= 128:
            header = original[:128]
            want = len(original) - 128
            if len(body) > want:
                body = body[:want]
            elif len(body) < want:
                body += original[128 + len(body) :]
            return header + body

    return _dds_header(size, mip_count) + body


def bundled_day_sky_png() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [here / "assets" / "always_day.png"]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        mei = Path(getattr(sys, "_MEIPASS", exe_dir))
        candidates = [
            mei / "assets" / "always_day.png",
            exe_dir / "assets" / "always_day.png",
            exe_dir / "_internal" / "assets" / "always_day.png",
            here / "assets" / "always_day.png",
        ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def ensure_day_sky_png() -> Path:
    src = bundled_day_sky_png()
    dest = rf.app_data_dir() / "always_day.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        shutil.copy2(src, dest)
        return dest
    img = Image.new("RGB", (512, 512), (110, 176, 230))
    img.save(dest, "PNG")
    return dest


def apply_sky(
    png_path: Path,
    install: rf.RobloxInstall | None = None,
    persist: bool = True,
) -> rf.RobloxInstall:
    png_path = Path(png_path)
    if not png_path.is_file():
        raise FileNotFoundError(f"PNG del cielo non trovato:\n{png_path}")

    install = install or rf.find_roblox()
    if install is None:
        raise FileNotFoundError("Roblox non trovato.")

    folder = sky_folder(install)
    if not folder.is_dir():
        raise FileNotFoundError("Cartella cielo di Roblox non trovata.")

    backup = backup_root(install) / "sky"
    written = 0
    for target in sorted(folder.glob("*.tex")):
        name = target.name.lower()
        if name.startswith("sky512_"):
            size, mips = 1024, 11
        elif name.startswith("indoor512_"):
            size, mips = 512, 10
        else:
            continue
        _copy_backup(target, backup / target.name)
        tex = png_to_sky_tex(png_path, size, mips, template=backup / target.name)
        rf.make_writable(target)
        target.write_bytes(tex)
        written += 1

    if written == 0:
        raise FileNotFoundError("Nessun file cielo .tex trovato in Roblox.")

    if persist:
        cfg = rf.load_config()
        cfg["sky_png"] = str(png_path)
        rf.save_config(cfg)
    rf.log(f"sky: wrote {written} tex from {png_path}")
    return install


def apply_always_day(install: rf.RobloxInstall | None = None) -> rf.RobloxInstall:
    return apply_sky(ensure_day_sky_png(), install, persist=False)


def restore_sky(install: rf.RobloxInstall | None = None) -> None:
    install = install or rf.find_roblox()
    if install is None:
        return
    backup = backup_root(install) / "sky"
    folder = sky_folder(install)
    if not backup.is_dir():
        return
    for tex in backup.glob("*.tex"):
        _restore_backup(tex, folder / tex.name)


def apply_shift_lock(png_path: Path, install: rf.RobloxInstall | None = None) -> rf.RobloxInstall:
    png_path = Path(png_path)
    if not png_path.is_file():
        raise FileNotFoundError(f"PNG shift lock non trovato:\n{png_path}")

    install = install or rf.find_roblox()
    if install is None:
        raise FileNotFoundError("Roblox non trovato.")

    target = shift_lock_file(install)
    if target.is_file():
        _copy_backup(target, backup_root(install) / "textures" / "MouseLockedCursor.png")

    image = Image.open(png_path).convert("RGBA")
    if image.size != (32, 32):
        image = image.resize((32, 32), Image.Resampling.LANCZOS)
    target.parent.mkdir(parents=True, exist_ok=True)
    rf.make_writable(target)
    image.save(target, format="PNG")

    cfg = rf.load_config()
    cfg["shift_lock_png"] = str(png_path)
    rf.save_config(cfg)
    return install


def restore_shift_lock(install: rf.RobloxInstall | None = None) -> None:
    install = install or rf.find_roblox()
    if install is None:
        return
    backup = backup_root(install) / "textures" / "MouseLockedCursor.png"
    _restore_backup(backup, shift_lock_file(install))
