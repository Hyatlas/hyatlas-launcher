# app/core/mods/cache.py
"""
Hyatlas Launcher – mod & resource package cache
===============================================

High-level flow (called from `core.mods.loader` or the updater):

1. Launcher receives *ModRequirement* list from the server handshake.
2. `sync_with_server()` checks which packages are already verified.
3. Missing or outdated packages are downloaded into `~/.hyatlas/cache/`.
4. Each ZIP is passed to `verifier.verify_package()` (RSA + AV scan).
5. On success the file is extracted/placed in `~/.hyatlas/mods/<id>-<ver>/`
   and the local registry is updated.
6. Any package that fails verification is moved to the quarantine folder
   and the player gets an error dialog.

Only *verified* packages are returned to the caller, who then supplies
their paths to the game executable via launch arguments.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Sequence

import aiohttp

from app.core import config
from app.core.models import (
    ModDescriptor,
    ModRequirement,
    PackageType,
    RegistryEntry,
    RegistryStatus,
)

# Lazy import (avoids circular dependency if verifier imports cache)
from . import verifier  # noqa: E402, pylint: disable=wrong-import-position


REGISTRY_PATH: Path = config.MODS_DIR / config.REGISTRY_FILE_NAME


# ──────────────────────────────────────────────
# Registry helpers
# ──────────────────────────────────────────────
def _load_registry() -> Dict[str, RegistryEntry]:
    if not REGISTRY_PATH.exists():
        return {}

    try:
        with REGISTRY_PATH.open(encoding="utf-8") as fh:
            raw = json.load(fh)
            return {
                key: RegistryEntry(**val)  # type: ignore[arg-type]
                for key, val in raw.items()
            }
    except (json.JSONDecodeError, OSError):
        backup = REGISTRY_PATH.with_suffix(".corrupt.json")
        shutil.copy2(REGISTRY_PATH, backup)
        return {}


def _save_registry(entries: Dict[str, RegistryEntry]) -> None:
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump({k: v.dict() for k, v in entries.items()}, fh, indent=2)
    tmp.replace(REGISTRY_PATH)


def _key(mod_id: str, version: str) -> str:
    return f"{mod_id}:{version}"


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
async def sync_with_server(
    requirements: Sequence[ModRequirement],
) -> List[Path]:
    """
    Ensure all required packages are present & verified.
    Returns list of *folder paths* to load into the game.
    """
    registry = _load_registry()
    verified_paths: List[Path] = []
    to_fetch: List[ModDescriptor] = []

    # 1) Decide what to download
    for req in requirements:
        key = _key(req.id, req.version)
        entry = registry.get(key)

        if entry and entry.status == RegistryStatus.verified:
            if entry.sha256 == req.sha256 and entry.path.exists():
                verified_paths.append(entry.path)
                continue  # already good

        # Queue for download
        to_fetch.append(
            ModDescriptor(
                id=req.id,
                version=req.version,
                sha256=req.sha256,
                type=PackageType.mod,
                paid=req.paid,
                url=None,           # server will provide absolute URL in handshake
            )
        )

    # 2) Download & verify missing packages
    if to_fetch:
        async with aiohttp.ClientSession() as session:
            for descriptor in to_fetch:
                archive = await _download_package(session, descriptor)
                entry = await _install_package(archive, descriptor)
                registry[_key(entry.id, entry.version)] = entry
                if entry.status == RegistryStatus.verified:
                    verified_paths.append(entry.path)

    # 3) Persist registry
    _save_registry(registry)
    return verified_paths


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────
async def _download_package(
    session: aiohttp.ClientSession,
    descriptor: ModDescriptor,
) -> Path:
    """Save ZIP to cache/ and return the path."""
    if descriptor.url is None:
        raise RuntimeError(f"No download URL for mod '{descriptor.id}'")

    filename = f"{descriptor.id}-{descriptor.version}.zip"
    dest = config.CACHE_DIR / filename

    async with session.get(descriptor.url) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            async for chunk in resp.content.iter_chunked(8192):
                fh.write(chunk)
    return dest


async def _install_package(archive: Path, descriptor: ModDescriptor) -> RegistryEntry:
    """
    Verify SHA256, RSA signature & AV scan, then move/extract to mods/.
    Returns the resulting registry entry.
    """
    sha256 = _calc_sha256(archive)
    key = _key(descriptor.id, descriptor.version)

    if sha256 != descriptor.sha256:
        return _quarantine(
            key, archive, sha256, reason="sha256 mismatch (tampered?)"
        )

    # RSA + AV scan
    if not verifier.verify_package(archive, descriptor):
        return _quarantine(key, archive, sha256, reason="signature or AV failed")

    # Extraction/move
    target_dir = config.mod_path(descriptor.id, descriptor.version)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # We simply move the archive for now; later we can extract if desired
    dest_archive = target_dir / archive.name
    shutil.move(archive, dest_archive)

    return RegistryEntry(
        id=descriptor.id,
        version=descriptor.version,
        sha256=sha256,
        type=descriptor.type,
        path=target_dir,
        status=RegistryStatus.verified,
        scanned_at=verifier.last_scan_time(),
    )


def _quarantine(key: str, archive: Path, sha256: str, reason: str) -> RegistryEntry:
    """Move a suspicious package to ~/.hyatlas/quarantine/ and record it."""
    q_path = config.QUARANTINE_DIR / archive.name
    shutil.move(archive, q_path)

    sys.stderr.write(f"[cache] Package {archive.name} quarantined: {reason}\n")

    return RegistryEntry(
        id=key.split(":")[0],
        version=key.split(":")[1],
        sha256=sha256,
        type=PackageType.mod,
        path=q_path,
        status=RegistryStatus.quarantine,
        malware=reason,
    )


def _calc_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
