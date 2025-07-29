# app/core/models.py
"""
Hyatlas Launcher – shared data models
=====================================

All modules (API routers, updater, mod-handler, UI layer) should
communicate through **typed** value objects defined here.  Using
Pydantic gives us validation, (de)serialisation, and autocompletion
for free.

Feel free to extend individual models, but avoid adding business
logic – that belongs in `core/` sub-modules.
"""

from __future__ import annotations

import enum
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


# ──────────────────────────────────────────────
# 1. JWT / Auth
# ──────────────────────────────────────────────
class UserToken(BaseModel):
    """Parsed JWT payload returned by the authentication service."""
    sub: str                      # user id
    username: str
    exp: int                      # unix epoch
    roles: List[str] = Field(default_factory=list)

    @property
    def expires_at(self) -> datetime:
        return datetime.fromtimestamp(self.exp)

    def is_admin(self) -> bool:
        return "admin" in self.roles


# ──────────────────────────────────────────────
# 2. Server list / matchmaking
# ──────────────────────────────────────────────
class ModRequirement(BaseModel):
    id: str
    version: str
    sha256: str
    paid: bool = False


class ServerInfo(BaseModel):
    id: str
    name: str
    address: str                 # hostname or IP
    port: int
    online_players: int
    max_players: int
    build_id: str
    requires_official_client: bool = True
    mods: List[ModRequirement] = Field(default_factory=list)

    @validator("port")
    def port_range(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


# ──────────────────────────────────────────────
# 3. Manifest & update system
# ──────────────────────────────────────────────
class ManifestFile(BaseModel):
    path: str
    sha256: str
    size: int
    url: Optional[HttpUrl] = None      # may be repo-relative

    class Config:
        frozen = True                  # hashable


class Manifest(BaseModel):
    build_id: str
    unity_version: str
    channel: str                       # stable / nightly / …
    files: List[ManifestFile]
    signature: str                     # RSA-PSS base64

    def file_by_path(self, rel_path: str) -> Optional[ManifestFile]:
        return next((f for f in self.files if f.path == rel_path), None)


# ──────────────────────────────────────────────
# 4. Mods & resource packs
# ──────────────────────────────────────────────
class PackageType(str, enum.Enum):
    mod = "mod"
    resource = "resource"


class ModDescriptor(BaseModel):
    id: str
    version: str
    sha256: str
    type: PackageType = PackageType.mod
    paid: bool = False
    url: Optional[HttpUrl] = None
    signature: Optional[str] = None    # RSA signature (optional for free mods)


class RegistryStatus(str, enum.Enum):
    verified = "verified"
    quarantine = "quarantine"
    blocked = "blocked"
    unknown = "unknown"


class RegistryEntry(BaseModel):
    """Entry stored in ~/.hyatlas/mods/registry.json"""
    id: str
    version: str
    sha256: str
    type: PackageType
    path: Path
    status: RegistryStatus = RegistryStatus.unknown
    scanned_at: Optional[datetime] = None
    malware: Optional[str] = None      # engine id if AV flagged

    @property
    def is_usable(self) -> bool:
        return self.status == RegistryStatus.verified


# ──────────────────────────────────────────────
# 5. Pydantic global config
# ──────────────────────────────────────────────
class Config:
    """Global model config: enable orm-mode, allow mutation, etc."""
    orm_mode = True
