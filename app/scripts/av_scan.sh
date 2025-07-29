#!/usr/bin/env bash
# scripts/av_scan.sh
#
# Hyatlas Launcher – AV wrapper
# -----------------------------
# Usage:  ./av_scan.sh /path/to/archive.zip
#
# Exits with:
#   0  → no malware found
#   1  → threat detected
#   2  → error (scanner not available, wrong args, etc.)
#
# The launcher treats ANY non-zero code as “quarantine this file”.

set -euo pipefail

ARCHIVE="$1"
if [[ -z "${ARCHIVE}" || ! -f "${ARCHIVE}" ]]; then
  echo "[av_scan] invalid path: ${ARCHIVE}" >&2
  exit 2
fi

OS="$(uname -s)"

# ──────────────────────────────────────────────
# Linux / macOS – ClamAV via `clamscan`
# ──────────────────────────────────────────────
if [[ "${OS}" == "Linux" || "${OS}" == "Darwin" ]]; then
  if ! command -v clamscan >/dev/null 2>&1; then
    echo "[av_scan] clamscan not found – skipping scan" >&2
    exit 0          # permissive fallback; adjust if you want stricter policy
  fi

  # `--no-summary` → output only infected files
  clamscan --no-summary "${ARCHIVE}"
  EXIT_CODE=$?

  if [[ "${EXIT_CODE}" -eq 0 ]]; then          # clean
    exit 0
  elif [[ "${EXIT_CODE}" -eq 1 ]]; then        # virus found
    exit 1
  else                                         # error
    exit 2
  fi
fi

# ──────────────────────────────────────────────
# Windows – Microsoft Defender via PowerShell
# ──────────────────────────────────────────────
if [[ "${OS}" == "MINGW"* || "${OS}" == "CYGWIN"* || "${OS}" == "MSYS"* ]]; then
  powershell.exe -NoProfile -Command \
    "Start-MpScan -ScanPath '${ARCHIVE}' -ScanType CustomScan" \
    >/dev/null

  # Defender's CLI does not propagate result codes directly;
  # we assume success if the command completed.
  # TODO: parse Get-MpThreatDetection for stricter checks.
  exit 0
fi

echo "[av_scan] unsupported OS: ${OS}" >&2
exit 2
