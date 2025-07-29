# app/core/launcher.py
"""
Hyatlas Launcher – game process bootstrapper
===========================================

This module is *purely* responsible for locating the correct Hyatlas
client executable, building the command-line arguments (server address,
mods, JWT, fullscreen flag, etc.) and spawning the subprocess.

Public helpers
--------------
• locate_executable(build_id) -> Path
• build_launch_cmd(build_id, server, token, mods, fullscreen) -> List[str]
• start_game(token, server, mods, fullscreen) -> subprocess.Popen

Other modules (login flow, UI) call **start_game** – they don’t need to
know any filesystem details.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

from app.core import config
from app.core.models import ServerInfo


# ──────────────────────────────────────────────
# 1. Locate executable
# ──────────────────────────────────────────────
def locate_executable(build_id: str) -> Path:
    """
    Return platform-specific client executable.

    Raises FileNotFoundError if the binary is missing.
    """
    build_dir = config.build_path(build_id)
    if not build_dir.exists():
        raise FileNotFoundError(f"Build '{build_id}' not installed")

    system = platform.system()
    exe_name = "Hyatlas.exe" if system == "Windows" else "Hyatlas.x86_64"
    exe_path = build_dir / exe_name

    if not exe_path.exists():
        # Fallback: first file with executable flag
        for cand in build_dir.iterdir():
            if cand.is_file() and os.access(cand, os.X_OK):
                exe_path = cand
                break
        else:
            raise FileNotFoundError(f"No executable found in {build_dir}")

    return exe_path.resolve()


# ──────────────────────────────────────────────
# 2. Build launch arguments
# ──────────────────────────────────────────────
def build_launch_cmd(
    build_id: str,
    server: ServerInfo,
    token: str,
    mods: Sequence[Path],
    fullscreen: bool = True,
) -> List[str]:
    """
    Compose the argument vector for subprocess.Popen().
    """
    exe = str(locate_executable(build_id))
    args: List[str] = [exe]

    # Server connection
    args += [
        f"--server={server.address}",
        f"--port={server.port}",
        f"--token={token}",
    ]

    # Mods (semicolon-separated absolute paths)
    if mods:
        mods_arg = ";".join(str(p) for p in mods)
        args.append(f"--mods={mods_arg}")

    # Fullscreen / windowed
    args.append("--fullscreen" if fullscreen else "--windowed")

    return args


# ──────────────────────────────────────────────
# 3. Environment preparation
# ──────────────────────────────────────────────
def _prepare_env() -> dict:
    """
    Start with a clean copy of os.environ; add overrides if needed.
    """
    env = os.environ.copy()
    # Example: disable Unity crash reporter on Linux
    env.setdefault("UNITY_DISABLE_CRASH_REPORTER", "1")
    return env


# ──────────────────────────────────────────────
# 4. Public entry – spawn game
# ──────────────────────────────────────────────
def start_game(
    token: str,
    server: ServerInfo,
    build_id: str,
    mods: Sequence[Path] | None = None,
    fullscreen: bool = True,
) -> subprocess.Popen:  # noqa: D401
    """
    Spawn the game client **non-blocking** and return the Popen handle.

    The caller (e.g. FastAPI route) can choose to:
    • detach immediately, letting the webview stay open
    • or terminate/close the UI once the subprocess begins
    """
    mods = mods or []

    cmd = build_launch_cmd(
        build_id=build_id,
        server=server,
        token=token,
        mods=mods,
        fullscreen=fullscreen,
    )

    env = _prepare_env()
    cwd = config.build_path(build_id)

    sys.stdout.write(f"[launcher] Starting game: {' '.join(cmd)}\n")
    proc = subprocess.Popen(cmd, cwd=str(cwd), env=env)

    return proc


# ──────────────────────────────────────────────
# 5. Quick CLI for debugging
# ──────────────────────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    p = argparse.ArgumentParser(description="Launch Hyatlas client manually")
    p.add_argument("build_id")
    p.add_argument("--server", required=True, help="hostname:port")
    p.add_argument("--token", required=True)
    p.add_argument("--mods-json", help="path to JSON list of mod folders")
    p.add_argument("--windowed", action="store_true")
    args = p.parse_args()

    host, port_str = args.server.split(":")
    dummy_server = ServerInfo(
        id="cli",
        name="CLI-Server",
        address=host,
        port=int(port_str),
        online_players=0,
        max_players=0,
        build_id=args.build_id,
        mods=[],
    )

    mod_paths: List[Path] = []
    if args.mods_json:
        mod_paths = [Path(p) for p in json.loads(Path(args.mods_json).read_text())]

    start_game(
        token=args.token,
        server=dummy_server,
        build_id=args.build_id,
        mods=mod_paths,
        fullscreen=not args.windowed,
    )
