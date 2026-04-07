from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pathlib import Path

from app.config import settings
from app.database import get_session
from app.models.episode import Episode
from app.schemas.episode import EpisodeList, EpisodeOut
from app.schemas.job import JobOut

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


def _safe_unlink(path_str: str, *allowed_parents: Path) -> None:
    """Delete a file only if it resides within one of the allowed directories."""
    try:
        p = Path(path_str).resolve()
        for parent in allowed_parents:
            if str(p).startswith(str(parent.resolve())):
                p.unlink(missing_ok=True)
                return
    except Exception:
        pass


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
    import logging
    from app.database import AsyncSessionLocal
    from app.services.publisher import publish_episode

    log = logging.getLogger(__name__)
    async with AsyncSessionLocal() as session:
        ep = await session.get(Episode, episode_id)
        if ep:
            try:
                await publish_episode(session, ep)
            except Exception as exc:
                log.error("Publish failed for episode %d: %s", episode_id, exc, exc_info=True)
                ep.status = "failed"
                ep.error_msg = _publish_error_msg(exc)
                await session.commit()


def _publish_error_msg(exc: Exception) -> str:
    """Traducir excepciones de YouTube a mensajes en español para el usuario."""
    msg = str(exc).lower()

    # Token expirado / revocado (modo Testing en Google Cloud expira cada 7 días)
    if "invalid_grant" in msg or "token has been expired or revoked" in msg:
        return (
            "El token de YouTube expiró o fue revocado. "
            "Andá a Configuración → Desconectar YouTube → Conectar con YouTube para renovarlo. "
            "Si el problema se repite cada 7 días, tu app está en modo 'Testing' en Google Cloud Console "
            "— publicala o agregá tu cuenta como usuario de prueba."
        )

    # Sin permisos / cuota
    if "forbidden" in msg or "quotaexceeded" in msg or "403" in msg:
        return (
            "YouTube rechazó la publicación por falta de permisos o cuota agotada. "
            "Verificá los permisos de la app en Google Cloud Console."
        )

    # No autenticado
    if "unauthorized" in msg or "401" in msg or "not connected" in msg:
        return (
            "No hay sesión activa con YouTube. "
            "Andá a Configuración y conectá tu cuenta de YouTube."
        )

    # Archivo no encontrado
    if "no render" in msg or "no such file" in msg or "not found" in msg:
        return "No se encontró el archivo de video para publicar. Intentá renderizar el episodio nuevamente."

    # Error genérico — incluir el mensaje original para que sea útil
    return f"Error al publicar en YouTube: {exc}"


@router.delete("/{episode_id}", status_code=204)
async def delete_episode(episode_id: int, session: AsyncSession = Depends(get_session)):
    ep = await session.get(Episode, episode_id)
    if ep is None:
        raise HTTPException(404, "Episode not found")

    # Clean up files (safe path check to prevent path traversal)
    if ep.mp3_path:
        _safe_unlink(ep.mp3_path, settings.downloads_dir)
    if ep.render_path:
        _safe_unlink(ep.render_path, settings.renders_dir)

    await session.delete(ep)
    await session.commit()
