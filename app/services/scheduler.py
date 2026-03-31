"""APScheduler jobs for RSS polling and automatic pipeline."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.episode import Episode
from app.models.podcast import Podcast

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _poll_podcast(podcast: Podcast) -> None:
    """Poll one podcast's feed and run the pipeline if auto mode is on."""
    from app.services.downloader import download_episode
    from app.services.publisher import publish_episode
    from app.services.renderer import render_episode
    from app.services.rss import diff_feed, fetch_feed

    logger.info("Polling feed for '%s': %s", podcast.name, podcast.feed_url)
    try:
        parsed = fetch_feed(podcast.feed_url)
    except Exception as exc:
        logger.error("Feed fetch failed for '%s': %s", podcast.name, exc)
        return

    async with AsyncSessionLocal() as session:
        new_episodes = await diff_feed(
            session, parsed, podcast_id=podcast.id, feed_url=podcast.feed_url
        )

        if not settings.flowcast_auto_publish:
            if not new_episodes:
                logger.info("No new episodes for '%s'", podcast.name)
            else:
                logger.info(
                    "Auto-publish disabled. %d new episode(s) available in UI for '%s'.",
                    len(new_episodes), podcast.name,
                )
            return

        # Also pick up episodes already in DB that are stuck in 'discovered' state
        pending_result = await session.execute(
            select(Episode).where(
                Episode.podcast_id == podcast.id,
                Episode.status == "discovered",
            )
        )
        pending = list(pending_result.scalars().all())

        # Combine: new episodes detected this poll + any stuck discovered ones
        all_episodes = list({ep.guid: ep for ep in pending}.values())
        for ep_data in new_episodes:
            result = await session.execute(select(Episode).where(Episode.guid == ep_data.guid))
            ep = result.scalar_one_or_none()
            if ep and ep.guid not in {e.guid for e in all_episodes}:
                all_episodes.append(ep)

        if not all_episodes:
            logger.info("No new episodes for '%s'", podcast.name)
            return

        logger.info("Auto-processing %d episode(s) for '%s'", len(all_episodes), podcast.name)

        for episode in all_episodes:
            try:
                logger.info("Auto-processing: %s", episode.title)
                await download_episode(session, episode)
                await session.refresh(episode)

                # Use podcast's default template if set
                template_id = podcast.default_template_id
                job = await render_episode(session, episode, template_id)
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


async def _poll_all_podcasts() -> None:
    """Poll all active podcasts."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Podcast).where(Podcast.is_active == True)  # noqa: E712
        )
        podcasts = result.scalars().all()

    if not podcasts:
        logger.info("No active podcasts configured yet")
        return

    for podcast in podcasts:
        await _poll_podcast(podcast)


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
        _poll_all_podcasts,
        "interval",
        minutes=settings.poll_interval_minutes,
        id="poll_all_podcasts",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
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
