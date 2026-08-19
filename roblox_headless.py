"""Headless locale: elimina content/avatar/heads (con backup)."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import roblox_fonts as rf

HEADS_REL = Path("content") / "avatar" / "heads"


def heads_dir(install: rf.RobloxInstall) -> Path:
    return install.version_dir / HEADS_REL


def backup_dir(install: rf.RobloxInstall) -> Path:
    return rf.app_data_dir() / "backups" / install.version_id / "heads"


def _writable_tree(path: Path) -> None:
    if not path.exists():
        return
    for item in [path, *path.rglob("*")]:
        rf.make_writable(item)


def _force_rmtree(path: Path) -> None:
    if not path.exists():
        return
    _writable_tree(path)

    def onexc(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        except OSError:
            pass
        func(p)

    shutil.rmtree(path, onexc=onexc)


def _backup_has_files(backup: Path) -> bool:
    return backup.is_dir() and any(backup.rglob("*"))


def apply_headless(install: rf.RobloxInstall | None = None) -> rf.RobloxInstall:
    install = install or rf.find_roblox()
    if install is None:
        raise FileNotFoundError("Roblox non trovato.")

    folder = heads_dir(install)
    backup = backup_dir(install)
    if folder.is_dir() and not _backup_has_files(backup):
        backup.parent.mkdir(parents=True, exist_ok=True)
        _force_rmtree(backup)
        shutil.copytree(folder, backup)

    if folder.exists():
        _force_rmtree(folder)
        rf.log(f"headless: deleted {folder}")
    return install


def restore_headless(install: rf.RobloxInstall | None = None) -> None:
    install = install or rf.find_roblox()
    if install is None:
        return
    backup = backup_dir(install)
    folder = heads_dir(install)
    if not _backup_has_files(backup):
        return
    _force_rmtree(folder)
    shutil.copytree(backup, folder)
    rf.log(f"headless: restored {folder}")
