"""Streaming MP3 downloader with progress tracking."""
from __future__ import annotations

import logging
import re
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.episode import Episode

logger = logging.getLogger(__name__)

_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")


def _safe_filename(guid: str) -> str:
    """Convert a GUID to a safe filename."""
    safe = _SAFE_FILENAME_RE.sub("_", guid)
    return safe[:200] + ".mp3"


async def download_episode(session: AsyncSession, episode: Episode) -> Path:
    """Download the MP3 for an episode. Updates episode.status in DB."""
    dest_dir = settings.downloads_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = _safe_filename(episode.guid)
    dest_path = dest_dir / filename

    if dest_path.exists() and dest_path.stat().st_size > 0:
        logger.info("MP3 already exists: %s", dest_path)
        episode.mp3_path = str(dest_path)
        episode.status = "downloaded"
        await session.commit()
        return dest_path

    logger.info("Downloading %s → %s", episode.mp3_url, dest_path)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
            async with client.stream("GET", episode.mp3_url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = downloaded / total * 100
                            logger.debug("  %.1f%%", pct)

        episode.mp3_path = str(dest_path)
        episode.status = "downloaded"
        episode.error_msg = None
        await session.commit()
        logger.info("Download complete: %s (%.1f MB)", dest_path, dest_path.stat().st_size / 1_048_576)
        return dest_path

    except Exception as exc:
        logger.error("Download failed for episode %d: %s", episode.id, exc)
        episode.status = "failed"
        episode.error_msg = str(exc)
        await session.commit()
        if dest_path.exists():
            dest_path.unlink()
        raise
