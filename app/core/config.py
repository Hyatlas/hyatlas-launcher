# app/core/config.py
"""
Hyatlas Launcher – central configuration helper
===============================================

All modules import *only* from this file when they need:
• application constants (name, default channel, current launcher version)
• resolved user-specific paths (builds/, mods/, cache/, logs/…)
• persisted user settings (language, window size, last server, …)

Keeping everything here means we can later change directory layout,
add portable-mode switches, or expose new settings without touching
dozens of call-sites.

This file does *not* perform any network or heavy I/O.  Directory
creation happens lazily (at import time) and should complete in
milliseconds.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict

# ──────────────────────────────────────────────
# 1. Application constants
# ──────────────────────────────────────────────
APP_NAME: str = "Hyatlas Launcher"
APP_ID: str = "hyatlas-launcher"
LAUNCHER_VERSION: str = "0.1.0"
DEFAULT_CHANNEL: str = "stable"          # ← could be "nightly" during alpha

# file & directory names
CONFIG_FILE_NAME = "settings.json"
REGISTRY_FILE_NAME = "registry.json"     # mod/resource registry


# ──────────────────────────────────────────────
# 2. Directory resolution helpers
# ──────────────────────────────────────────────
def _home_base() -> Path:
    """Return the root folder for all user data (`~/.hyatlas/` on Unix,
    `%LOCALAPPDATA%\\Hyatlas\\` on Windows). Can be overridden with
    the env variable `HYATLAS_HOME`."""
    if env := os.getenv("HYATLAS_HOME"):
        return Path(env).expanduser().resolve()

    if platform.system() == "Windows":
        root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return (root / "Hyatlas").resolve()

    # Linux, macOS, everything else
    return (Path.home() / ".hyatlas").resolve()


BASE_DIR: Path = _home_base()
BUILDS_DIR: Path = BASE_DIR / "builds"
MODS_DIR: Path = BASE_DIR / "mods"
RESOURCE_DIR: Path = BASE_DIR / "resources"
CACHE_DIR: Path = BASE_DIR / "cache"
QUARANTINE_DIR: Path = BASE_DIR / "quarantine"
LOG_DIR: Path = BASE_DIR / "logs"
CONFIG_DIR: Path = BASE_DIR / "config"

# Map for easy iteration / testing
_ALL_DIRS = (
    BUILDS_DIR,
    MODS_DIR,
    RESOURCE_DIR,
    CACHE_DIR,
    QUARANTINE_DIR,
    LOG_DIR,
    CONFIG_DIR,
)


# ──────────────────────────────────────────────
# 3. Bootstrap – ensure folders exist
# ──────────────────────────────────────────────
def ensure_dirs() -> None:
    """Create any missing directories (no error if they exist)."""
    for d in _ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


ensure_dirs()  # create on first import


# ──────────────────────────────────────────────
# 4. User settings (read / write)
# ──────────────────────────────────────────────
_CONFIG_PATH: Path = CONFIG_DIR / CONFIG_FILE_NAME
_DEFAULT_SETTINGS: Dict[str, Any] = {
    "language": "en-US",
    "channel": DEFAULT_CHANNEL,
    "window": {"width": 1280, "height": 720, "fullscreen": False},
    "lastServer": None,
}


def _load_raw() -> Dict[str, Any]:
    if _CONFIG_PATH.exists():
        try:
            with _CONFIG_PATH.open(encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            # Backup the corrupted file before resetting
            backup = _CONFIG_PATH.with_suffix(".bak")
            shutil.copy2(_CONFIG_PATH, backup)
    return {}


def read_config() -> Dict[str, Any]:
    """Return merged settings (defaults overridden by user values)."""
    cfg = _DEFAULT_SETTINGS.copy()
    cfg.update(_load_raw())
    return cfg


def save_config(new_cfg: Dict[str, Any]) -> None:
    """Persist updated user settings atomically."""
    tmp = _CONFIG_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(new_cfg, fh, indent=2)
    tmp.replace(_CONFIG_PATH)


# ──────────────────────────────────────────────
# 5. Helper utilities (public API)
# ──────────────────────────────────────────────
def build_path(build_id: str) -> Path:
    """Return the directory for a specific client build."""
    return BUILDS_DIR / build_id


def mod_path(mod_id: str, version: str) -> Path:
    """Return the folder where a verified mod should live."""
    return MODS_DIR / f"{mod_id}-{version}"


def is_portable_mode() -> bool:
    """Launcher runs 'portable' if HYATLAS_HOME env var points inside the
    launcher folder itself."""
    return BASE_DIR.is_relative_to(Path.cwd())


# ──────────────────────────────────────────────
# Unit-test helpers
# ──────────────────────────────────────────────
def _reset_for_tests(tmp_path: Path) -> None:  # pragma: no cover
    """Internal helper: redirect BASE_DIR during pytest."""
    global BASE_DIR, BUILDS_DIR, MODS_DIR, RESOURCE_DIR, CACHE_DIR
    global QUARANTINE_DIR, LOG_DIR, CONFIG_DIR, _CONFIG_PATH
    BASE_DIR = tmp_path
    BUILDS_DIR = BASE_DIR / "builds"
    MODS_DIR = BASE_DIR / "mods"
    RESOURCE_DIR = BASE_DIR / "resources"
    CACHE_DIR = BASE_DIR / "cache"
    QUARANTINE_DIR = BASE_DIR / "quarantine"
    LOG_DIR = BASE_DIR / "logs"
    CONFIG_DIR = BASE_DIR / "config"
    _CONFIG_PATH = CONFIG_DIR / CONFIG_FILE_NAME
    ensure_dirs()
