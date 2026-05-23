"""RSS feed fetching and episode diffing."""
from __future__ import annotations

import http.client
import logging
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.episode import Episode
from app.utils.html_sanitizer import sanitize_html
from app.utils.url_validator import _check_ip_str, validate_external_url

logger = logging.getLogger(__name__)


class _SSRFRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            validate_external_url(newurl)
        except ValueError as exc:
            raise urllib.error.URLError(f"SSRF redirect blocked: {exc}") from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _SafeHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that validates resolved IPs at connect time (closes DNS TOCTOU gap)."""
    def connect(self) -> None:
        for info in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            _check_ip_str(info[4][0])
        super().connect()


class _SafeHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that validates resolved IPs at connect time (closes DNS TOCTOU gap)."""
    def connect(self) -> None:
        for info in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):
            _check_ip_str(info[4][0])
        super().connect()


class _SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_SafeHTTPConnection, req)


class _SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_SafeHTTPSConnection, req, context=self._context)


@dataclass
class ParsedEpisode:
    guid: str
    title: str
    description: str
    mp3_url: str
    duration_secs: Optional[int]
    pub_date: Optional[datetime]


def _extract_mp3_url(entry: feedparser.FeedParserDict) -> Optional[str]:
    for enc in getattr(entry, "enclosures", []):
        url = enc.get("href", "") or enc.get("url", "")
        mime = enc.get("type", "")
        if "audio" in mime or url.lower().endswith(".mp3"):
            # Only allow http/https — reject javascript: and other schemes
            if url.startswith(("http://", "https://")):
                return url
    link = getattr(entry, "link", "")
    if link and link.lower().endswith(".mp3") and link.startswith(("http://", "https://")):
        return link
    return None


def _parse_duration(entry: feedparser.FeedParserDict) -> Optional[int]:
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


def fetch_feed(feed_url: str) -> list[ParsedEpisode]:
    """Parse the RSS feed and return a list of ParsedEpisode objects."""
    validate_external_url(feed_url)
    feed = feedparser.parse(feed_url, handlers=[_SSRFRedirectHandler(), _SafeHTTPHandler(), _SafeHTTPSHandler()])
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

        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        if not content:
            content = entry.get("summary", "")

        episodes.append(
            ParsedEpisode(
                guid=guid,
                title=title,
                description=sanitize_html(content),
                mp3_url=mp3_url,
                duration_secs=_parse_duration(entry),
                pub_date=_parse_pub_date(entry),
            )
        )

    logger.info("Fetched %d episodes from %s", len(episodes), feed_url)
    return episodes


async def diff_feed(
    session: AsyncSession,
    parsed: list[ParsedEpisode],
    podcast_id: int,
    feed_url: str = "",
) -> list[ParsedEpisode]:
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
                podcast_id=podcast_id,
                feed_url=feed_url,
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
        logger.info("Discovered %d new episodes (podcast_id=%d)", len(new_episodes), podcast_id)

    return new_episodes
