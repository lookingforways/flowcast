from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.episode import Episode
from app.schemas.episode import EpisodeList, EpisodeOut
from app.schemas.job import JobOut

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.get("", response_model=EpisodeList)
async def list_episodes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    q = select(Episode).order_by(Episode.pub_date.desc().nullslast(), Episode.created_at.desc())
    if status:
        q = q.where(Episode.status == status)

    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await session.execute(q.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    return EpisodeList(items=list(items), total=total, page=page, per_page=per_page)


@router.get("/{episode_id}", response_model=EpisodeOut)
async def get_episode(episode_id: int, session: AsyncSession = Depends(get_session)):
    ep = await session.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(404, "Episode not found")
    return ep


@router.post("/{episode_id}/download", response_model=EpisodeOut)
async def trigger_download(
    episode_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    from app.services.downloader import download_episode

    ep = await session.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(404, "Episode not found")
    if ep.status not in ("discovered", "failed"):
        raise HTTPException(400, f"Episode is in status '{ep.status}', cannot download")

    background_tasks.add_task(_run_download, episode_id)
    return ep


async def _run_download(episode_id: int) -> None:
    from app.database import AsyncSessionLocal
    from app.services.downloader import download_episode

    async with AsyncSessionLocal() as session:
        ep = await session.get(Episode, episode_id)
        if ep:
            await download_episode(session, ep)


@router.post("/{episode_id}/render", response_model=JobOut)
async def trigger_render(
    episode_id: int,
    template_id: int | None = Query(None),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session),
):
    from app.services.renderer import render_episode

    ep = await session.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(404, "Episode not found")
    if ep.status not in ("downloaded", "rendered", "failed"):
        raise HTTPException(400, f"Episode must be downloaded first (current: '{ep.status}')")

    background_tasks.add_task(_run_render, episode_id, template_id)
    # Return a placeholder response; actual job created async
    from app.models.job import RenderJob
    from app.schemas.job import JobOut as JobOutSchema
    from datetime import datetime
    placeholder = {
        "id": 0,
        "episode_id": episode_id,
        "template_id": template_id or 0,
        "status": "queued",
        "ffmpeg_cmd": None,
        "ffmpeg_log": None,
        "started_at": None,
        "finished_at": None,
        "error_msg": None,
        "created_at": datetime.utcnow(),
    }
    return placeholder


async def _run_render(episode_id: int, template_id: int | None) -> None:
    from app.database import AsyncSessionLocal
    from app.services.renderer import render_episode

    async with AsyncSessionLocal() as session:
        ep = await session.get(Episode, episode_id)
        if ep:
            await render_episode(session, ep, template_id)


@router.post("/{episode_id}/publish", response_model=EpisodeOut)
async def trigger_publish(
    episode_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    ep = await session.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(404, "Episode not found")
    if ep.status != "rendered":
        raise HTTPException(400, f"Episode must be rendered first (current: '{ep.status}')")

    background_tasks.add_task(_run_publish, episode_id)
    return ep


async def _run_publish(episode_id: int) -> None:
    from app.database import AsyncSessionLocal
    from app.services.publisher import publish_episode

    async with AsyncSessionLocal() as session:
        ep = await session.get(Episode, episode_id)
        if ep:
            await publish_episode(session, ep)


@router.delete("/{episode_id}", status_code=204)
async def delete_episode(episode_id: int, session: AsyncSession = Depends(get_session)):
    ep = await session.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(404, "Episode not found")

    # Clean up files
    import pathlib
    for path_attr in ("mp3_path", "render_path"):
        p = getattr(ep, path_attr)
        if p and pathlib.Path(p).exists():
            pathlib.Path(p).unlink()

    await session.delete(ep)
    await session.commit()
