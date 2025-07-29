# app/api/auth.py
"""
Hyatlas Launcher – Authentication API
====================================

• Leitstelle fürs Frontend (HTML/JS): Login / Logout / Registrierung / Passwort-Reset
• Kommuniziert ausschließlich mit dem selbst gehosteten Identity-Service
• Speichert das erhaltene JWT (bearer-token) **verschlüsselt** in einer Datei
  unter `%LOCALAPPDATA%\\Hyatlas\\auth.json` (Windows) bzw.
  `~/.Hyatlas/auth.json` (macOS/Linux).

Bei `POST /logout` wird die Datei sofort gelöscht; beim Launcher-Start
versucht `/status`, einen vorhandenen Token zu laden und zu verifizieren.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path
from typing import Literal, Optional

import aiohttp
from cryptography.fernet import Fernet, InvalidToken  # pip install cryptography
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core import models

# ────────────────────── Config ──────────────────────────────────
AUTH_SERVER = os.getenv("HYATLAS_AUTH_URL", "http://localhost:9000").rstrip("/")

LOGIN_URL = f"{AUTH_SERVER}/login"
REGISTER_URL = f"{AUTH_SERVER}/register"
FORGOT_URL = f"{AUTH_SERVER}/password/forgot"
RESET_URL = f"{AUTH_SERVER}/password/reset"

# Token-Datei + symm. Schlüssel pro Computer
if sys.platform.startswith("win"):
    BASE_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
else:
    BASE_DIR = Path.home()
TOKEN_DIR = BASE_DIR / "Hyatlas"
TOKEN_DIR.mkdir(exist_ok=True)
TOKEN_FILE = TOKEN_DIR / "auth.json"
KEY_FILE = TOKEN_DIR / ".key"  # Fernet-Key

router = APIRouter(tags=["auth"])

# ────────────────────── Schemas ─────────────────────────────────
class LoginRequest(BaseModel):
    username: str = Field(min_length=4, max_length=32)
    password: str = Field(min_length=4, max_length=128)


class RegisterRequest(LoginRequest):
    email: EmailStr


class ForgotPwRequest(BaseModel):
    email: EmailStr


class ResetPwRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=4, max_length=128)


class LoginResponse(BaseModel):
    token_type: Literal["bearer"] = "bearer"
    access_token: str
    user: models.UserToken


class SimpleMessage(BaseModel):
    detail: str


# ────────────────────── Utils: Crypto & Storage ─────────────────
def _load_key() -> bytes:
    """
    Gibt den (pro Gerät) symmetrischen Schlüssel zurück,
    legt ihn bei Bedarf neu an.
    """
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return key


FERNET = Fernet(_load_key())


def _save_token(token_obj: LoginResponse) -> None:
    try:
        blob = FERNET.encrypt(json.dumps(token_obj.model_dump()).encode())
        TOKEN_FILE.write_bytes(blob)
    except Exception as exc:
        raise HTTPException(500, f"Token konnte nicht gespeichert werden: {exc}") from exc


def _delete_token() -> None:
    TOKEN_FILE.unlink(missing_ok=True)


def _load_token() -> LoginResponse | None:
    if not TOKEN_FILE.exists():
        return None
    try:
        blob = TOKEN_FILE.read_bytes()
        data = json.loads(FERNET.decrypt(blob, ttl=None))
        return LoginResponse(**data)
    except (InvalidToken, json.JSONDecodeError, TypeError):
        # Datei korrupt → löschen
        TOKEN_FILE.unlink(missing_ok=True)
        return None


# ────────────────────── HTTP-Helper ─────────────────────────────
async def _post_json(url: str, payload: dict) -> dict:
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=payload, timeout=10) as resp:
                if resp.status == 401:
                    raise HTTPException(401, "Benutzer/Passwort falsch")
                resp.raise_for_status()
                return await resp.json(content_type=None)
    except aiohttp.ClientError as exc:
        raise HTTPException(502, f"Auth-Service offline: {exc}") from exc


async def _login_remote(body: LoginRequest) -> LoginResponse:
    data = await _post_json(LOGIN_URL, body.model_dump())
    try:
        return LoginResponse(
            access_token=data["access_token"],
            user=models.UserToken(**data["user"]),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(502, "Unerwartetes Antwortformat") from exc


# ────────────────────── Routes ──────────────────────────────────
@router.get("/status", response_model=Optional[LoginResponse])
async def login_status():
    """
    Prüft, ob ein gültiger Token lokal gespeichert ist
    und gibt ihn (inklusiv User-Payload) zurück.
    """
    return _load_token()


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    token_obj = await _login_remote(body)
    _save_token(token_obj)
    return token_obj


@router.post("/logout", response_model=SimpleMessage)
async def logout():
    _delete_token()
    return SimpleMessage(detail="Abgemeldet")


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(body: RegisterRequest):
    await _post_json(REGISTER_URL, body.model_dump())
    token_obj = await _login_remote(LoginRequest(username=body.username, password=body.password))
    _save_token(token_obj)
    return token_obj


@router.post("/password/forgot", response_model=SimpleMessage)
async def password_forgot(body: ForgotPwRequest):
    await _post_json(FORGOT_URL, body.model_dump())
    return SimpleMessage(detail="Reset-E-Mail gesendet")


@router.post("/password/reset", response_model=SimpleMessage)
async def password_reset(body: ResetPwRequest):
    await _post_json(RESET_URL, body.model_dump())
    return SimpleMessage(detail="Passwort geändert")