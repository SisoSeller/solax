"""Korblox locale: sostituisce content/avatar/meshes/rightleg.mesh."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import roblox_fonts as rf

MESH_REL = Path("content") / "avatar" / "meshes" / "rightleg.mesh"


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _meipass() -> Path | None:
    if _frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return None


def _app_mesh() -> Path:
    return rf.app_data_dir() / "assets" / "rightleg.mesh"


def _source_meshes() -> list[Path]:
    here = Path(__file__).resolve().parent
    exe_dir = Path(sys.executable).resolve().parent if _frozen() else here
    paths = [
        here / "assets" / "rightleg.mesh",
        exe_dir / "assets" / "rightleg.mesh",
        exe_dir / "rightleg.mesh",
        _app_mesh(),
    ]
    mei = _meipass()
    if mei is not None:
        paths.insert(0, mei / "assets" / "rightleg.mesh")
        paths.insert(1, mei / "rightleg.mesh")
    return paths


def ensure_korblox_mesh() -> Path:
    dest = _app_mesh()
    dest.parent.mkdir(parents=True, exist_ok=True)
    for src in _source_meshes():
        try:
            if not src.is_file():
                continue
            if src.resolve() == dest.resolve():
                return dest
            if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
                shutil.copy2(src, dest)
            if _frozen():
                beside = Path(sys.executable).resolve().parent / "assets" / "rightleg.mesh"
                beside.parent.mkdir(parents=True, exist_ok=True)
                if not beside.is_file() or beside.stat().st_size != src.stat().st_size:
                    shutil.copy2(src, beside)
            return dest
        except OSError:
            continue
    if dest.is_file():
        return dest
    raise FileNotFoundError(
        "Korblox: rightleg.mesh non trovato.\n"
        "Passa SolaX.exe (quello nuovo) oppure metti rightleg.mesh nella cartella assets."
    )


def korblox_mesh_path() -> Path:
    cfg = rf.load_config()
    custom = cfg.get("korblox_mesh")
    if custom and Path(custom).is_file():
        return Path(custom)
    return ensure_korblox_mesh()


def target_mesh(install: rf.RobloxInstall) -> Path:
    return install.version_dir / MESH_REL


def backup_mesh(install: rf.RobloxInstall) -> Path:
    return rf.app_data_dir() / "backups" / install.version_id / "meshes" / "rightleg.mesh"


def apply_korblox(install: rf.RobloxInstall | None = None) -> rf.RobloxInstall:
    install = install or rf.find_roblox()
    if install is None:
        raise FileNotFoundError("Roblox non trovato.")

    src = korblox_mesh_path()
    dest = target_mesh(install)
    dest.parent.mkdir(parents=True, exist_ok=True)
    backup = backup_mesh(install)
    if dest.is_file() and not backup.is_file():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, backup)
    rf.make_writable(dest)
    shutil.copy2(src, dest)
    if dest.stat().st_size != src.stat().st_size:
        raise OSError("Copia Korblox incompleta: Roblox è aperto o il file è bloccato.")
    rf.log(f"korblox: {src} ({src.stat().st_size}b) -> {dest}")
    return install


def restore_korblox(install: rf.RobloxInstall | None = None) -> None:
    install = install or rf.find_roblox()
    if install is None:
        return
    backup = backup_mesh(install)
    dest = target_mesh(install)
    if not backup.is_file():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    rf.make_writable(dest)
    shutil.copy2(backup, dest)
    rf.log(f"korblox restore: {dest}")
