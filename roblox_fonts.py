"""Logica locale: trova Roblox, applica/ripristina un font, avvia il client."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import stat
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "SolaX"
CUSTOM_STEM = "CustomFont"
ASSET_PREFIX = "rbxasset://fonts/"


def app_data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_path() -> Path:
    return app_data_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    config_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def log(msg: str) -> None:
    try:
        with (app_data_dir() / "solax.log").open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def make_writable(path: Path) -> None:
    if not path.exists():
        return
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def _version_dirs() -> list[Path]:
    roots = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "Versions",
        Path(os.environ.get("PROGRAMFILES", "")) / "Roblox" / "Versions",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Roblox" / "Versions",
    ]
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if child.is_dir() and (child / "RobloxPlayerBeta.exe").is_file():
                found.append(child)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


@dataclass
class RobloxInstall:
    version_dir: Path
    player_exe: Path
    fonts_dir: Path
    families_dir: Path

    @property
    def version_id(self) -> str:
        return self.version_dir.name

    @property
    def custom_fonts(self) -> list[Path]:
        return sorted(self.fonts_dir.glob(f"{CUSTOM_STEM}.*"))

    def is_modified(self) -> bool:
        if self.custom_fonts:
            return True
        if not self.families_dir.is_dir():
            return False
        for json_file in self.families_dir.glob("*.json"):
            try:
                text = json_file.read_text(encoding="utf-8")
            except OSError:
                continue
            if f"{ASSET_PREFIX}{CUSTOM_STEM}." in text:
                return True
        return False


def find_roblox() -> RobloxInstall | None:
    for version_dir in _version_dirs():
        fonts_dir = version_dir / "content" / "fonts"
        families_dir = fonts_dir / "families"
        if fonts_dir.is_dir() and families_dir.is_dir():
            return RobloxInstall(
                version_dir=version_dir,
                player_exe=version_dir / "RobloxPlayerBeta.exe",
                fonts_dir=fonts_dir,
                families_dir=families_dir,
            )
    return None


def roblox_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    except OSError:
        return False
    return "RobloxPlayerBeta.exe" in (result.stdout or "")


def close_roblox(timeout: float = 12.0) -> None:
    subprocess.run(
        ["taskkill", "/IM", "RobloxPlayerBeta.exe", "/F"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    subprocess.run(
        ["taskkill", "/IM", "RobloxCrashHandler.exe", "/F"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    deadline = time.time() + timeout
    while time.time() < deadline and roblox_running():
        time.sleep(0.2)


def backup_dir_for(install: RobloxInstall) -> Path:
    return app_data_dir() / "backups" / install.version_id / "families"


def ensure_backup(install: RobloxInstall) -> Path:
    dest = backup_dir_for(install)
    if dest.is_dir() and any(dest.glob("*.json")):
        return dest
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(install.families_dir, dest)
    return dest


def apply_font(font_path: Path, install: RobloxInstall | None = None) -> RobloxInstall:
    font_path = Path(font_path)
    if not font_path.is_file():
        raise FileNotFoundError(f"File font non trovato:\n{font_path}")

    ext = font_path.suffix.lower()
    if ext not in {".ttf", ".otf"}:
        raise ValueError("Usa un file .ttf oppure .otf.")

    install = install or find_roblox()
    if install is None:
        raise FileNotFoundError(
            "Roblox non trovato. Installa Roblox, avvialo una volta, poi riprova."
        )

    ensure_backup(install)

    for old in install.custom_fonts:
        make_writable(old)
        old.unlink(missing_ok=True)

    dest = install.fonts_dir / f"{CUSTOM_STEM}{ext}"
    make_writable(dest)
    shutil.copy2(font_path, dest)

    asset_id = f"{ASSET_PREFIX}{CUSTOM_STEM}{ext}"
    written = 0
    for json_file in sorted(install.families_dir.glob("*.json")):
        make_writable(json_file)
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        faces = data.get("faces") or data.get("Faces") or []
        changed = False
        for face in faces:
            if not isinstance(face, dict):
                continue
            key = "assetId" if "assetId" in face else "AssetId" if "AssetId" in face else "assetId"
            if face.get(key) != asset_id:
                face[key] = asset_id
                changed = True
        if changed:
            json_file.write_text(
                json.dumps(data, indent="\t", ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            written += 1

    if written == 0:
        log("apply_font: nessun JSON families modificato, font copiato comunque")

    cfg = load_config()
    cfg["last_font"] = str(font_path)
    cfg["last_font_name"] = font_family_name(font_path) or font_path.stem
    cfg["last_version"] = install.version_id
    save_config(cfg)
    return install


def restore_fonts(install: RobloxInstall | None = None) -> RobloxInstall:
    install = install or find_roblox()
    if install is None:
        raise FileNotFoundError("Roblox non trovato.")

    backup = backup_dir_for(install)
    if not backup.is_dir() or not any(backup.glob("*.json")):
        raise FileNotFoundError(
            "Nessun backup per questa versione di Roblox.\n"
            "Se hai appena aggiornato Roblox, i font originali sono già tornati da soli."
        )

    for json_file in backup.glob("*.json"):
        dest = install.families_dir / json_file.name
        make_writable(dest)
        shutil.copy2(json_file, dest)

    for custom in install.custom_fonts:
        make_writable(custom)
        custom.unlink(missing_ok=True)

    cfg = load_config()
    cfg["last_version"] = install.version_id
    save_config(cfg)
    return install


def launch_roblox(install: RobloxInstall | None = None) -> None:
    install = install or find_roblox()
    if install is None:
        raise FileNotFoundError("Roblox non trovato.")

    exe = install.player_exe
    if not exe.is_file():
        raise FileNotFoundError("RobloxPlayerBeta.exe non trovato.")

    cwd = str(install.version_dir)
    log(f"launch {exe}")

    def wait_running(timeout: float = 8.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if roblox_running():
                return True
            time.sleep(0.25)
        return False

    # Come il collegamento ufficiale: ShellExecute, non come figlio di pythonw.
    for shortcut in _player_shortcuts():
        try:
            os.startfile(str(shortcut))
            log(f"started shortcut {shortcut}")
            if wait_running():
                return
        except OSError as exc:
            log(f"shortcut failed {shortcut}: {exc}")

    rc = ctypes.windll.shell32.ShellExecuteW(None, "open", str(exe), None, cwd, 1)
    if rc > 32 and wait_running():
        return
    log(f"ShellExecute rc={rc}")

    subprocess.Popen(
        ["cmd.exe", "/c", "start", "", "/D", cwd, str(exe)],
        cwd=cwd,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if wait_running():
        return
    raise FileNotFoundError(
        "Roblox non si è avviato. Prova ad aprirlo dal menu Start, poi riprova da SolaX."
    )


def _player_shortcuts() -> list[Path]:
    home = Path(os.environ.get("USERPROFILE", ""))
    appdata = Path(os.environ.get("APPDATA", ""))
    return [
        p
        for p in (
            appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Roblox" / "Roblox Player.lnk",
            home / "Desktop" / "Roblox Player.lnk",
            appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Roblox.lnk",
        )
        if p.is_file()
    ]


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def font_family_name(path: str | Path) -> str:
    """Legge il nome famiglia da un file TTF/OTF/TTC."""
    file_path = Path(path)
    try:
        data = file_path.read_bytes()
    except OSError:
        return file_path.stem

    try:
        name = _parse_family_name(data)
    except (struct.error, IndexError, ValueError):
        name = ""
    return name or file_path.stem


def _parse_family_name(data: bytes) -> str:
    if len(data) < 12:
        return ""

    offsets = [0]
    if data[:4] == b"ttcf":
        num_fonts = _u32(data, 8)
        offsets = [_u32(data, 12 + i * 4) for i in range(min(num_fonts, 8))]

    for font_offset in offsets:
        name = _parse_name_table(data, font_offset)
        if name:
            return name
    return ""


def _parse_name_table(data: bytes, font_offset: int) -> str:
    if font_offset + 12 > len(data):
        return ""
    num_tables = _u16(data, font_offset + 4)
    rec = font_offset + 12
    name_off = None
    for _ in range(num_tables):
        if rec + 16 > len(data):
            break
        tag = data[rec : rec + 4]
        if tag == b"name":
            name_off = _u32(data, rec + 8)
            break
        rec += 16
    if name_off is None or name_off + 6 > len(data):
        return ""

    count = _u16(data, name_off + 2)
    string_offset = _u16(data, name_off + 4)
    records = name_off + 6

    # Prefer typographic family (16), then family (1), then full name (4).
    ranked: list[tuple[int, int, int, str]] = []
    for i in range(count):
        entry = records + i * 12
        if entry + 12 > len(data):
            break
        platform_id = _u16(data, entry)
        encoding_id = _u16(data, entry + 2)
        language_id = _u16(data, entry + 4)
        name_id = _u16(data, entry + 6)
        length = _u16(data, entry + 8)
        offset = _u16(data, entry + 10)
        if name_id not in {1, 4, 16}:
            continue
        start = name_off + string_offset + offset
        raw = data[start : start + length]
        decoded = _decode_name(raw, platform_id, encoding_id)
        if not decoded:
            continue
        platform_rank = 0 if platform_id == 3 else 1 if platform_id == 0 else 2
        lang_rank = 0 if language_id in {0x0409, 0x0000, 0x009} else 1
        name_rank = {16: 0, 1: 1, 4: 2}[name_id]
        ranked.append((platform_rank, lang_rank, name_rank, decoded))

    if not ranked:
        return ""
    ranked.sort()
    return ranked[0][3]


def _decode_name(raw: bytes, platform_id: int, encoding_id: int) -> str:
    if not raw:
        return ""
    utf16 = platform_id in {0, 3} or encoding_id in {1, 10}
    if utf16 and len(raw) % 2 == 0:
        try:
            text = raw.decode("utf-16-be").replace("\x00", "").strip()
            if text:
                return text
        except UnicodeDecodeError:
            pass
    text = raw.decode("latin-1", errors="ignore").replace("\x00", "").strip()
    return text


def windows_font_dirs() -> list[Path]:
    dirs = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
    ]
    return [d for d in dirs if d.is_dir()]


def list_windows_fonts() -> list[tuple[str, Path]]:
    """Elenca (nome famiglia, percorso) dei font TTF/OTF installati."""
    seen: dict[str, Path] = {}
    for folder in windows_font_dirs():
        for pattern in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            for file_path in folder.glob(pattern):
                family = font_family_name(file_path)
                key = family.lower()
                if key not in seen:
                    seen[key] = file_path
    items = [(font_family_name(path), path) for path in seen.values()]
    items.sort(key=lambda item: item[0].lower())
    return items
