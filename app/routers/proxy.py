"""Image proxy — fetches external images server-side to avoid CSP issues."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.utils.url_validator import validate_external_url

router = APIRouter(prefix="/api", tags=["proxy"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml", "image/x-icon"}
_MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@router.get("/img")
async def proxy_image(url: str = Query(...)):
    """Proxy an external image through the server.

    Validates the URL against SSRF attacks before fetching.
    Returns the image with its original content-type.
    """
    try:
        validate_external_url(url)
    except ValueError:
        return Response(status_code=400)

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, max_redirects=3) as client:
            resp = await client.get(url, headers={"User-Agent": "Flowcast/1.0"})

        if resp.status_code != 200:
            return Response(status_code=502)

        content_type = resp.headers.get("content-type", "").split(";")[0].strip()
        if content_type not in _ALLOWED_CONTENT_TYPES:
            return Response(status_code=415)

        if len(resp.content) > _MAX_SIZE:
            return Response(status_code=502)

        return Response(
            content=resp.content,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    except httpx.RequestError:
        return Response(status_code=502)
