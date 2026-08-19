"""Stretched solo su Roblox: Windows resta nativo, il gioco viene schiacciato."""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

import roblox_fonts as rf

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_BORDER = 0x00800000
WS_POPUP = 0x80000000
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
SWP_NOSENDCHANGING = 0x0400
HWND_TOP = 0
HWND_TOPMOST = -1
MONITOR_DEFAULTTONEAREST = 2
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_RESTORE = 9
SW_SHOW = 5
SW_MAXIMIZE = 3
LONG_PTR = ctypes.c_ssize_t

PRESETS = {
    "4:3": 4 / 3,
    "5:4": 5 / 4,
    "16:10": 16 / 10,
    "4:3 extreme": 4 / 3,
}

PRESET_LABELS = ["4:3", "5:4", "16:10", "4:3 extreme"]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


_watcher_stop = threading.Event()
_watcher_thread: threading.Thread | None = None

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.MonitorFromWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
user32.MonitorFromWindow.restype = wintypes.HANDLE
user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = LONG_PTR
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
user32.SetWindowLongPtrW.restype = LONG_PTR
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]


def gbs_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Roblox" / "GlobalBasicSettings_13.xml"


def gbs_backup_path() -> Path:
    return rf.app_data_dir() / "backups" / "GlobalBasicSettings_13.xml"


def _ensure_gbs_backup() -> None:
    src = gbs_path()
    dest = gbs_backup_path()
    if src.is_file() and not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _set_bool(xml: str, name: str, value: bool) -> str:
    token = "true" if value else "false"
    pattern = rf'(<bool name="{name}">)(true|false)(</bool>)'
    if re.search(pattern, xml):
        return re.sub(pattern, rf"\g<1>{token}\g<3>", xml)
    return xml.replace(
        "</Properties>",
        f'\t\t\t<bool name="{name}">{token}</bool>\n\t\t</Properties>',
        1,
    )


def _set_vector2(xml: str, name: str, x: int, y: int) -> str:
    pattern = rf'(<Vector2 name="{name}">\s*<X>)([^<]+)(</X>\s*<Y>)([^<]+)(</Y>)'
    if re.search(pattern, xml, flags=re.S):
        return re.sub(pattern, rf"\g<1>{x}\g<3>{y}\g<5>", xml, flags=re.S)
    return xml


def monitor_size() -> tuple[int, int]:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def render_size(preset: str) -> tuple[int, int]:
    mon_w, mon_h = monitor_size()
    ratio = PRESETS.get(preset, 4 / 3)
    height = mon_h
    width = int(round(mon_h * ratio))
    if preset == "4:3 extreme":
        width = int(round(mon_h * (4 / 3) * 0.85))
    width = max(800, min(width, mon_w))
    return width, height


def apply_windowed_maximized() -> None:
    path = gbs_path()
    if not path.is_file():
        rf.log("window: GlobalBasicSettings_13.xml non trovato")
        return
    xml = path.read_text(encoding="utf-8")
    mon_w, mon_h = monitor_size()
    xml = _set_bool(xml, "Fullscreen", False)
    xml = _set_bool(xml, "StartMaximized", True)
    xml = _set_vector2(xml, "StartScreenSize", max(1280, mon_w), max(720, mon_h))
    xml = _set_vector2(xml, "StartScreenPosition", 0, 0)
    rf.make_writable(path)
    path.write_text(xml, encoding="utf-8")
    rf.log(f"window: bordered maximized {mon_w}x{mon_h}")


def restore_window_chrome(hwnd: int) -> None:
    if not hwnd or not user32.IsWindow(hwnd):
        return
    style = int(user32.GetWindowLongPtrW(hwnd, GWL_STYLE))
    style |= WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
    style &= ~WS_POPUP
    user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    flags = SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_NOSENDCHANGING
    user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, flags | 0x0001 | 0x0002)


def start_max_watcher() -> None:
    global _watcher_thread
    stop_stretch_watcher()
    _watcher_stop.clear()

    def work():
        apply_windowed_maximized()
        deadline = time.time() + 60
        hwnd = 0
        while time.time() < deadline and not _watcher_stop.is_set():
            hwnd = find_roblox_hwnd()
            if hwnd:
                break
            time.sleep(0.3)
        if not hwnd:
            rf.log("window: finestra Roblox non trovata")
            return
        for _ in range(16):
            if _watcher_stop.is_set():
                return
            current = find_roblox_hwnd() or hwnd
            restore_window_chrome(current)
            time.sleep(0.6)

    _watcher_thread = threading.Thread(target=work, daemon=True)
    _watcher_thread.start()


def restore_gbs() -> None:
    backup = gbs_backup_path()
    path = gbs_path()
    if backup.is_file() and path.parent.is_dir():
        rf.make_writable(path)
        shutil.copy2(backup, path)


def _pid_image(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buf))
        kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        return buf.value
    finally:
        kernel32.CloseHandle(h)


def _class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def find_roblox_hwnd() -> int:
    found: list[tuple[int, int]] = []

    def callback(hwnd, _lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        image = _pid_image(pid.value).lower()
        if not image.endswith("robloxplayerbeta.exe"):
            return True
        if not user32.IsWindow(hwnd):
            return True
        cls = _class_name(hwnd).upper()
        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        width = max(0, rect.right - rect.left)
        height = max(0, rect.bottom - rect.top)
        area = width * height
        score = area
        if "WINDOWSCLIENT" in cls or cls == "ROBLOX":
            score += 10_000_000
        if area < 100 * 100 and "WINDOWSCLIENT" not in cls:
            return True
        found.append((score, int(hwnd)))
        return True

    enum_proc = WNDENUMPROC(callback)
    user32.EnumWindows(enum_proc, 0)
    if not found:
        return 0
    found.sort(reverse=True)
    return found[0][1]


def _monitor_rect(hwnd: int) -> tuple[int, int, int, int]:
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        r = info.rcMonitor
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    w, h = monitor_size()
    return 0, 0, w, h


def stretch_window(hwnd: int) -> None:
    if not hwnd or not user32.IsWindow(hwnd):
        return
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.ShowWindow(hwnd, SW_SHOW)
    style = int(user32.GetWindowLongPtrW(hwnd, GWL_STYLE))
    style &= ~(
        WS_CAPTION
        | WS_THICKFRAME
        | WS_MINIMIZEBOX
        | WS_MAXIMIZEBOX
        | WS_SYSMENU
        | WS_BORDER
    )
    style |= WS_POPUP
    user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)
    x, y, mw, mh = _monitor_rect(hwnd)
    flags = SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_NOSENDCHANGING
    user32.SetWindowPos(hwnd, HWND_TOP, x, y, mw, mh, flags)


def start_stretch_watcher(preset: str) -> None:
    spawn_stretch_helper(preset)
    global _watcher_thread
    stop_stretch_watcher()
    _watcher_stop.clear()

    def work():
        _stretch_loop(preset, _watcher_stop)

    _watcher_thread = threading.Thread(target=work, daemon=True)
    _watcher_thread.start()


def spawn_stretch_helper(preset: str) -> None:
    if getattr(sys, "frozen", False):
        args = [sys.executable, "--stretch-watch", preset]
    else:
        app = Path(__file__).resolve().parent / "app.py"
        args = [sys.executable, str(app), "--stretch-watch", preset]
    flags = 0
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        flags |= subprocess.CREATE_NEW_PROCESS_GROUP
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flags |= subprocess.CREATE_NO_WINDOW
    flags |= 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
    try:
        subprocess.Popen(args, close_fds=False, creationflags=flags)
        rf.log(f"stretch helper: {' '.join(args)}")
    except OSError as exc:
        rf.log(f"stretch helper failed: {exc}")


def _stretch_loop(preset: str, stop_event) -> None:
    deadline = time.time() + 90
    hwnd = 0
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            return
        hwnd = find_roblox_hwnd()
        if hwnd:
            break
        time.sleep(0.3)
    if not hwnd:
        rf.log("stretch: finestra Roblox non trovata")
        return
    rw, rh = render_size(preset)
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, rw, rh, SWP_FRAMECHANGED | SWP_SHOWWINDOW)
    time.sleep(0.4)
    stretch_window(hwnd)
    rf.log(f"stretch: applied hwnd={hwnd} render={rw}x{rh}")
    while rf.roblox_running():
        if stop_event is not None and stop_event.is_set():
            return
        current = find_roblox_hwnd() or hwnd
        stretch_window(current)
        time.sleep(0.8)


def apply_gbs_stretched(preset: str) -> None:
    _stretch_loop(preset, None)


def run_stretch_watch(preset: str) -> None:
    _stretch_loop(preset, None)


def stop_stretch_watcher() -> None:
    _watcher_stop.set()
