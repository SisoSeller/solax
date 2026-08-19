# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['PIL._tkinter_finder', 'roblox_fonts', 'roblox_flags', 'roblox_mods', 'roblox_stretch', 'roblox_headless', 'roblox_korblox', 'roblox_plugins', 'windnd']
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
datas += [('assets/rightleg.mesh', 'assets')]
datas += [('assets/plugins', 'assets/plugins')]
datas += [('website/index.html', 'website')]
datas += [('website/icon.png', 'website')]
datas += [('website/icon.ico', 'website')]
datas += [('website/favicon.png', 'website')]


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SolaX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='website/icon.ico',
)

exe_auto = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SolaX Auto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='website/icon.ico',
)

coll = COLLECT(
    exe,
    exe_auto,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SolaX',
)
