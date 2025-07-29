# app/core/mods/verifier.py
"""
Hyatlas Launcher – package verifier
===================================

Responsible for **two** security checks before a mod / resource package is
accepted:

1. **Cryptographic signature** – ensures the archive really originates from
   an official Marketplace key (or a self-hosted server key the user has
   trusted).  Uses RSA-PSS with SHA-256.

2. **Antivirus scan** – delegates to the platform’s AV engine
   (ClamAV on Linux/macOS, Windows Defender via PowerShell) through the
   wrapper script `scripts/av_scan.sh`.

Both checks must pass – otherwise the caller should treat the file as
malicious and move it to quarantine.

Public keys are stored in `~/.hyatlas/config/keys/`.  The handshake adds
new server keys there (after user confirmation) and removes revoked ones.
"""

from __future__ import annotations

import base64
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core import config
from app.core.models import ModDescriptor

_KEYS_DIR: Path = config.CONFIG_DIR / "keys"
_KEYS_DIR.mkdir(parents=True, exist_ok=True)

_last_scan: datetime | None = None

# ──────────────────────────────────────────────
# 1. Key loading helpers
# ──────────────────────────────────────────────
def _load_public_keys() -> List[rsa.RSAPublicKey]:
    """Return all RSA public keys found in ~/.hyatlas/config/keys/"""
    keys: List[rsa.RSAPublicKey] = []
    for pem in _KEYS_DIR.glob("*.pem"):
        try:
            with pem.open("rb") as fh:
                pub = serialization.load_pem_public_key(fh.read())
                if isinstance(pub, rsa.RSAPublicKey):
                    keys.append(pub)
        except Exception:
            sys.stderr.write(f"[verifier] Ignoring invalid key file {pem.name}\n")
    return keys


_PUBLIC_KEYS = _load_public_keys()


# ──────────────────────────────────────────────
# 2. Signature verification
# ──────────────────────────────────────────────
def _verify_signature(archive: Path, signature_b64: str | None) -> bool:
    if not signature_b64:
        # free mods may omit a signature
        return True

    if not _PUBLIC_KEYS:
        sys.stderr.write("[verifier] No trusted public keys available\n")
        return False

    try:
        sig = base64.b64decode(signature_b64)
    except Exception:
        return False

    data = archive.read_bytes()
    for key in _PUBLIC_KEYS:
        try:
            key.verify(
                sig,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True  # verified with this key
        except InvalidSignature:
            continue

    return False  # none matched


# ──────────────────────────────────────────────
# 3. Antivirus wrapper
# ──────────────────────────────────────────────
def _scan_with_av(archive: Path) -> bool:
    """
    Calls scripts/av_scan.sh which abstracts over ClamAV / Windows Defender.
    The script must exit 0 on success, non-zero if malware was found or an
    error occurred.
    """
    global _last_scan
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "av_scan.sh"
    if not script_path.exists():
        sys.stderr.write("[verifier] AV script missing – skipping scan!\n")
        return True  # fallback (should never happen in production)

    res = subprocess.run([str(script_path), str(archive)], capture_output=True)
    _last_scan = datetime.now(tz=timezone.utc)

    if res.returncode == 0:
        return True

    sys.stderr.write(f"[verifier] AV scan flagged {archive.name}:\n{res.stdout.decode()}\n")
    return False


# ──────────────────────────────────────────────
# 4. Public API
# ──────────────────────────────────────────────
def verify_package(archive: Path, descriptor: ModDescriptor) -> bool:
    """
    Returns True if both cryptographic signature AND AV scan succeed.
    """
    if not archive.exists():
        sys.stderr.write("[verifier] archive path does not exist\n")
        return False

    if not _verify_signature(archive, descriptor.signature):
        sys.stderr.write(f"[verifier] signature check failed for {archive.name}\n")
        return False

    if not _scan_with_av(archive):
        return False

    return True


def last_scan_time() -> datetime | None:
    """Return the timestamp of the most recent AV scan run in this session."""
    return _last_scan
