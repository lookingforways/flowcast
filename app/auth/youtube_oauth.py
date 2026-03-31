"""YouTube OAuth2 flow using google-auth-oauthlib."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
]

REDIRECT_URI_PATH = "/auth/youtube/callback"


def _get_fernet() -> Fernet:
    """Derive a Fernet key from SECRET_KEY for token encryption."""
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{settings.app_base_url}{REDIRECT_URI_PATH}"],
        }
    }


def create_flow() -> Flow:
    return Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=f"{settings.app_base_url}{REDIRECT_URI_PATH}",
    )


def get_authorization_url() -> tuple[str, str]:
    """Return (auth_url, state) for the OAuth2 redirect."""
    flow = create_flow()
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state


def exchange_code(code: str, state: str) -> Credentials:
    """Exchange auth code for credentials and save them."""
    flow = create_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_credentials(creds)
    return creds


def save_credentials(creds: Credentials) -> None:
    token_path = settings.youtube_token_path
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    encrypted = _get_fernet().encrypt(json.dumps(token_data).encode())
    token_path.write_bytes(encrypted)
    os.chmod(token_path, 0o600)
    logger.info("YouTube credentials saved (encrypted) to %s", token_path)


def load_credentials() -> Optional[Credentials]:
    token_path = settings.youtube_token_path
    if not token_path.exists():
        return None
    try:
        raw = token_path.read_bytes()
        try:
            data = json.loads(_get_fernet().decrypt(raw))
        except (InvalidToken, Exception):
            # Migration: file may be plain JSON from before encryption was added
            data = json.loads(raw.decode())
            # Re-save encrypted
            token_path.write_bytes(_get_fernet().encrypt(json.dumps(data).encode()))
            os.chmod(token_path, 0o600)
            logger.info("Migrated YouTube token to encrypted format")
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id", settings.google_client_id),
            client_secret=data.get("client_secret", settings.google_client_secret),
            scopes=data.get("scopes", SCOPES),
        )
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_credentials(creds)
        return creds
    except Exception as exc:
        logger.error("Failed to load YouTube credentials: %s", exc)
        return None


def revoke_credentials() -> None:
    token_path = settings.youtube_token_path
    if token_path.exists():
        token_path.unlink()
        logger.info("YouTube credentials revoked")


def is_connected() -> bool:
    return load_credentials() is not None
