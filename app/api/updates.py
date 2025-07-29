# app/api/updates.py
"""
Hyatlas Launcher – update API
=============================

Two endpoints for the frontend:

1) GET  /api/update/check?channel=stable
      -> returns whether a newer build exists, plus metadata.

2) POST /api/update/apply
      -> launches the download/patch process (core.updater)
         and responds immediately (202 Accepted).
         Frontend can poll `/check` again to see if the local build
         has been updated.

The heavy lifting is delegated to `app.core.updater`, which exposes:

• get_local_build(channel) -> str
• get_remote_manifest(channel) -> Manifest | None
• apply_update(manifest) -> None  (downloads & installs)
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel

from app.core import config, updater
from app.core.models import Manifest

router = APIRouter(tags=["updates"])


# ──────────────────────────────────────────────
# Response / request models
# ──────────────────────────────────────────────
class UpdateCheckResponse(BaseModel):
    currentBuildId: str
    latestBuildId: Optional[str] = None
    updateAvailable: bool
    downloadSize: Optional[int] = None  # bytes


class UpdateApplyRequest(BaseModel):
    channel: Optional[str] = None  # override default channel if desired


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────
async def _fetch_manifest_or_404(channel: str) -> Manifest:
    manifest = await updater.get_remote_manifest(channel)
    if manifest is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Update service unavailable",
        )
    return manifest


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
@router.get("/update/check", response_model=UpdateCheckResponse)
async def check_update(channel: str = Query(config.DEFAULT_CHANNEL)):
    """
    Compare local build vs. remote manifest.
    """
    local_build = updater.get_local_build(channel)
    manifest = await _fetch_manifest_or_404(channel)

    update_available = manifest.build_id != local_build
    dl_size = sum(f.size for f in manifest.files) if update_available else None

    return UpdateCheckResponse(
        currentBuildId=local_build,
        latestBuildId=manifest.build_id if update_available else None,
        updateAvailable=update_available,
        downloadSize=dl_size,
    )


@router.post("/update/apply", status_code=status.HTTP_202_ACCEPTED)
async def apply_update(
    body: UpdateApplyRequest,
    background: BackgroundTasks,
):
    """
    Kick off download/patch process in a background task.
    """
    channel = body.channel or config.DEFAULT_CHANNEL
    manifest = await _fetch_manifest_or_404(channel)

    local_build = updater.get_local_build(channel)
    if manifest.build_id == local_build:
        return {"detail": "Already up to date"}

    # Run updater in background so HTTP request returns immediately
    background.add_task(updater.apply_update, manifest)
    return {"detail": f"Updating to {manifest.build_id}"}
