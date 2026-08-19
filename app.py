"""SolaX — launcher locale per Roblox (font + FastFlag)."""

from __future__ import annotations

import ctypes
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox
from PIL import Image, ImageTk
import customtkinter as ctk

import roblox_flags as rff
import roblox_fonts as rf
import roblox_headless as rh
import roblox_korblox as rk
import roblox_mods as rm
import roblox_stretch as rst

VERSION = "1.0.7"
FR_PRIVATE = 0x10

BG = "#1a1a1a"
SURFACE = "#2c2c2c"
SURFACE_HOVER = "#353535"
BORDER = "#3d3d3d"
TEXT = "#ffffff"
MUTED = "#9a9a9a"
PURPLE = "#b794f6"
PURPLE_BTN = "#7c5cfc"
PURPLE_BTN_HOVER = "#8f74ff"
FOOTER_BG = "#141414"
NAV_ACTIVE = "#252525"
HOME_SIZE = "560x300"
HOME_MIN = (520, 270)
SETTINGS_SIZE = "1040x740"
SETTINGS_MIN = (880, 600)


def resource_path(*parts: str) -> Path:
    here = Path(__file__).resolve().parent
    candidates = [here.joinpath(*parts)]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        mei = Path(getattr(sys, "_MEIPASS", exe_dir))
        candidates = [
            mei.joinpath(*parts),
            exe_dir.joinpath(*parts),
            here.joinpath(*parts),
        ]
    for path in candidates:
        if path.is_file() or path.is_dir():
            return path
    return candidates[0]


def icon_family() -> str:
    available = set(tkfont.families())
    for name in ("Segoe Fluent Icons", "Segoe MDL2 Assets"):
        if name in available:
            return name
    return "Segoe UI Symbol"


def dark_titlebar(window) -> None:
    try:
        window.update()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), 4)
    except Exception:
        pass


def bind_all(widget, sequence, handler) -> None:
    widget.bind(sequence, handler)
    for child in widget.winfo_children():
        bind_all(child, sequence, handler)


class MenuTile(ctk.CTkFrame):
    def __init__(self, master, icon: str, title: str, command, subtitle: str | None = None, height: int = 56):
        super().__init__(
            master,
            fg_color=SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=BORDER,
            height=height,
            cursor="hand2",
        )
        self._command = command
        self.pack_propagate(False)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=8)

        ctk.CTkLabel(
            inner,
            text=icon,
            font=ctk.CTkFont(family=icon_family(), size=16),
            text_color=TEXT,
            width=22,
        ).pack(side="left")

        text_col = ctk.CTkFrame(inner, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True, padx=(12, 8))
        ctk.CTkLabel(
            text_col,
            text=title,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14),
            text_color=TEXT,
            anchor="w",
        ).pack(fill="x")
        if subtitle:
            ctk.CTkLabel(
                text_col,
                text=subtitle,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color=MUTED,
                anchor="w",
            ).pack(fill="x")

        ctk.CTkLabel(
            inner,
            text="\uE76C",
            font=ctk.CTkFont(family=icon_family(), size=12),
            text_color=MUTED,
            width=16,
        ).pack(side="right")

        bind_all(self, "<Enter>", self._on_enter)
        bind_all(self, "<Leave>", self._on_leave)
        bind_all(self, "<Button-1>", self._on_click)

    def _contains_pointer(self) -> bool:
        try:
            widget = self.winfo_containing(*self.winfo_pointerxy())
        except Exception:
            return False
        while widget is not None:
            if widget == self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _on_enter(self, _event=None):
        self.configure(fg_color=SURFACE_HOVER)

    def _on_leave(self, _event=None):
        if not self._contains_pointer():
            self.configure(fg_color=SURFACE)

    def _on_click(self, _event=None):
        if self._command:
            self._command()


class SidebarItem(ctk.CTkFrame):
    def __init__(self, master, icon: str, title: str, command, selected: bool = False):
        super().__init__(master, fg_color="transparent", height=42, cursor="hand2")
        self._command = command
        self._selected = selected
        self.pack_propagate(False)

        self.bar = ctk.CTkFrame(self, width=3, corner_radius=1, fg_color="transparent")
        self.bar.pack(side="left", fill="y", pady=8)

        self.inner = ctk.CTkFrame(self, fg_color="transparent", corner_radius=6)
        self.inner.pack(side="left", fill="both", expand=True, padx=(8, 10), pady=4)

        row = ctk.CTkFrame(self.inner, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=10)
        ctk.CTkLabel(
            row,
            text=icon,
            font=ctk.CTkFont(family=icon_family(), size=15),
            text_color=TEXT,
            width=22,
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT,
            anchor="w",
        ).pack(side="left", padx=(10, 0))

        self.set_selected(selected)
        bind_all(self, "<Button-1>", lambda _e: self._command())

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self.bar.configure(fg_color=PURPLE)
            self.inner.configure(fg_color=NAV_ACTIVE)
        else:
            self.bar.configure(fg_color="transparent")
            self.inner.configure(fg_color="transparent")


class FooterButton(ctk.CTkButton):
    def __init__(self, master, text: str, command, primary: bool = False, width: int = 130):
        if primary:
            super().__init__(
                master,
                text=text,
                command=command,
                width=width,
                height=36,
                corner_radius=8,
                fg_color=PURPLE_BTN,
                hover_color=PURPLE_BTN_HOVER,
                text_color=TEXT,
                font=ctk.CTkFont(family="Segoe UI Semibold", size=13),
            )
        else:
            super().__init__(
                master,
                text=text,
                command=command,
                width=width,
                height=36,
                corner_radius=8,
                fg_color=SURFACE,
                hover_color=SURFACE_HOVER,
                border_width=1,
                border_color=BORDER,
                text_color=TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=13),
            )


class App(ctk.CTk):
    def __init__(self, auto: bool = False):
        super().__init__()
        self._auto_mode = auto
        ctk.set_appearance_mode("dark")
        self.title("SolaX")
        self.configure(fg_color=BG)
        self.geometry(HOME_SIZE)
        self.minsize(*HOME_MIN)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SolaX.App")
        except Exception:
            pass
        self._apply_app_icon()

        self.selected_font: Path | None = None
        self.selected_family = ""
        self.windows_fonts: list[tuple[str, Path]] = []
        self._loaded_font_path: str | None = None
        self._preview_font: tkfont.Font | None = None
        self._busy = False
        self._page = "home"
        self.nav_items: dict[str, SidebarItem] = {}

        cfg = rf.load_config()
        last = cfg.get("last_font")
        if last and Path(last).is_file():
            self.selected_font = Path(last)
            self.selected_family = cfg.get("last_font_name") or rf.font_family_name(self.selected_font)

        self.use_font_var = ctk.BooleanVar(value=bool(cfg.get("use_custom_font", True if self.selected_font else False)))
        self.use_sky_var = ctk.BooleanVar(value=bool(cfg.get("use_custom_sky", False)))
        self.use_shift_var = ctk.BooleanVar(value=bool(cfg.get("use_shift_lock", False)))
        self.use_korblox_var = ctk.BooleanVar(value=bool(cfg.get("use_korblox", False)))
        self.test_mode_var = ctk.BooleanVar(value=bool(cfg.get("test_mode", False)))
        fflags = {**rff.DEFAULT_FFLAGS, **(cfg.get("fflags") or {})}
        self.unlock_fps_var = ctk.BooleanVar(value=bool(fflags.get("unlock_fps", False)))
        self.fps_var = ctk.StringVar(value=str(fflags.get("fps", 240)))
        self.postfx_var = ctk.BooleanVar(value=bool(fflags.get("disable_postfx", False)))
        self.shadows_var = ctk.BooleanVar(
            value=bool(fflags.get("disable_shadows", fflags.get("reduce_shadows", False)))
        )
        self.textures_var = ctk.BooleanVar(value=bool(fflags.get("low_textures", False)))
        self.low_quality_var = ctk.BooleanVar(value=bool(fflags.get("low_quality", False)))
        self.particles_var = ctk.BooleanVar(value=bool(fflags.get("disable_particles", False)))
        self.msaa_var = ctk.BooleanVar(value=bool(fflags.get("no_msaa", False)))
        self.lights_var = ctk.BooleanVar(value=bool(fflags.get("low_lights", False)))
        self.clouds_var = ctk.BooleanVar(value=bool(fflags.get("no_clouds", False)))
        self.alt_enter_var = ctk.BooleanVar(value=bool(fflags.get("alt_enter_fullscreen", False)))
        self.dpi_var = ctk.BooleanVar(value=bool(fflags.get("disable_dpi_scale", False)))
        self.d3d11_var = ctk.BooleanVar(value=bool(fflags.get("prefer_d3d11", False)))
        self.vulkan_var = ctk.BooleanVar(value=bool(fflags.get("prefer_vulkan", False)))
        self.gray_sky_var = ctk.BooleanVar(value=bool(fflags.get("gray_sky", False)))
        self.grass_var = ctk.BooleanVar(value=bool(fflags.get("freeze_grass", False)))
        self.custom_flags: dict[str, str] = {
            str(k): str(v) for k, v in (cfg.get("custom_fflags") or {}).items()
        }
        self.flag_name_var = ctk.StringVar(value="")
        self.flag_value_var = ctk.StringVar(value="")
        self.font_search_var = ctk.StringVar(value="")
        self.font_search_var.trace_add("write", lambda *_: self._rebuild_font_list())
        self.sky_png: Path | None = Path(cfg["sky_png"]) if cfg.get("sky_png") and Path(cfg["sky_png"]).is_file() else None
        self.shift_png: Path | None = (
            Path(cfg["shift_lock_png"]) if cfg.get("shift_lock_png") and Path(cfg["shift_lock_png"]).is_file() else None
        )
        self._font_rows: list[tuple[ctk.CTkFrame, Path]] = []
        self._ready = False
        self._persist_job: str | None = None
        self._settings_tab = cfg.get("settings_tab") or "integrations"
        if self._settings_tab == "robux":
            self._settings_tab = "integrations"

        self.home = ctk.CTkFrame(self, fg_color=BG)
        self.settings = ctk.CTkFrame(self, fg_color=BG)
        self._build_home()
        self._build_settings()
        self._bind_persist()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._ready = True
        try:
            rk.ensure_korblox_mesh()
        except Exception as exc:
            rf.log(f"korblox mesh: {exc}")
        if self._auto_mode:
            self.withdraw()
            self.after(120, self._run_auto)
        else:
            self.show_home()
            self.after(50, lambda: dark_titlebar(self))
            self.after(80, self._load_windows_fonts_async)

    def _run_auto(self):
        self.save_settings(True, silent=True)

    def _auto_quit_if_idle(self):
        if rf.roblox_running():
            self.after(8000, self._auto_quit_if_idle)
            return
        self.destroy()

    def _build_home(self):
        left = ctk.CTkFrame(self.home, fg_color=BG, width=170)
        left.pack(side="left", fill="y", padx=(18, 8), pady=14)
        left.pack_propagate(False)

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(fill="x", pady=(18, 0))
        logo = resource_path("website", "icon.png")
        if logo.is_file():
            try:
                raw = Image.open(logo).convert("RGBA")
                self._home_logo = ctk.CTkImage(light_image=raw, dark_image=raw, size=(36, 36))
                ctk.CTkLabel(title_row, image=self._home_logo, text="").pack(side="left", padx=(0, 10))
            except Exception:
                pass
        ctk.CTkLabel(
            title_row,
            text="SolaX",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=26),
            text_color=TEXT,
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            left,
            text=f"Version {VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        about_row = ctk.CTkFrame(left, fg_color="transparent", cursor="hand2")
        about_row.pack(side="bottom", fill="x", pady=(0, 4))
        ctk.CTkLabel(
            about_row,
            text="\uE946",
            font=ctk.CTkFont(family=icon_family(), size=12),
            text_color=PURPLE,
            width=18,
            cursor="hand2",
        ).pack(side="left")
        about = ctk.CTkLabel(
            about_row,
            text="About SolaX",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PURPLE,
            anchor="w",
            cursor="hand2",
        )
        about.pack(side="left")
        bind_all(about_row, "<Button-1>", lambda _e: self._about())

        web_row = ctk.CTkFrame(left, fg_color="transparent", cursor="hand2")
        web_row.pack(side="bottom", fill="x", pady=(0, 2))
        ctk.CTkLabel(
            web_row,
            text="\uE774",
            font=ctk.CTkFont(family=icon_family(), size=12),
            text_color=PURPLE,
            width=18,
            cursor="hand2",
        ).pack(side="left")
        web = ctk.CTkLabel(
            web_row,
            text="Website",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=PURPLE,
            anchor="w",
            cursor="hand2",
        )
        web.pack(side="left")
        bind_all(web_row, "<Button-1>", lambda _e: self._open_website())

        right = ctk.CTkFrame(self.home, fg_color=BG)
        right.pack(side="left", fill="both", expand=True, padx=(4, 16), pady=18)

        MenuTile(right, "\uE7FC", "Launch Roblox", self.launch_from_home).pack(fill="x", pady=(18, 8))
        MenuTile(right, "\uE713", "Settings", self.show_settings).pack(fill="x")

    def _build_settings(self):
        body = ctk.CTkFrame(self.settings, fg_color=BG)
        body.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(body, fg_color=BG, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="SETTINGS",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", padx=22, pady=(22, 10))

        self.nav_items["integrations"] = SidebarItem(
            sidebar, "\uE710", "Integrations", lambda: self._show_tab("integrations"), True
        )
        self.nav_items["integrations"].pack(fill="x", padx=8)
        self.nav_items["fastflag"] = SidebarItem(
            sidebar, "\uE7C1", "FastFlag", lambda: self._show_tab("fastflag"), False
        )
        self.nav_items["fastflag"].pack(fill="x", padx=8)

        ctk.CTkLabel(
            sidebar,
            text="BOOST",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", padx=22, pady=(18, 8))

        self.nav_items["graphics"] = SidebarItem(
            sidebar, "\uE7F4", "Graphics", lambda: self._show_tab("graphics"), False
        )
        self.nav_items["graphics"].pack(fill="x", padx=8)
        self.nav_items["premium"] = SidebarItem(
            sidebar, "\uE735", "Korblox", lambda: self._show_tab("premium"), False
        )
        self.nav_items["premium"].pack(fill="x", padx=8)

        ctk.CTkFrame(body, width=1, fg_color=BORDER).pack(side="left", fill="y")

        content = ctk.CTkFrame(body, fg_color=BG)
        content.pack(side="left", fill="both", expand=True)

        self.integrations_page = ctk.CTkScrollableFrame(content, fg_color=BG, corner_radius=0)
        self.fastflag_page = ctk.CTkScrollableFrame(content, fg_color=BG, corner_radius=0)
        self.graphics_page = ctk.CTkScrollableFrame(content, fg_color=BG, corner_radius=0)
        self.premium_page = ctk.CTkFrame(content, fg_color=BG)
        self._build_integrations(self.integrations_page)
        self._build_fastflag(self.fastflag_page)
        self._build_graphics(self.graphics_page)
        self._build_premium(self.premium_page)

        footer = ctk.CTkFrame(self.settings, fg_color=FOOTER_BG, height=64, corner_radius=0)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        test_wrap = ctk.CTkFrame(footer, fg_color="transparent")
        test_wrap.pack(side="left", padx=22)
        ctk.CTkLabel(
            test_wrap,
            text="Test mode",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkSwitch(
            test_wrap,
            text="",
            variable=self.test_mode_var,
            progress_color=PURPLE_BTN,
            button_color=TEXT,
            fg_color="#3a3a3a",
            width=44,
            switch_width=36,
        ).pack(side="left")

        self._footer_status = ctk.CTkLabel(
            footer,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
        )
        self._footer_status.pack(side="left", padx=(8, 0))

        btns = ctk.CTkFrame(footer, fg_color="transparent")
        btns.pack(side="right", padx=18)
        self._btn_close = FooterButton(btns, "Close", self.show_home, width=100)
        self._btn_close.pack(side="right", padx=(8, 0))
        self._btn_save = FooterButton(btns, "Save", lambda: self.save_settings(False), width=100)
        self._btn_save.pack(side="right", padx=(8, 0))
        self._btn_launch = FooterButton(
            btns, "Save and Launch", lambda: self.save_settings(True), primary=True, width=150
        )
        self._btn_launch.pack(side="right")

    def _page_header(self, parent, icon: str, title: str, subtitle: str):
        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(22, 8))
        title_row = ctk.CTkFrame(head, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(
            title_row,
            text=icon,
            font=ctk.CTkFont(family=icon_family(), size=22),
            text_color=TEXT,
            width=28,
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text=title,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=26),
            text_color=TEXT,
            anchor="w",
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            head,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

    def _card(self, parent) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="x", padx=28, pady=(8, 0))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        return inner

    def _switch_row(self, parent, title: str, subtitle: str, variable: ctk.BooleanVar):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=8)
        texts = ctk.CTkFrame(row, fg_color="transparent")
        texts.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            texts,
            text=title,
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14),
            text_color=TEXT,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            texts,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        ).pack(fill="x")
        ctk.CTkSwitch(
            row,
            text="",
            variable=variable,
            progress_color=PURPLE_BTN,
            button_color=TEXT,
            fg_color="#3a3a3a",
            width=44,
            switch_width=36,
        ).pack(side="right", padx=(12, 0))

    def _build_integrations(self, parent):
        self._page_header(
            parent,
            "\uE710",
            "Integrations",
            "Font, cielo e shift lock — solo su Roblox",
        )

        font_card = self._card(parent)
        self._switch_row(
            font_card,
            "Custom font",
            "Sostituisce il font delle parole nel client Roblox.",
            self.use_font_var,
        )

        search = ctk.CTkEntry(
            font_card,
            textvariable=self.font_search_var,
            placeholder_text="Cerca font…",
            height=34,
            corner_radius=8,
            fg_color="#1f1f1f",
            border_color=BORDER,
            text_color=TEXT,
        )
        search.pack(fill="x", pady=(8, 8))

        picker = ctk.CTkFrame(font_card, fg_color="transparent")
        picker.pack(fill="x", pady=(0, 8))
        self.font_name_label = ctk.CTkLabel(
            picker,
            text=self.selected_family or "Nessun font selezionato",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=14),
            text_color=TEXT,
            anchor="w",
        )
        self.font_name_label.pack(side="left", fill="x", expand=True)
        FooterButton(picker, "Scegli file .ttf", self.pick_file, width=130).pack(side="right")

        self.font_list = ctk.CTkScrollableFrame(
            font_card,
            height=230,
            fg_color="#1f1f1f",
            corner_radius=8,
            border_width=1,
            border_color=BORDER,
        )
        self.font_list.pack(fill="x", pady=(0, 10))
        self._rebuild_font_list()

        self.preview = ctk.CTkLabel(
            font_card,
            text="Ciao Roblox  123  ABC abc  Le scritte cambiano così",
            font=ctk.CTkFont(family="Segoe UI", size=20),
            text_color=TEXT,
            anchor="w",
        )
        self.preview.pack(fill="x", pady=(4, 0))

        sky_card = self._card(parent)
        self._switch_row(
            sky_card,
            "Custom sky",
            "Cambia il cielo di default. Aggiungi un PNG (vale per tutte le facce).",
            self.use_sky_var,
        )
        self.sky_row = self._png_picker_row(
            sky_card,
            self.sky_png,
            "Scegli PNG cielo",
            self.pick_sky,
        )
        self.sky_name_label, self.sky_preview_label = self.sky_row

        shift_card = self._card(parent)
        self._switch_row(
            shift_card,
            "Shift lock",
            "Cambia l’icona del mouse quando usi lo shift lock. Aggiungi un PNG.",
            self.use_shift_var,
        )
        self.shift_row = self._png_picker_row(
            shift_card,
            self.shift_png,
            "Scegli PNG shift lock",
            self.pick_shift_lock,
        )
        self.shift_name_label, self.shift_preview_label = self.shift_row

    def _png_picker_row(self, parent, path: Path | None, button_text: str, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        preview = ctk.CTkLabel(row, text="", width=72, height=72, fg_color="#1f1f1f", corner_radius=8)
        preview.pack(side="left", padx=(0, 12))
        texts = ctk.CTkFrame(row, fg_color="transparent")
        texts.pack(side="left", fill="x", expand=True)
        name = ctk.CTkLabel(
            texts,
            text=path.name if path else "Nessun PNG selezionato",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=13),
            text_color=TEXT,
            anchor="w",
        )
        name.pack(fill="x")
        ctk.CTkLabel(
            texts,
            text="File .png",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x")
        FooterButton(row, button_text, command, width=160).pack(side="right")
        if path:
            self._set_thumb(preview, path)
        return name, preview

    def _set_thumb(self, label: ctk.CTkLabel, path: Path, size: tuple[int, int] = (72, 72)):
        try:
            image = Image.open(path).convert("RGBA")
            image.thumbnail(size, Image.Resampling.LANCZOS)
            copy = image.copy()
            thumb = ctk.CTkImage(light_image=copy, dark_image=copy, size=copy.size)
            label.configure(image=thumb, text="")
            label._solax_thumb = thumb
        except Exception:
            label.configure(image=None, text="PNG")

    def _build_fastflag(self, parent):
        self._page_header(
            parent,
            "\uE7C1",
            "FastFlag",
            "Flag del client Roblox. Quelle non in allowlist vengono ignorate.",
        )
        card = self._card(parent)

        self._switch_row(
            card,
            "Unlock FPS",
            "Alza il limite FPS del client (valore sotto).",
            self.unlock_fps_var,
        )

        fps_row = ctk.CTkFrame(card, fg_color="transparent")
        fps_row.pack(fill="x", pady=(4, 10))
        ctk.CTkLabel(
            fps_row,
            text="FPS target",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT,
        ).pack(side="left")
        self.fps_entry = ctk.CTkEntry(
            fps_row,
            textvariable=self.fps_var,
            width=90,
            height=32,
            corner_radius=8,
            fg_color="#1f1f1f",
            border_color=BORDER,
            text_color=TEXT,
        )
        self.fps_entry.pack(side="right")

        self._switch_row(
            card,
            "Alt+Enter fullscreen",
            "Gestione fullscreen classica con Alt+Invio.",
            self.alt_enter_var,
        )
        self._switch_row(
            card,
            "Disable DPI scale",
            "Ignora lo scaling di Windows (125%, 150%).",
            self.dpi_var,
        )
        self._switch_row(
            card,
            "Prefer D3D11",
            "Usa Direct3D 11 come renderer.",
            self.d3d11_var,
        )
        self._switch_row(
            card,
            "Prefer Vulkan",
            "Usa Vulkan come renderer.",
            self.vulkan_var,
        )
        self._switch_row(
            card,
            "Gray sky",
            "Cielo grigio, meno effetti in atmosfera.",
            self.gray_sky_var,
        )
        self._switch_row(
            card,
            "Freeze grass",
            "Blocca il movimento dell’erba.",
            self.grass_var,
        )

        editor = self._card(parent)
        ctk.CTkLabel(
            editor,
            text="FastFlag Editor",
            font=ctk.CTkFont(family="Segoe UI Semibold", size=16),
            text_color=TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            editor,
            text="Aggiungi una flag a mano (nome + valore).",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        add_row = ctk.CTkFrame(editor, fg_color="transparent")
        add_row.pack(fill="x")
        self.flag_name_entry = ctk.CTkEntry(
            add_row,
            textvariable=self.flag_name_var,
            placeholder_text="Nome flag  es. DFFlagDisableDPIScale",
            height=34,
            corner_radius=8,
            fg_color="#1f1f1f",
            border_color=BORDER,
            text_color=TEXT,
        )
        self.flag_name_entry.pack(side="left", fill="x", expand=True)
        self.flag_value_entry = ctk.CTkEntry(
            add_row,
            textvariable=self.flag_value_var,
            placeholder_text="Valore  true",
            width=110,
            height=34,
            corner_radius=8,
            fg_color="#1f1f1f",
            border_color=BORDER,
            text_color=TEXT,
        )
        self.flag_value_entry.pack(side="left", padx=(8, 8))
        FooterButton(add_row, "Add", self._add_custom_flag, primary=True, width=80).pack(side="right")

        self.flag_list = ctk.CTkScrollableFrame(
            editor,
            height=180,
            fg_color="#1f1f1f",
            corner_radius=8,
            border_width=1,
            border_color=BORDER,
        )
        self.flag_list.pack(fill="x", pady=(12, 0))
        self._rebuild_flag_list()

    def _rebuild_flag_list(self):
        if not hasattr(self, "flag_list"):
            return
        for child in self.flag_list.winfo_children():
            child.destroy()
        if not self.custom_flags:
            ctk.CTkLabel(
                self.flag_list,
                text="Nessuna flag extra. Aggiungine una sopra.",
                text_color=MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=12),
            ).pack(pady=14)
            return
        for name in sorted(self.custom_flags):
            value = self.custom_flags[name]
            row = ctk.CTkFrame(self.flag_list, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text=name,
                font=ctk.CTkFont(family="Segoe UI Semibold", size=13),
                text_color=TEXT,
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(family="Consolas", size=12),
                text_color=PURPLE,
                width=90,
                anchor="e",
            ).pack(side="left", padx=(8, 8))
            FooterButton(row, "Remove", lambda n=name: self._remove_custom_flag(n), width=80).pack(side="right")

    def _add_custom_flag(self):
        name = self.flag_name_var.get().strip()
        value = self.flag_value_var.get().strip()
        if not name:
            messagebox.showwarning("FastFlag", "Scrivi il nome della flag.")
            return
        if not value:
            messagebox.showwarning("FastFlag", "Scrivi il valore della flag.")
            return
        self.custom_flags[name] = value
        self.flag_name_var.set("")
        self.flag_value_var.set("")
        self._rebuild_flag_list()
        self._persist_ui()

    def _remove_custom_flag(self, name: str):
        self.custom_flags.pop(name, None)
        self._rebuild_flag_list()
        self._persist_ui()

    def _build_graphics(self, parent):
        self._page_header(
            parent,
            "\uE7F4",
            "Graphics",
            "Disattiva effetti per potenziare FPS e fluidità",
        )
        card = self._card(parent)
        self._switch_row(
            card,
            "Disable post",
            "Toglie post-processing (bloom, filtri extra).",
            self.postfx_var,
        )
        self._switch_row(
            card,
            "Disable shadow",
            "Toglie ombre e abbassa l’intensità.",
            self.shadows_var,
        )
        self._switch_row(
            card,
            "Disable texture",
            "Abbassa la qualità delle texture per guadagnare FPS.",
            self.textures_var,
        )
        self._switch_row(
            card,
            "Low quality",
            "Forza il livello grafica più basso.",
            self.low_quality_var,
        )
        self._switch_row(
            card,
            "Disable particles",
            "Riduce particelle e effetti sparsi.",
            self.particles_var,
        )
        self._switch_row(
            card,
            "No MSAA",
            "Disattiva l’anti-aliasing.",
            self.msaa_var,
        )
        self._switch_row(
            card,
            "Low lights",
            "Taglia gli aggiornamenti delle luci locali.",
            self.lights_var,
        )
        self._switch_row(
            card,
            "No clouds",
            "Toglie le nuvole dinamiche.",
            self.clouds_var,
        )

    def _build_premium(self, parent):
        self._page_header(
            parent,
            "\uE735",
            "Korblox",
            "Sostituisce la mesh della gamba destra, solo sul tuo client",
        )
        card = self._card(parent)
        self._switch_row(
            card,
            "Korblox",
            "Mette rightleg.mesh al posto di content/avatar/meshes/rightleg.mesh. Incluso nell’exe.",
            self.use_korblox_var,
        )
        status = "Mesh Korblox pronta."
        try:
            mesh = rk.ensure_korblox_mesh()
            status = f"Mesh pronta: {mesh.name} ({mesh.stat().st_size} byte)"
        except Exception as exc:
            status = str(exc)
        ctk.CTkLabel(
            card,
            text=status,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=MUTED,
            anchor="w",
            wraplength=520,
        ).pack(fill="x", pady=(8, 0))

    def show_home(self):
        self._persist_ui()
        self._page = "home"
        self.settings.pack_forget()
        self.home.pack(fill="both", expand=True)
        self.title("SolaX")
        self.minsize(*HOME_MIN)
        self.geometry(HOME_SIZE)
        self.after(30, lambda: dark_titlebar(self))

    def show_settings(self):
        self._page = "settings"
        self.home.pack_forget()
        self.settings.pack(fill="both", expand=True)
        self.title("SolaX Settings")
        self.minsize(*SETTINGS_MIN)
        self.geometry(SETTINGS_SIZE)
        self._show_tab(self._settings_tab)
        self.after(30, lambda: dark_titlebar(self))
        if self.selected_font:
            self._update_preview()

    def _show_tab(self, name: str):
        self._settings_tab = name
        for key, item in self.nav_items.items():
            item.set_selected(key == name)
        pages = {
            "integrations": self.integrations_page,
            "fastflag": self.fastflag_page,
            "graphics": self.graphics_page,
            "premium": self.premium_page,
        }
        for page in pages.values():
            page.pack_forget()
        pages.get(name, self.integrations_page).pack(fill="both", expand=True)
        self._schedule_persist()

    def _apply_app_icon(self):
        png = resource_path("website", "icon.png")
        ico = resource_path("website", "icon.ico")
        try:
            if ico.is_file():
                self.iconbitmap(str(ico))
        except Exception:
            pass
        try:
            if png.is_file():
                img = Image.open(png).convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
                self._icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon_photo)
        except Exception:
            pass

    def _open_website(self):
        path = resource_path("website", "index.html")
        if path.is_file():
            webbrowser.open(path.as_uri())
        else:
            webbrowser.open("https://discord.gg/zq3fR5MxgU")

    def _about(self):
        messagebox.showinfo(
            "About SolaX",
            "SolaX  " + VERSION + "\n\n"
            "Launcher locale per Roblox.\n"
            "Cambia il font delle scritte e alcune FastFlag sul tuo PC.\n"
            "Non modifica quello che vedono gli altri giocatori.",
        )

    def _load_windows_fonts_async(self):
        def work():
            fonts = rf.list_windows_fonts()
            self.after(0, lambda: self._set_windows_fonts(fonts))

        threading.Thread(target=work, daemon=True).start()

    def _set_windows_fonts(self, fonts: list[tuple[str, Path]]):
        self.windows_fonts = fonts
        if self.selected_font and self.selected_family:
            if not any(p == self.selected_font for _n, p in fonts):
                self.windows_fonts = [(self.selected_family, self.selected_font), *fonts]
        self._rebuild_font_list()
        if self.selected_font:
            self._update_preview()

    def _rebuild_font_list(self):
        if not hasattr(self, "font_list"):
            return
        for child in self.font_list.winfo_children():
            child.destroy()
        self._font_rows.clear()
        query = self.font_search_var.get().strip().lower()
        shown = 0
        for name, path in self.windows_fonts:
            if query and query not in name.lower():
                continue
            self._add_font_row(name, path)
            shown += 1
            if shown >= 80:
                break
        if shown == 0:
            ctk.CTkLabel(
                self.font_list,
                text="Nessun font trovato",
                text_color=MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=13),
            ).pack(pady=16)

    def _add_font_row(self, name: str, path: Path):
        selected = self.selected_font is not None and Path(self.selected_font) == Path(path)
        row = ctk.CTkFrame(
            self.font_list,
            fg_color=NAV_ACTIVE if selected else "transparent",
            corner_radius=6,
            cursor="hand2",
        )
        try:
            row_font = ctk.CTkFont(family=name, size=17)
        except Exception:
            row_font = ctk.CTkFont(family="Segoe UI", size=17)
        label = ctk.CTkLabel(
            row,
            text=f"{name}    ABC abc 123",
            font=row_font,
            text_color=TEXT,
            anchor="w",
        )
        label.pack(fill="x", padx=12, pady=8)

        def select(_event=None, family=name, font_path=path):
            self._select_font(family, font_path)

        bind_all(row, "<Button-1>", select)
        row.pack(fill="x", pady=1)
        self._font_rows.append((row, Path(path)))

    def _select_font(self, name: str, path: Path):
        self.selected_font = Path(path)
        self.selected_family = name
        self.font_name_label.configure(text=name)
        self.use_font_var.set(True)
        for frame, font_path in self._font_rows:
            frame.configure(fg_color=NAV_ACTIVE if font_path == self.selected_font else "transparent")
        self._update_preview()
        self._persist_ui()

    def pick_file(self):
        path = filedialog.askopenfilename(
            title="Scegli un font",
            filetypes=[
                ("Font", "*.ttf *.otf *.TTF *.OTF"),
                ("TrueType", "*.ttf"),
                ("OpenType", "*.otf"),
                ("Tutti i file", "*.*"),
            ],
        )
        if not path:
            return
        font_path = Path(path)
        self.selected_font = font_path
        self.selected_family = rf.font_family_name(font_path)
        self._load_private_font(font_path)
        if not any(p == font_path for _n, p in self.windows_fonts):
            self.windows_fonts = [(self.selected_family, font_path), *self.windows_fonts]
        self.use_font_var.set(True)
        self._rebuild_font_list()
        self._select_font(self.selected_family, font_path)

    def _pick_png(self, title: str) -> Path | None:
        path = filedialog.askopenfilename(
            title=title,
            filetypes=[("PNG", "*.png *.PNG"), ("Immagini", "*.png *.jpg *.jpeg *.webp"), ("Tutti i file", "*.*")],
        )
        return Path(path) if path else None

    def pick_sky(self):
        path = self._pick_png("Scegli un PNG per il cielo")
        if not path:
            return
        self.sky_png = path
        self.use_sky_var.set(True)
        self.gray_sky_var.set(False)
        self.sky_name_label.configure(text=path.name)
        self._set_thumb(self.sky_preview_label, path)
        self._persist_ui()

    def pick_shift_lock(self):
        path = self._pick_png("Scegli un PNG per lo shift lock")
        if not path:
            return
        self.shift_png = path
        self.use_shift_var.set(True)
        self.shift_name_label.configure(text=path.name)
        self._set_thumb(self.shift_preview_label, path)
        self._persist_ui()

    def _update_preview(self):
        if not self.selected_font or not self.selected_font.is_file():
            return
        self._load_private_font(self.selected_font)
        family = self.selected_family or rf.font_family_name(self.selected_font)
        try:
            self.preview.configure(font=ctk.CTkFont(family=family, size=20))
        except Exception:
            self.preview.configure(font=ctk.CTkFont(family="Segoe UI", size=20))

    def _load_private_font(self, path: Path):
        try:
            gdi32 = ctypes.windll.gdi32
            if self._loaded_font_path:
                gdi32.RemoveFontResourceExW(self._loaded_font_path, FR_PRIVATE, 0)
            if gdi32.AddFontResourceExW(str(path), FR_PRIVATE, 0):
                self._loaded_font_path = str(path)
        except Exception:
            pass

    def _collect(self) -> dict:
        fps = 240
        try:
            fps = int(self.fps_var.get().strip() or "240")
        except ValueError:
            fps = 240
        fps = max(30, min(fps, 1000))
        self.fps_var.set(str(fps))
        cfg = rf.load_config()
        cfg.update(
            {
                "use_custom_font": bool(self.use_font_var.get()),
                "use_custom_sky": bool(self.use_sky_var.get()),
                "use_shift_lock": bool(self.use_shift_var.get()),
                "use_stretch": False,
                "last_font": str(self.selected_font) if self.selected_font else cfg.get("last_font"),
                "last_font_name": self.selected_family or cfg.get("last_font_name"),
                "sky_png": str(self.sky_png) if self.sky_png else cfg.get("sky_png"),
                "shift_lock_png": str(self.shift_png) if self.shift_png else cfg.get("shift_lock_png"),
                "use_headless": False,
                "use_korblox": bool(self.use_korblox_var.get()),
                "test_mode": bool(self.test_mode_var.get()),
                "settings_tab": self._settings_tab,
                "fflags": {
                    "unlock_fps": bool(self.unlock_fps_var.get()),
                    "fps": fps,
                    "disable_postfx": bool(self.postfx_var.get()),
                    "disable_shadows": bool(self.shadows_var.get()),
                    "low_textures": bool(self.textures_var.get()),
                    "low_quality": bool(self.low_quality_var.get()),
                    "disable_particles": bool(self.particles_var.get()),
                    "no_msaa": bool(self.msaa_var.get()),
                    "low_lights": bool(self.lights_var.get()),
                    "no_clouds": bool(self.clouds_var.get()),
                    "alt_enter_fullscreen": bool(self.alt_enter_var.get()),
                    "disable_dpi_scale": bool(self.dpi_var.get()),
                    "prefer_d3d11": bool(self.d3d11_var.get()),
                    "prefer_vulkan": bool(self.vulkan_var.get()),
                    "gray_sky": bool(self.gray_sky_var.get()) and not bool(self.use_sky_var.get()),
                    "freeze_grass": bool(self.grass_var.get()),
                },
                "custom_fflags": dict(self.custom_flags),
            }
        )
        return cfg

    def _bind_persist(self):
        watched = (
            self.use_font_var,
            self.use_sky_var,
            self.use_shift_var,
            self.use_korblox_var,
            self.test_mode_var,
            self.unlock_fps_var,
            self.fps_var,
            self.postfx_var,
            self.shadows_var,
            self.textures_var,
            self.low_quality_var,
            self.particles_var,
            self.msaa_var,
            self.lights_var,
            self.clouds_var,
            self.alt_enter_var,
            self.dpi_var,
            self.d3d11_var,
            self.vulkan_var,
            self.gray_sky_var,
            self.grass_var,
        )
        for var in watched:
            var.trace_add("write", lambda *_: self._schedule_persist())
        self.use_sky_var.trace_add("write", self._sky_disables_gray)

    def _sky_disables_gray(self, *_):
        if self.use_sky_var.get() and self.gray_sky_var.get():
            self.gray_sky_var.set(False)

    def _schedule_persist(self):
        if not self._ready:
            return
        if self._persist_job is not None:
            try:
                self.after_cancel(self._persist_job)
            except Exception:
                pass
        self._persist_job = self.after(250, self._persist_ui)

    def _persist_ui(self):
        if not self._ready:
            return
        self._persist_job = None
        try:
            rf.save_config(self._collect())
        except Exception as exc:
            rf.log(f"persist: {exc}")

    def _on_close(self):
        self._persist_ui()
        self.destroy()

    def launch_from_home(self):
        self.save_settings(True, silent=True)

    def _set_busy_ui(self, busy: bool, status: str = ""):
        self._busy = busy
        state = "disabled" if busy else "normal"
        for btn in (getattr(self, "_btn_launch", None), getattr(self, "_btn_save", None)):
            if btn is not None:
                btn.configure(state=state)
        if getattr(self, "_footer_status", None) is not None:
            self._footer_status.configure(text=status)

    def save_settings(self, launch: bool, silent: bool = False):
        if self._busy:
            messagebox.showinfo("SolaX", "Sto ancora applicando le modifiche, aspetta un attimo.")
            return
        old_custom_keys = list((rf.load_config().get("custom_fflags") or {}).keys())
        cfg = self._collect()
        notes: list[str] = []
        if cfg.get("use_custom_font") and not (self.selected_font and self.selected_font.is_file()):
            cfg["use_custom_font"] = False
            self.use_font_var.set(False)
            notes.append("Font non trovato: opzione disattivata.")
        if cfg.get("use_custom_sky") and not (self.sky_png and self.sky_png.is_file()):
            cfg["use_custom_sky"] = False
            self.use_sky_var.set(False)
            notes.append("PNG cielo non trovato: opzione disattivata.")
        if cfg.get("use_shift_lock") and not (self.shift_png and self.shift_png.is_file()):
            cfg["use_shift_lock"] = False
            self.use_shift_var.set(False)
            notes.append("PNG shift lock non trovato: opzione disattivata.")
        if rf.find_roblox() is None:
            messagebox.showerror(
                "Roblox non trovato",
                "Installa Roblox, avvialo una volta, poi riprova.",
            )
            return
        if rf.roblox_running():
            if self._auto_mode:
                rf.close_roblox()
            elif not messagebox.askyesno(
                "Roblox è aperto",
                "Per applicare le modifiche Roblox va chiuso e riaperto.\n\nVuoi chiuderlo ora?",
            ):
                return
            else:
                rf.close_roblox()

        self._set_busy_ui(True, "Avvio Roblox..." if launch else "Salvataggio...")
        rf.save_config(cfg)
        font_path = self.selected_font
        use_font = bool(cfg.get("use_custom_font"))
        use_sky = bool(cfg.get("use_custom_sky"))
        use_shift = bool(cfg.get("use_shift_lock"))
        use_korblox = bool(cfg.get("use_korblox"))
        sky_png = self.sky_png
        shift_png = self.shift_png
        fflags = cfg.get("fflags") or {}
        custom_flags = cfg.get("custom_fflags") or {}

        def work():
            warnings = list(notes)
            launched = False
            fatal: Exception | None = None
            try:
                install = rf.find_roblox()
                if install is None:
                    raise FileNotFoundError("Roblox non trovato.")

                def step(label: str, fn):
                    try:
                        fn()
                    except Exception as exc:
                        rf.log(f"{label}: {exc}")
                        warnings.append(f"{label}: {exc}")

                if use_font and font_path:
                    step("Font", lambda: rf.apply_font(font_path, install))
                else:
                    def restore_font():
                        try:
                            rf.restore_fonts(install)
                        except FileNotFoundError:
                            pass

                    step("Font", restore_font)
                if use_sky and sky_png:
                    self.after(0, lambda: self.gray_sky_var.set(False))
                    fflags["gray_sky"] = False
                    step("Cielo", lambda: rm.apply_sky(sky_png, install))
                else:
                    step("Cielo", lambda: rm.restore_sky(install))
                if use_shift and shift_png:
                    step("Shift lock", lambda: rm.apply_shift_lock(shift_png, install))
                else:
                    step("Shift lock", lambda: rm.restore_shift_lock(install))
                step("Heads", lambda: rh.restore_headless(install))
                if use_korblox:
                    step("Korblox", lambda: rk.apply_korblox(install))
                else:
                    step("Korblox", lambda: rk.restore_korblox(install))
                rst.stop_stretch_watcher()
                step(
                    "FastFlag",
                    lambda: rff.apply_fflags(
                        fflags,
                        install,
                        custom=custom_flags,
                        previous_custom_keys=old_custom_keys,
                        disable_gray_sky=bool(use_sky),
                    ),
                )
                if launch:
                    rf.launch_roblox(install)
                    launched = True
            except Exception as exc:
                fatal = exc
                rf.log(f"save/launch: {exc}")
            warn_text = "\n".join(warnings) if warnings else None
            self.after(
                0,
                lambda f=fatal, w=warn_text, did=launched: self._done_save(
                    f is None, launch, silent, f, w, did
                ),
            )

        threading.Thread(target=work, daemon=True).start()

    def _done_save(
        self,
        ok: bool,
        launch: bool,
        silent: bool,
        error: Exception | None,
        warnings: str | None = None,
        launched: bool = False,
    ):
        self._set_busy_ui(False, "")
        if error is not None and not launched:
            messagebox.showerror("Errore", str(error))
            if self._auto_mode:
                self.after(4000, self.destroy)
            return
        if self._auto_mode:
            self.after(25000, self._auto_quit_if_idle)
            return
        parts: list[str] = []
        if launch or launched:
            parts.append("Impostazioni salvate. Roblox è in avvio.")
        elif not silent:
            parts.append("Impostazioni salvate.")
        if warnings:
            parts.append(warnings)
        if not parts:
            return
        text = "\n\n".join(parts)
        if warnings:
            messagebox.showwarning("SolaX", text)
        elif not silent:
            messagebox.showinfo("SolaX", text)

    def destroy(self):
        self._ready = False
        try:
            rf.save_config(self._collect())
        except Exception:
            pass
        try:
            if self._loaded_font_path:
                ctypes.windll.gdi32.RemoveFontResourceExW(self._loaded_font_path, FR_PRIVATE, 0)
        except Exception:
            pass
        super().destroy()


if __name__ == "__main__":
    def is_auto_launch() -> bool:
        if "--auto" in sys.argv:
            return True
        stem = Path(sys.argv[0]).stem.lower().replace("-", " ").replace("_", " ")
        return stem in {"solax auto", "solax automatico"}

    App(auto=is_auto_launch()).mainloop()
