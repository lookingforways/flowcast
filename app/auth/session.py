"""Cookie-based session management using itsdangerous signed cookies."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

COOKIE_NAME = "flowcast_session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="flowcast-session")


def get_session(request: Request) -> dict:
    """Read and verify the session cookie. Returns empty dict if invalid."""
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return {}
    try:
        data = _serializer().loads(cookie, max_age=settings.session_max_age)
        return data if isinstance(data, dict) else {}
    except (BadSignature, SignatureExpired):
        return {}


def set_session(response: Response, data: dict) -> None:
    """Write signed session data to cookie."""
    signed = _serializer().dumps(data)
    response.set_cookie(
        COOKIE_NAME,
        signed,
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.app_base_url.startswith("https://"),
    )


def clear_session(response: Response) -> None:
    """Delete the session cookie."""
    response.delete_cookie(COOKIE_NAME)


def is_fully_authenticated(request: Request) -> bool:
    """Return True if the user has completed both password and 2FA verification."""
    session = get_session(request)
    return session.get("authenticated") is True and session.get("totp_verified") is True


def is_password_verified(request: Request) -> bool:
    """Return True if the user has completed the password step."""
    return get_session(request).get("authenticated") is True
