"""Render service: orchestrates download → FFmpeg → status updates."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ffmpeg.pipeline import run_pipeline
from app.models.episode import Episode
from app.models.job import RenderJob
from app.models.template import Template

logger = logging.getLogger(__name__)

_SAFE_RE = re.compile(r"[^\w\-]")


def _output_filename(episode: Episode) -> str:
    safe = _SAFE_RE.sub("_", episode.guid)[:180]
    return f"{safe}.mp4"


async def get_default_template(session: AsyncSession) -> Template:
    result = await session.execute(select(Template).where(Template.is_default == True))  # noqa: E712
    tmpl = result.scalar_one_or_none()
    if tmpl is None:
        # Fall back to first available template
        result = await session.execute(select(Template).limit(1))
        tmpl = result.scalar_one_or_none()
    if tmpl is None:
        raise RuntimeError("No templates found. Create a template first.")
    return tmpl


async def render_episode(
    session: AsyncSession,
    episode: Episode,
    template_id: int | None = None,
) -> RenderJob:
    """Render an episode to MP4. Returns the RenderJob record."""

    if episode.status not in ("downloaded", "rendered", "failed"):
        raise ValueError(f"Episode {episode.id} is in status '{episode.status}', cannot render.")

    if not episode.mp3_path or not Path(episode.mp3_path).exists():
        raise ValueError(f"Episode {episode.id} has no downloaded MP3 at {episode.mp3_path!r}")

    # Resolve template
    if template_id:
        tmpl = await session.get(Template, template_id)
        if tmpl is None:
            raise ValueError(f"Template {template_id} not found")
    else:
        tmpl = await get_default_template(session)

    # Create render job
    job = RenderJob(
        episode_id=episode.id,
        template_id=tmpl.id,
        status="queued",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    output_dir = settings.renders_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / _output_filename(episode))

    job.status = "running"
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()

    try:
        cmd, ffmpeg_log = await run_pipeline(
            mp3_path=episode.mp3_path,
            output_path=output_path,
            template=tmpl,
            title=episode.title,
            duration_secs=episode.duration_secs,
        )
        job.ffmpeg_cmd = " ".join(cmd)
        job.ffmpeg_log = ffmpeg_log[-4000:]  # Keep last 4KB of log
        job.status = "done"
        job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)

        episode.render_path = output_path
        episode.status = "rendered"
        episode.error_msg = None

    except Exception as exc:
        logger.error("Render failed for episode %d: %s", episode.id, exc)
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        job.error_msg = "Render failed. Check server logs."

        episode.status = "failed"
        episode.error_msg = "Render failed. Check server logs."

    await session.commit()
    await session.refresh(job)
    return job
