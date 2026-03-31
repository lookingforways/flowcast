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
    from app.models.episode import Episode

    podcast = await session.get(Podcast, podcast_id)
    if podcast is None:
        raise HTTPException(404, "Podcast not found")
    await session.execute(delete(Episode).where(Episode.podcast_id == podcast_id))
    await session.delete(podcast)
    await session.commit()


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
