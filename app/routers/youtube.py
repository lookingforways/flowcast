import logging

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

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
async def youtube_auth():
    if not settings.google_client_id or not settings.google_client_secret:
        return {
            "error": "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env"
        }
    url, _ = get_authorization_url()
    return RedirectResponse(url)


@router.get("/auth/youtube/callback")
async def youtube_callback(code: str, state: str = ""):
    try:
        exchange_code(code, state)
        return RedirectResponse("/settings?youtube=connected")
    except Exception as exc:
        logger.error("YouTube OAuth callback failed: %s", exc)
        return RedirectResponse("/settings?youtube=error")


@router.post("/api/youtube/disconnect")
async def youtube_disconnect():
    revoke_credentials()
    return {"disconnected": True}
