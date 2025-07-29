# app/api/settings.py
"""
Hyatlas Launcher – user settings API
====================================

Persists simple launcher settings (language, update channel, window
preferences) in `~/.hyatlas/config/settings.json` using the helpers
defined in *app/core/config.py*.

Routes
------
GET  /api/settings
    -> returns current settings (merged with defaults).

POST /api/settings
    -> body: SettingsUpdate
    -> merges with existing data, saves to disk, returns updated object.
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core import config

router = APIRouter(tags=["settings"])


# ──────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────
class WindowPref(BaseModel):
    width: int = Field(1280, ge=800, le=3840)
    height: int = Field(720, ge=600, le=2160)
    fullscreen: bool = False


class Settings(BaseModel):
    language: str = "en-US"
    channel: str = config.DEFAULT_CHANNEL
    window: WindowPref = WindowPref()


class SettingsUpdate(BaseModel):
    language: Optional[str] = None
    channel: Optional[str] = None
    window: Optional[WindowPref] = None


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────
def _merge(existing: Dict, update: SettingsUpdate) -> Dict:
    data = existing.copy()
    up = update.dict(exclude_unset=True)

    for key, val in up.items():
        if isinstance(val, dict) and isinstance(data.get(key), dict):
            data[key].update(val)
        else:
            data[key] = val
    return data


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
@router.get("/settings", response_model=Settings)
async def get_settings():
    """
    Return the currently effective settings (defaults overwritten by user file).
    """
    return Settings(**config.read_config())


@router.post("/settings", response_model=Settings)
async def save_settings(body: SettingsUpdate):
    """
    Validate & persist changes.  Returns the merged settings object.
    """
    merged = _merge(config.read_config(), body)
    try:
        config.save_config(merged)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {exc}",
        ) from exc
    return Settings(**merged)
