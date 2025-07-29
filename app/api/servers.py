# app/api/servers.py
from __future__ import annotations

import asyncio
import os
import random
import uuid
from typing import List, Optional

import aiohttp
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator

from app.core import models

# ─────────────────────────────── DEV-Mock-Liste ────────────────────────────────
def _make_mock(index: int) -> dict:
    return {
        "id":          str(uuid.uuid4()),
        "name":        f"MockWorld #{index}",
        "description": "A lively voxel realm full of adventure and quests.",
        "address":     "127.0.0.1",
        "port":        25565 + index,
        "build_id":    "2025-07-dev",
        "online_players": random.randint(0, 38),
        "max_players": 40,
        "ping":        random.randint(20, 120),
        "thumbnail":   "/static/img/tile_placeholder.png",
    }

MOCK_SERVERS: List[dict] = [_make_mock(i) for i in range(1, 31)]
MM_DISABLED: bool = os.getenv("HYATLAS_MM_DISABLED", "1") != "0"

# ────────────────────────────────────────────────────────────────────────────────
router = APIRouter(tags=["servers"])
MM_URL  = os.getenv("HYATLAS_MM_URL", "https://mm.hyatlas.io").rstrip("/")

# ─────────────────────────────── GET /api/servers ──────────────────────────────
@router.get("/servers", response_model=List[models.ServerInfo])
async def list_servers(channel: Optional[str] = None):
    """DEV → Mock‐Daten | PROD → externes Matchmaking‐Backend"""
    if MM_DISABLED:
        # jede Dict in ein ServerInfo-Objekt casten → Validation OK
        return [models.ServerInfo(**srv) for srv in MOCK_SERVERS]

    url    = f"{MM_URL}/v1/servers"
    params = {"channel": channel} if channel else None

    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except aiohttp.ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Matchmaking service unreachable: {exc}",
        ) from exc

    try:
        return [models.ServerInfo(**item) for item in data]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Malformed server data from matchmaking",
        ) from exc

# ─────────────────────────────── POST /api/servers/ping ─────────────────────────
class PingRequest(BaseModel):
    address: str = Field(description="Hostname or IPv4/IPv6")
    port:    int = Field(gt=0, lt=65536)

    @validator("address")
    def _strip(cls, v: str) -> str:        # pylint: disable=no-self-argument
        return v.strip()

class PingResponse(BaseModel):
    latencyMs: Optional[int] = None
    online:    bool
    buildId:   Optional[str] = None

async def _tcp_ping(host: str, port: int) -> Optional[int]:
    loop, start = asyncio.get_running_loop(), asyncio.get_running_loop().time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=1.0
        )
        writer.close(); await writer.wait_closed()
        return int((loop.time() - start) * 1000)
    except Exception:
        return None

@router.post("/servers/ping", response_model=PingResponse)
async def ping_server(payload: PingRequest):
    latency = await _tcp_ping(payload.address, payload.port)
    if latency is None:
        return PingResponse(latencyMs=None, online=False)

    build_id: Optional[str] = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(payload.address, payload.port), timeout=0.5
        )
        banner = await asyncio.wait_for(reader.readexactly(16), timeout=0.5)
        if banner.startswith(b"HYATLAS\x00"):
            build_id = banner.split(b"\x00", 1)[1].decode(errors="ignore").strip()
        writer.close(); await writer.wait_closed()
    except Exception:
        pass

    return PingResponse(latencyMs=latency, online=True, buildId=build_id)
