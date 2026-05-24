import logging
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

from app.auth.session import get_session, set_session
from app.auth.youtube_oauth import (
    exchange_code,
    get_authorization_url,
    is_connected,
    load_credentials,
    revoke_credentials,
)
from app.config import settings

router = APIRouter(tags=["youtube"])


@router.get("/api/youtube/status")
async def youtube_status():
    if not is_connected():
        return {"connected": False, "channel": None}

    try:
        from app.services.publisher import get_channel_info
        channel = await get_channel_info()
        return {"connected": True, "channel": channel}
    except Exception as exc:
        logger.error("YouTube status check failed: %s", exc)
        return {"connected": False, "channel": None, "error": "YouTube connection error. Check server logs."}


@router.get("/auth/youtube")
async def youtube_auth(request: Request):
    if not settings.google_client_id or not settings.google_client_secret:
        from urllib.parse import urlparse
        referer = request.headers.get("referer", "")
        back = urlparse(referer).path if referer else "/"
        if not back or back == "/auth/youtube":
            back = "/"
        return RedirectResponse(f"{back}?yt_config_error=1")
    url, state = get_authorization_url()
    session = get_session(request)
    session["oauth_state"] = state
    response = RedirectResponse(url)
    set_session(response, session)
    return response


@router.get("/auth/youtube/callback")
async def youtube_callback(request: Request, code: str, state: str = ""):
    session = get_session(request)
    stored_state = session.get("oauth_state", "")
    if not stored_state or not secrets.compare_digest(stored_state, state):
        logger.warning("OAuth state mismatch — possible CSRF attempt")
        return RedirectResponse("/settings?youtube=error")
    session.pop("oauth_state", None)
    try:
        exchange_code(code, state)
        response = RedirectResponse("/settings?youtube=connected")
        set_session(response, session)
        return response
    except Exception as exc:
        logger.error("YouTube OAuth callback failed: %s", exc)
        return RedirectResponse("/settings?youtube=error")


@router.post("/api/youtube/disconnect")
async def youtube_disconnect():
    revoke_credentials()
    return {"disconnected": True}
