"""Plugin locali: solo file .bat nella cartella plugin di SolaX."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import roblox_fonts as rf


def plugins_dir() -> Path:
    path = rf.app_data_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def display_name(path: Path) -> str:
    return Path(path).stem.replace("_", " ").strip() or Path(path).name


def _plugin_key(name: str) -> str:
    return " ".join(Path(name).stem.lower().replace("_", " ").replace("-", " ").split())


def is_always_day(name: str) -> bool:
    return _plugin_key(name) in {"all day", "allday", "sempre giorno"}


def has_always_day(enabled: list[str]) -> bool:
    return any(is_always_day(name) for name in enabled)


def description(path: Path) -> str:
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
    return sorted(p for p in root.glob("*.bat") if p.is_file())


def add_plugin(src: Path) -> Path:
    src = Path(src)
    if src.suffix.lower() != ".bat":
        raise ValueError("I plugin accettano solo file .bat.")
    if not src.is_file():
        raise FileNotFoundError("File .bat non trovato.")
    dest = plugins_dir() / src.name
    shutil.copy2(src, dest)
    rf.log(f"plugin add: {dest}")
    return dest


def remove_plugin(name: str) -> None:
    root = plugins_dir().resolve()
    path = (plugins_dir() / Path(name).name).resolve()
    if path.parent != root or path.suffix.lower() != ".bat":
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
        path = (plugins_dir() / Path(name).name).resolve()
        if path.parent != root or path.suffix.lower() != ".bat" or not path.is_file():
            continue
        try:
            completed = subprocess.run(
                ["cmd.exe", "/c", str(path)],
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
