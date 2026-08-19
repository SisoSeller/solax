"""Scrive FastFlag locali in ClientSettings di Roblox (solo grafica/prestazioni)."""

from __future__ import annotations

import json
from pathlib import Path

import roblox_fonts as rf

MANAGED_KEYS = {
    "DFIntTaskSchedulerTargetFps",
    "FFlagDisablePostFx",
    "DFFlagDebugPauseVoxelizer",
    "DFFlagTextureQualityOverrideEnabled",
    "DFIntTextureQualityOverride",
    "FFlagHandleAltEnterFullscreenManually",
    "FIntFRMMaxGrassDistance",
    "FIntFRMMinGrassDistance",
    "DFIntDebugFRMQualityLevelOverride",
    "DFFlagDisableDPIScale",
    "FFlagDebugGraphicsPreferD3D11",
    "FFlagDebugGraphicsPreferVulkan",
    "FFlagDebugSkyGray",
    "FIntGrassMovementReducedMotionFactor",
    "FIntRenderShadowIntensity",
    "FIntDebugForceMSAASamples",
    "FFlagDebugDisableParticleRendering",
    "FIntRenderLocalLightUpdatesMax",
    "FIntRenderLocalLightUpdatesMin",
    "FIntRenderCloudsCountLimit",
    "FFlagCloudsUseNewSystem",
}

DEFAULT_FFLAGS = {
    "unlock_fps": False,
    "fps": 240,
    "disable_postfx": False,
    "disable_shadows": False,
    "low_textures": False,
    "low_quality": False,
    "disable_particles": False,
    "no_msaa": False,
    "low_lights": False,
    "no_clouds": False,
    "alt_enter_fullscreen": False,
    "disable_dpi_scale": False,
    "prefer_d3d11": False,
    "prefer_vulkan": False,
    "gray_sky": False,
    "freeze_grass": False,
}


def client_settings_file(install: rf.RobloxInstall) -> Path:
    return install.version_dir / "ClientSettings" / "ClientAppSettings.json"


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def flags_from_settings(fflags: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        fps = int(str(fflags.get("fps") or 240).strip())
    except (TypeError, ValueError):
        fps = 240
    fps = max(30, min(fps, 1000))
    if fflags.get("unlock_fps"):
        out["DFIntTaskSchedulerTargetFps"] = str(fps)
    if fflags.get("disable_postfx"):
        out["FFlagDisablePostFx"] = "true"
    if fflags.get("disable_postfx") or fflags.get("low_quality"):
        out["DFIntDebugFRMQualityLevelOverride"] = "1"
    if fflags.get("disable_shadows"):
        out["DFFlagDebugPauseVoxelizer"] = "true"
        out["FIntRenderShadowIntensity"] = "0"
        out["FIntFRMMaxGrassDistance"] = "0"
        out["FIntFRMMinGrassDistance"] = "0"
    if fflags.get("low_textures"):
        out["DFFlagTextureQualityOverrideEnabled"] = "true"
        out["DFIntTextureQualityOverride"] = "0"
    if fflags.get("disable_particles"):
        out["FFlagDebugDisableParticleRendering"] = "true"
    if fflags.get("no_msaa"):
        out["FIntDebugForceMSAASamples"] = "1"
    if fflags.get("low_lights"):
        out["FIntRenderLocalLightUpdatesMax"] = "0"
        out["FIntRenderLocalLightUpdatesMin"] = "0"
    if fflags.get("no_clouds"):
        out["FIntRenderCloudsCountLimit"] = "0"
        out["FFlagCloudsUseNewSystem"] = "false"
    if fflags.get("alt_enter_fullscreen"):
        out["FFlagHandleAltEnterFullscreenManually"] = "true"
    if fflags.get("disable_dpi_scale"):
        out["DFFlagDisableDPIScale"] = "true"
    if fflags.get("prefer_d3d11"):
        out["FFlagDebugGraphicsPreferD3D11"] = "true"
    if fflags.get("prefer_vulkan"):
        out["FFlagDebugGraphicsPreferVulkan"] = "true"
    if fflags.get("gray_sky"):
        out["FFlagDebugSkyGray"] = "true"
    if fflags.get("freeze_grass"):
        out["FIntGrassMovementReducedMotionFactor"] = "0"
    return out


def apply_fflags(
    fflags: dict,
    install: rf.RobloxInstall | None = None,
    custom: dict | None = None,
    previous_custom_keys: list[str] | None = None,
    disable_gray_sky: bool = False,
) -> rf.RobloxInstall:
    install = install or rf.find_roblox()
    if install is None:
        raise FileNotFoundError("Roblox non trovato.")

    flags = dict(fflags)
    if disable_gray_sky:
        flags["gray_sky"] = False

    path = client_settings_file(install)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = _load_json(path)
    for key in MANAGED_KEYS:
        current.pop(key, None)
    for key in previous_custom_keys or []:
        current.pop(key, None)
    current.update(flags_from_settings(flags))
    for name, value in (custom or {}).items():
        key = str(name).strip()
        if not key:
            continue
        if disable_gray_sky and key == "FFlagDebugSkyGray":
            continue
        current[key] = str(value)
    if disable_gray_sky:
        current.pop("FFlagDebugSkyGray", None)
    rf.make_writable(path)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return install


def clear_managed_fflags(install: rf.RobloxInstall | None = None) -> None:
    install = install or rf.find_roblox()
    if install is None:
        return
    path = client_settings_file(install)
    current = _load_json(path)
    if not current:
        return
    for key in MANAGED_KEYS:
        current.pop(key, None)
    rf.make_writable(path)
    if current:
        path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    elif path.exists():
        path.unlink(missing_ok=True)
