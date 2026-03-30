"""APScheduler jobs for RSS polling and automatic pipeline."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.episode import Episode

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _poll_and_process() -> None:
    """Fetch feed, discover new episodes, and run the pipeline if auto mode."""
    from app.services.downloader import download_episode
    from app.services.publisher import publish_episode
    from app.services.renderer import render_episode
    from app.services.rss import fetch_feed, diff_feed

    if not settings.rss_feed_url:
        logger.warning("RSS_FEED_URL not set, skipping poll")
        return

    logger.info("Polling RSS feed: %s", settings.rss_feed_url)
    try:
        parsed = fetch_feed(settings.rss_feed_url)
    except Exception as exc:
        logger.error("Feed fetch failed: %s", exc)
        return

    async with AsyncSessionLocal() as session:
        new_episodes = await diff_feed(session, parsed)

        if not new_episodes:
            logger.info("No new episodes found")
            return

        logger.info("Found %d new episode(s)", len(new_episodes))

        if not settings.flowcast_auto_publish:
            logger.info("Auto-publish disabled. New episodes available in UI.")
            return

        # Full automatic pipeline
        for ep_data in new_episodes:
            result = await session.execute(
                select(Episode).where(Episode.guid == ep_data.guid)
            )
            episode = result.scalar_one_or_none()
            if episode is None:
                continue

            try:
                logger.info("Auto-processing episode: %s", episode.title)
                await download_episode(session, episode)
                await session.refresh(episode)

                job = await render_episode(session, episode)
                await session.refresh(episode)

                if job.status == "done":
                    await publish_episode(session, episode)
                else:
                    logger.error("Render failed for episode %d, skipping publish", episode.id)

            except Exception as exc:
                logger.error("Auto-pipeline failed for episode %d: %s", episode.id, exc)
                episode.status = "failed"
                episode.error_msg = str(exc)
                await session.commit()


async def _cleanup_old_renders() -> None:
    """Delete MP4 renders older than MAX_RENDER_AGE_DAYS to free disk space."""
    if settings.max_render_age_days <= 0:
        return

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=settings.max_render_age_days)
    renders_dir = settings.renders_dir

    if not renders_dir.exists():
        return

    deleted = 0
    for mp4 in renders_dir.glob("*.mp4"):
        mtime = datetime.fromtimestamp(mp4.stat().st_mtime)
        if mtime < cutoff:
            mp4.unlink()
            deleted += 1

    if deleted:
        logger.info("Cleaned up %d old render(s)", deleted)

    # Update DB: clear render_path for deleted files
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Episode).where(Episode.render_path.isnot(None), Episode.status == "published")
        )
        for episode in result.scalars():
            if episode.render_path and not __import__("pathlib").Path(episode.render_path).exists():
                episode.render_path = None
        await session.commit()


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        _poll_and_process,
        "interval",
        minutes=settings.poll_interval_minutes,
        id="poll_rss",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # Run once immediately on startup
    )

    _scheduler.add_job(
        _cleanup_old_renders,
        "cron",
        hour=3,
        minute=0,
        id="cleanup_renders",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started. RSS poll every %d min. Auto-publish: %s",
        settings.poll_interval_minutes,
        settings.flowcast_auto_publish,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
