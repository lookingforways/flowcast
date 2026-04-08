from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.youtube_oauth import is_connected
from app.config import settings
from app.database import get_session
from app.models.episode import Episode
from app.models.job import RenderJob
from app.models.podcast import Podcast
from app.models.template import Template
from app.utils.html_sanitizer import sanitize_html

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["sanitize_html"] = sanitize_html


def _format_secs(secs) -> str:
    """Convierte segundos a M:SS o H:MM:SS."""
    if secs is None:
        return "—"
    secs = int(secs)
    m, s = divmod(secs, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


templates.env.filters["format_secs"] = _format_secs


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
    total_podcasts = (await session.execute(select(func.count(Podcast.id)))).scalar_one()
    recent_jobs = (
        await session.execute(
            select(RenderJob)
            .options(selectinload(RenderJob.episode))
            .order_by(RenderJob.created_at.desc())
            .limit(10)
        )
    ).scalars().all()

    # Conteo de renders por episodio (para badge de re-renders)
    ep_ids = [j.episode_id for j in recent_jobs]
    render_counts: dict[int, int] = {}
    if ep_ids:
        rows = (await session.execute(
            select(RenderJob.episode_id, func.count(RenderJob.id).label("cnt"))
            .where(RenderJob.episode_id.in_(ep_ids))
            .group_by(RenderJob.episode_id)
        )).all()
        render_counts = {row.episode_id: row.cnt for row in rows}

    return templates.TemplateResponse(
        "index.html",
        {
            **_base_ctx(request),
            "total_eps": total_eps,
            "published": published,
            "pending": pending,
            "total_podcasts": total_podcasts,
            "recent_jobs": recent_jobs,
            "render_counts": render_counts,
        },
    )


@router.get("/podcasts", response_class=HTMLResponse)
async def podcasts_page(request: Request, session: AsyncSession = Depends(get_session)):
    podcast_list = (await session.execute(select(Podcast).order_by(Podcast.id))).scalars().all()
    tmpl_list = (await session.execute(select(Template).order_by(Template.is_default.desc()))).scalars().all()
    return templates.TemplateResponse(
        "podcasts.html",
        {**_base_ctx(request), "podcasts": podcast_list, "templates": tmpl_list},
    )


@router.get("/episodes", response_class=HTMLResponse)
async def episodes_page(
    request: Request,
    podcast_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    q = select(Episode).order_by(Episode.pub_date.desc().nullslast(), Episode.created_at.desc())
    if podcast_id:
        q = q.where(Episode.podcast_id == podcast_id)

    episodes = (await session.execute(q)).scalars().all()
    tmpl_list = (await session.execute(select(Template).order_by(Template.is_default.desc()))).scalars().all()
    podcast_list = (await session.execute(select(Podcast).order_by(Podcast.id))).scalars().all()

    current_podcast = None
    if podcast_id:
        current_podcast = await session.get(Podcast, podcast_id)

    return templates.TemplateResponse(
        "episodes.html",
        {
            **_base_ctx(request),
            "episodes": episodes,
            "templates": tmpl_list,
            "podcasts": podcast_list,
            "current_podcast": current_podcast,
        },
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
    podcast = await session.get(Podcast, ep.podcast_id) if ep.podcast_id else None
    return templates.TemplateResponse(
        "episode_detail.html",
        {**_base_ctx(request), "episode": ep, "jobs": jobs, "templates": tmpl_list, "podcast": podcast},
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
            "poll_interval": settings.poll_interval_minutes,
            "auto_publish": settings.flowcast_auto_publish,
            "youtube_privacy": settings.youtube_privacy,
            "yt_status": yt_status,
        },
    )
