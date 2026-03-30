"""YouTube publisher: uploads rendered MP4s via YouTube Data API v3."""
from __future__ import annotations

import logging
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.youtube_oauth import load_credentials
from app.config import settings
from app.models.episode import Episode

logger = logging.getLogger(__name__)

# YouTube title limit
_MAX_TITLE_LEN = 100
# YouTube description limit
_MAX_DESC_LEN = 5000


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


async def get_channel_info() -> dict:
    """Return basic channel info for the authenticated user."""
    creds = load_credentials()
    if not creds:
        raise RuntimeError("YouTube not connected. Complete OAuth2 flow first.")
    youtube = build("youtube", "v3", credentials=creds)
    resp = youtube.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        return {"id": "", "title": "Unknown Channel"}
    ch = items[0]
    return {
        "id": ch["id"],
        "title": ch["snippet"]["title"],
        "thumbnail": ch["snippet"]["thumbnails"].get("default", {}).get("url", ""),
    }


async def publish_episode(session: AsyncSession, episode: Episode) -> str:
    """Upload the rendered MP4 to YouTube. Returns the YouTube video ID."""
    if not episode.render_path or not Path(episode.render_path).exists():
        raise ValueError(f"Episode {episode.id} has no render at {episode.render_path!r}")

    creds = load_credentials()
    if not creds:
        raise RuntimeError("YouTube not connected. Complete OAuth2 flow first.")

    youtube = build("youtube", "v3", credentials=creds)

    title = _truncate(episode.title, _MAX_TITLE_LEN)
    description = _truncate(episode.description or "", _MAX_DESC_LEN)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": settings.youtube_category_id,
        },
        "status": {
            "privacyStatus": settings.youtube_privacy,
        },
    }

    media = MediaFileUpload(
        episode.render_path,
        mimetype="video/mp4",
        chunksize=-1,
        resumable=True,
    )

    logger.info("Uploading to YouTube: %s (privacy=%s)", title, settings.youtube_privacy)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            logger.info("  Upload progress: %d%%", pct)

    video_id = response["id"]
    logger.info("Uploaded to YouTube: https://youtu.be/%s", video_id)

    # Assign to playlist if the podcast has one configured
    playlist_id = None
    if episode.podcast_id:
        from app.models.podcast import Podcast
        podcast = await session.get(Podcast, episode.podcast_id)
        if podcast and podcast.youtube_playlist_id:
            playlist_id = podcast.youtube_playlist_id

    if playlist_id:
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            logger.info("Added video %s to playlist %s", video_id, playlist_id)
        except Exception as exc:
            logger.warning("Could not add video to playlist: %s", exc)

    episode.youtube_id = video_id
    episode.status = "published"
    episode.error_msg = None
    await session.commit()

    return video_id
