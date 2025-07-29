# app/core/updater.py
"""
Hyatlas Launcher – build & patch manager
=======================================

Very first iteration: **full-package updates only**
(delta / binary diff support can be bolted on later).

Public functions
----------------
get_local_build(channel)        -> str
get_remote_manifest(channel)    -> Manifest | None
apply_update(manifest)          -> None   (downloads & installs)

Filesystem layout
-----------------
~/.hyatlas/builds/
    ├─ 2025-07-beta12/
    │   ├─ Game.exe
    │   └─ ...
    ├─ 2025-08-alpha01/
    └─ channel-current.txt      ← stores *just* the build_id in one line
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional

import aiohttp

from app.core import config, models

_MANIFEST_URL = "https://updates.hyatlas.io/{channel}/manifest.json"
_MARKER_NAME = "channel-current.txt"   # lives in builds/

# ──────────────────────────────────────────────
# 1. Local build helpers
# ──────────────────────────────────────────────
def _marker_path(channel: str) -> Path:
    return config.BUILDS_DIR / f"{channel}-{_MARKER_NAME}"


def get_local_build(channel: str) -> str:
    """
    Return the buildId currently active for a channel, or 'unknown'.
    """
    marker = _marker_path(channel)
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    return "unknown"


def _write_marker(channel: str, build_id: str) -> None:
    _marker_path(channel).write_text(build_id, encoding="utf-8")


# ──────────────────────────────────────────────
# 2. Remote manifest
# ──────────────────────────────────────────────
async def get_remote_manifest(channel: str) -> Optional[models.Manifest]:
    url = _MANIFEST_URL.format(channel=channel)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                raw = await resp.json()
    except aiohttp.ClientError as exc:
        sys.stderr.write(f"[updater] manifest download failed: {exc}\n")
        return None

    try:
        return models.Manifest(**raw)
    except Exception as exc:
        sys.stderr.write(f"[updater] malformed manifest: {exc}\n")
        return None


# ──────────────────────────────────────────────
# 3. Apply update
# ──────────────────────────────────────────────
async def _download_file(
    session: aiohttp.ClientSession,
    url: str,
    dest: Path,
    expected_sha256: str,
) -> None:
    """
    Stream download to dest, verify sha256, raise RuntimeError if mismatch.
    """
    hasher = hashlib.sha256()
    tmp = dest.with_suffix(".tmp")

    async with session.get(url) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            async for chunk in resp.content.iter_chunked(65536):
                fh.write(chunk)
                hasher.update(chunk)

    if hasher.hexdigest() != expected_sha256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"SHA256 mismatch for {dest.name}")

    tmp.replace(dest)


async def apply_update(manifest: models.Manifest) -> None:
    """
    Download *all* files described by the manifest into a new build folder.
    On success, write channel-current marker.
    """
    channel = manifest.channel
    build_dir = config.build_path(manifest.build_id)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        # parallel downloads (max 4 at once)
        semaphore = asyncio.Semaphore(4)
        tasks = []

        for f in manifest.files:
            dest_path = build_dir / f.path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            async def _task(file=f):
                async with semaphore:
                    await _download_file(session, file.url or f.path, dest_path, file.sha256)

            tasks.append(asyncio.create_task(_task()))

        # wait and propagate first exception
        await asyncio.gather(*tasks)

    # Persist manifest locally (for delta diff checks later)
    (build_dir / "manifest.json").write_text(
        json.dumps(manifest.dict(), indent=2), encoding="utf-8"
    )

    # Update channel marker
    _write_marker(channel, manifest.build_id)
    sys.stdout.write(f"[updater] updated to {manifest.build_id} ({channel})\n")
