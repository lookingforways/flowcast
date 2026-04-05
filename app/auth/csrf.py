"""CSRF token generation and validation using itsdangerous."""
from __future__ import annotations

import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

CSRF_COOKIE = "fc_csrf"
_CSRF_SALT = "flowcast-csrf"
_CSRF_MAX_AGE = 3600  # 1 hour


def _s() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt=_CSRF_SALT)


def new_csrf_token() -> str:
    """Generate a new signed CSRF token containing a random nonce."""
    return _s().dumps(secrets.token_hex(16))


def is_valid_token(token: str) -> bool:
    """Return True if token is a valid, unexpired signed token."""
    if not token:
        return False
    try:
        _s().loads(token, max_age=_CSRF_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def verify_csrf(form_token: str, cookie_token: str) -> bool:
    """Return True only if both tokens are valid, unexpired, and carry the same nonce."""
    if not form_token or not cookie_token:
        return False
    try:
        form_nonce = _s().loads(form_token, max_age=_CSRF_MAX_AGE)
        cookie_nonce = _s().loads(cookie_token, max_age=_CSRF_MAX_AGE)
        return secrets.compare_digest(str(form_nonce), str(cookie_nonce))
    except (BadSignature, SignatureExpired):
        return False
