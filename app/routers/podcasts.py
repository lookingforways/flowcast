from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.podcast import Podcast
from app.schemas.podcast import PodcastCreate, PodcastOut, PodcastUpdate

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


@router.get("", response_model=list[PodcastOut])
async def list_podcasts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Podcast).order_by(Podcast.id))
    return result.scalars().all()


@router.post("", response_model=PodcastOut, status_code=201)
async def create_podcast(body: PodcastCreate, session: AsyncSession = Depends(get_session)):
    podcast = Podcast(**body.model_dump())
    session.add(podcast)
    await session.commit()
    await session.refresh(podcast)
    return podcast


@router.get("/{podcast_id}", response_model=PodcastOut)
async def get_podcast(podcast_id: int, session: AsyncSession = Depends(get_session)):
    podcast = await session.get(Podcast, podcast_id)
    if podcast is None:
        raise HTTPException(404, "Podcast not found")
    return podcast


@router.put("/{podcast_id}", response_model=PodcastOut)
async def update_podcast(
    podcast_id: int, body: PodcastUpdate, session: AsyncSession = Depends(get_session)
):
    podcast = await session.get(Podcast, podcast_id)
    if podcast is None:
        raise HTTPException(404, "Podcast not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(podcast, k, v)
    await session.commit()
    await session.refresh(podcast)
    return podcast


@router.delete("/{podcast_id}", status_code=204)
async def delete_podcast(podcast_id: int, session: AsyncSession = Depends(get_session)):
    import logging
    from pathlib import Path

    from app.models.episode import Episode
    from app.models.job import RenderJob

    logger = logging.getLogger(__name__)

    podcast = await session.get(Podcast, podcast_id)
    if podcast is None:
        raise HTTPException(404, "Podcast not found")

    # Collect all episodes to get their file paths before deleting
    episodes_result = await session.execute(
        select(Episode).where(Episode.podcast_id == podcast_id)
    )
    episodes = episodes_result.scalars().all()
    episode_ids = [ep.id for ep in episodes]

    # Collect files to delete from disk
    files_to_delete: list[Path] = []
    for ep in episodes:
        if ep.mp3_path:
            files_to_delete.append(Path(ep.mp3_path))
        if ep.render_path:
            files_to_delete.append(Path(ep.render_path))

    # Delete render jobs first (FK constraint)
    if episode_ids:
        await session.execute(
            delete(RenderJob).where(RenderJob.episode_id.in_(episode_ids))
        )

    # Delete episodes
    await session.execute(delete(Episode).where(Episode.podcast_id == podcast_id))

    # Delete podcast
    await session.delete(podcast)
    await session.commit()

    # Delete files from disk after DB commit
    for path in files_to_delete:
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            logger.warning("Could not delete file %s: %s", path, exc)


@router.post("/{podcast_id}/poll", status_code=202)
async def poll_podcast(
    podcast_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger an RSS poll for a single podcast."""
    podcast = await session.get(Podcast, podcast_id)
    if podcast is None:
        raise HTTPException(404, "Podcast not found")
    background_tasks.add_task(_run_poll, podcast_id)
    return {"message": f"Polling feed for '{podcast.name}'"}


async def _run_poll(podcast_id: int) -> None:
    from app.database import AsyncSessionLocal
    from app.services.rss import diff_feed, fetch_feed

    async with AsyncSessionLocal() as session:
        podcast = await session.get(Podcast, podcast_id)
        if not podcast:
            return
        try:
            parsed = fetch_feed(podcast.feed_url)
            await diff_feed(session, parsed, podcast_id=podcast_id)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "Poll failed for podcast %d: %s", podcast_id, exc
            )
