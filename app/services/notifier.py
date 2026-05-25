import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.utils.url_validator import _SSRFSafeTransport, validate_external_url

logger = logging.getLogger(__name__)


async def notify(event: str, payload: dict) -> None:
    """Send a webhook notification. Best-effort — logs errors but never raises."""
    if not settings.webhook_url:
        return

    try:
        validate_external_url(settings.webhook_url)
    except ValueError as exc:
        logger.warning("Webhook URL inválida (%s): %s", event, exc)
        return

    body = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    data = json.dumps(body, ensure_ascii=False).encode()

    headers = {"Content-Type": "application/json"}
    if settings.webhook_secret:
        sig = hmac.new(settings.webhook_secret.encode(), data, hashlib.sha256).hexdigest()
        headers["X-FlowCast-Signature"] = f"sha256={sig}"

    try:
        async with httpx.AsyncClient(
            transport=_SSRFSafeTransport(), timeout=settings.webhook_timeout
        ) as client:
            r = await client.post(settings.webhook_url, content=data, headers=headers)
            r.raise_for_status()
            logger.debug("Webhook entregado: %s", event)
    except Exception as exc:
        logger.warning("Webhook fallido (%s): %s", event, exc)
