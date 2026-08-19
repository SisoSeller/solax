"""Plugin locali: .exe/.bat in AppData, più ALL DAY.exe incluso nel setup."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import roblox_fonts as rf

PLUGIN_EXTS = {".exe", ".bat"}


def plugins_dir() -> Path:
    path = rf.app_data_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def builtin_all_day() -> Path | None:
    frozen = install_dir() / "ALL DAY.exe"
    if frozen.is_file() and frozen.stat().st_size > 1024:
        return frozen
    dummy = plugins_dir() / "ALL DAY.exe"
    if not dummy.is_file():
        dummy.write_bytes(b"")
    return dummy


def bundled_plugin_names() -> list[str]:
    return ["ALL DAY.exe"]


def is_bundled(name: str) -> bool:
    return Path(name).name.lower() == "all day.exe"


def install_bundled_plugins() -> list[str]:
    root = plugins_dir()
    old_bat = root / "ALL DAY.bat"
    if old_bat.is_file():
        old_bat.unlink()
        rf.log("plugin bundled: removed ALL DAY.bat")
    dummy = root / "ALL DAY.exe"
    builtin = install_dir() / "ALL DAY.exe"
    if builtin.is_file() and builtin.stat().st_size > 1024 and dummy.is_file() and dummy.stat().st_size < 1024:
        dummy.unlink()
    builtin_all_day()
    return list(bundled_plugin_names())


def display_name(path: Path) -> str:
    return Path(path).stem.replace("_", " ").strip() or Path(path).name


def _plugin_key(name: str) -> str:
    return " ".join(Path(name).stem.lower().replace("_", " ").replace("-", " ").split())


def is_always_day(name: str) -> bool:
    return _plugin_key(name) in {"all day", "allday", "sempre giorno"}


def has_always_day(enabled: list[str]) -> bool:
    return any(is_always_day(name) for name in enabled)


def description(path: Path) -> str:
    if is_always_day(path.name):
        return "Solo sul tuo client: cielo sempre questo, gli altri non lo vedono."
    if path.suffix.lower() == ".exe":
        return "Plugin .exe. Si avvia con Save and Launch se è attivo."
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return "Plugin locale. Si avvia con Save and Launch se è attivo."
    notes: list[str] = []
    for line in lines:
        text = line.strip()
        if text.lower().startswith("rem "):
            note = text[4:].strip()
            if note.lower().startswith("solax plugin"):
                continue
            if note.lower().startswith("aggiungilo"):
                continue
            if note:
                notes.append(note)
        if len(notes) >= 2:
            break
    if notes:
        return " ".join(notes)
    return "Plugin locale. Si avvia con Save and Launch se è attivo."


def list_plugins() -> list[Path]:
    root = plugins_dir()
    items: list[Path] = []
    seen: set[str] = set()
    builtin = builtin_all_day()
    if builtin is not None:
        items.append(builtin)
        seen.add(builtin.name.lower())
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in PLUGIN_EXTS:
            continue
        if path.name.lower() in seen:
            continue
        if path.name.lower() == "all day.bat":
            continue
        items.append(path)
        seen.add(path.name.lower())
    return items


def add_plugin(src: Path) -> Path:
    src = Path(src)
    if src.suffix.lower() not in PLUGIN_EXTS:
        raise ValueError("I plugin accettano file .exe o .bat.")
    if not src.is_file():
        raise FileNotFoundError("File plugin non trovato.")
    if is_always_day(src.name):
        raise ValueError("ALL DAY è già dentro SolaX.")
    dest = plugins_dir() / src.name
    shutil.copy2(src, dest)
    rf.log(f"plugin add: {dest}")
    return dest


def remove_plugin(name: str) -> None:
    if is_bundled(name) or is_always_day(name):
        return
    root = plugins_dir().resolve()
    path = (plugins_dir() / Path(name).name).resolve()
    if path.parent != root or path.suffix.lower() not in PLUGIN_EXTS:
        return
    if path.is_file():
        path.unlink()
        rf.log(f"plugin remove: {path.name}")


def run_plugins(enabled: list[str], cwd: Path | None = None) -> list[str]:
    warnings: list[str] = []
    root = plugins_dir().resolve()
    workdir = Path(cwd) if cwd and Path(cwd).is_dir() else plugins_dir()
    flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flags |= subprocess.CREATE_NO_WINDOW
    for name in enabled:
        if is_always_day(name):
            continue
        path = (plugins_dir() / Path(name).name).resolve()
        if path.parent != root or path.suffix.lower() not in PLUGIN_EXTS or not path.is_file():
            continue
        try:
            if path.suffix.lower() == ".bat":
                cmd = ["cmd.exe", "/c", str(path)]
            else:
                cmd = [str(path)]
            completed = subprocess.run(
                cmd,
                cwd=str(workdir),
                timeout=90,
                capture_output=True,
                text=True,
                creationflags=flags,
            )
            rf.log(f"plugin run: {path.name} code={completed.returncode}")
            if completed.returncode != 0:
                err = (completed.stderr or completed.stdout or "").strip()[:240]
                warnings.append(f"{path.name}: uscita {completed.returncode}" + (f" ({err})" if err else ""))
        except Exception as exc:
            rf.log(f"plugin run failed: {path.name}: {exc}")
            warnings.append(f"{path.name}: {exc}")
    return warnings
