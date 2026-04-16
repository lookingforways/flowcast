"""TOTP (Time-based One-Time Password) management using pyotp."""
from __future__ import annotations

import base64
import io
import logging

import pyotp
import qrcode

from app.config import settings

logger = logging.getLogger(__name__)


def get_or_create_secret() -> str:
    """Return the TOTP secret, creating it on first call."""
    path = settings.totp_secret_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        secret = path.read_text().strip()
        if secret:
            return secret

    # Generate a new secret — restrict permissions before writing (prevents race condition)
    import os
    secret = pyotp.random_base32()
    old_umask = os.umask(0o177)
    try:
        path.write_text(secret)
    finally:
        os.umask(old_umask)
    os.chmod(path, 0o600)
    logger.info("Generated new TOTP secret at %s", path)
    return secret


def verify_token(token: str) -> bool:
    """Verify a 6-digit TOTP token. Allows 1 step of clock drift."""
    secret = get_or_create_secret()
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


def get_provisioning_uri() -> str:
    """Return the otpauth:// URI for QR code generation."""
    secret = get_or_create_secret()
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=settings.admin_username, issuer_name="FlowCast")


def get_qr_code_base64() -> str:
    """Return a base64-encoded PNG QR code for the provisioning URI."""
    uri = get_provisioning_uri()
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def is_2fa_configured() -> bool:
    """Return True if a TOTP secret has been generated."""
    path = settings.totp_secret_path
    return path.exists() and bool(path.read_text().strip())
