from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.youtube_oauth import is_connected
from app.config import settings
from app.database import get_session
from app.models.episode import Episode
from app.models.job import RenderJob
from app.models.template import Template

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/templates")


def _base_ctx(request: Request) -> dict:
    return {
        "request": request,
        "youtube_connected": is_connected(),
        "auto_publish": settings.flowcast_auto_publish,
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    total_eps = (await session.execute(select(func.count(Episode.id)))).scalar_one()
    published = (
        await session.execute(select(func.count(Episode.id)).where(Episode.status == "published"))
    ).scalar_one()
    pending = (
        await session.execute(
            select(func.count(Episode.id)).where(Episode.status.in_(["discovered", "downloaded"]))
        )
    ).scalar_one()
    recent_jobs = (
        await session.execute(select(RenderJob).order_by(RenderJob.created_at.desc()).limit(10))
    ).scalars().all()
    recent_episodes = (
        await session.execute(select(Episode).order_by(Episode.created_at.desc()).limit(5))
    ).scalars().all()

    return templates.TemplateResponse(
        "index.html",
        {
            **_base_ctx(request),
            "total_eps": total_eps,
            "published": published,
            "pending": pending,
            "recent_jobs": recent_jobs,
            "recent_episodes": recent_episodes,
        },
    )


@router.get("/episodes", response_class=HTMLResponse)
async def episodes_page(request: Request, session: AsyncSession = Depends(get_session)):
    episodes = (
        await session.execute(
            select(Episode).order_by(Episode.pub_date.desc().nullslast(), Episode.created_at.desc())
        )
    ).scalars().all()
    tmpl_list = (await session.execute(select(Template).order_by(Template.is_default.desc()))).scalars().all()
    return templates.TemplateResponse(
        "episodes.html",
        {**_base_ctx(request), "episodes": episodes, "templates": tmpl_list},
    )


@router.get("/episodes/{episode_id}", response_class=HTMLResponse)
async def episode_detail(episode_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException

    ep = await session.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(404, "Episode not found")
    jobs = (
        await session.execute(
            select(RenderJob)
            .where(RenderJob.episode_id == episode_id)
            .order_by(RenderJob.created_at.desc())
        )
    ).scalars().all()
    tmpl_list = (await session.execute(select(Template).order_by(Template.is_default.desc()))).scalars().all()
    return templates.TemplateResponse(
        "episode_detail.html",
        {**_base_ctx(request), "episode": ep, "jobs": jobs, "templates": tmpl_list},
    )


@router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request, session: AsyncSession = Depends(get_session)):
    tmpl_list = (await session.execute(select(Template).order_by(Template.is_default.desc()))).scalars().all()
    return templates.TemplateResponse(
        "templates.html",
        {**_base_ctx(request), "templates": tmpl_list},
    )


@router.get("/templates/{template_id}/edit", response_class=HTMLResponse)
async def template_editor(template_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    from fastapi import HTTPException

    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")
    return templates.TemplateResponse(
        "template_editor.html",
        {**_base_ctx(request), "template": tmpl},
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    yt_status = {"connected": is_connected()}
    if is_connected():
        try:
            from app.services.publisher import get_channel_info
            yt_status["channel"] = await get_channel_info()
        except Exception:
            yt_status["connected"] = False

    return templates.TemplateResponse(
        "settings.html",
        {
            **_base_ctx(request),
            "rss_feed_url": settings.rss_feed_url,
            "poll_interval": settings.poll_interval_minutes,
            "auto_publish": settings.flowcast_auto_publish,
            "youtube_privacy": settings.youtube_privacy,
            "yt_status": yt_status,
        },
    )
