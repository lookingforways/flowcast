"""RSS feed fetching and episode diffing."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.episode import Episode

logger = logging.getLogger(__name__)


@dataclass
class ParsedEpisode:
    guid: str
    title: str
    description: str
    mp3_url: str
    duration_secs: Optional[int]
    pub_date: Optional[datetime]


def _extract_mp3_url(entry: feedparser.FeedParserDict) -> Optional[str]:
    """Return the first enclosure URL that looks like an audio file."""
    for enc in getattr(entry, "enclosures", []):
        url = enc.get("href", "") or enc.get("url", "")
        mime = enc.get("type", "")
        if "audio" in mime or url.lower().endswith(".mp3"):
            return url
    # Some feeds put the link directly
    link = getattr(entry, "link", "")
    if link and link.lower().endswith(".mp3"):
        return link
    return None


def _parse_duration(entry: feedparser.FeedParserDict) -> Optional[int]:
    """Return duration in seconds from itunes:duration or similar."""
    itunes = getattr(entry, "itunes_duration", None)
    if itunes:
        parts = str(itunes).split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            return int(parts[0])
        except (ValueError, IndexError):
            pass
    return None


def _parse_pub_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    raw = getattr(entry, "published", None)
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            pass
    return None


def _clean_html(text: str) -> str:
    """Strip HTML tags for plain-text description fallback."""
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_feed(feed_url: str) -> list[ParsedEpisode]:
    """Parse the RSS feed and return a list of ParsedEpisode objects."""
    feed = feedparser.parse(feed_url)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Failed to parse feed: {feed_url} — {feed.bozo_exception}")

    episodes: list[ParsedEpisode] = []
    for entry in feed.entries:
        mp3_url = _extract_mp3_url(entry)
        if not mp3_url:
            logger.debug("Skipping entry without audio enclosure: %s", entry.get("title"))
            continue

        guid = entry.get("id") or entry.get("guid") or mp3_url
        title = entry.get("title", "Untitled Episode")

        # Prefer content over summary for show notes
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        if not content:
            content = entry.get("summary", "")

        episodes.append(
            ParsedEpisode(
                guid=guid,
                title=title,
                description=content,
                mp3_url=mp3_url,
                duration_secs=_parse_duration(entry),
                pub_date=_parse_pub_date(entry),
            )
        )

    logger.info("Fetched %d episodes from %s", len(episodes), feed_url)
    return episodes


async def diff_feed(session: AsyncSession, parsed: list[ParsedEpisode]) -> list[ParsedEpisode]:
    """Return only episodes not already in the database. Insert new ones."""
    if not parsed:
        return []

    guids = [ep.guid for ep in parsed]
    existing = set(
        row[0]
        for row in (await session.execute(select(Episode.guid).where(Episode.guid.in_(guids)))).all()
    )

    new_episodes: list[ParsedEpisode] = []
    for ep in parsed:
        if ep.guid not in existing:
            db_ep = Episode(
                guid=ep.guid,
                feed_url=settings.rss_feed_url,
                title=ep.title,
                description=ep.description,
                mp3_url=ep.mp3_url,
                duration_secs=ep.duration_secs,
                pub_date=ep.pub_date,
                status="discovered",
            )
            session.add(db_ep)
            new_episodes.append(ep)

    if new_episodes:
        await session.commit()
        logger.info("Discovered %d new episodes", len(new_episodes))

    return new_episodes
