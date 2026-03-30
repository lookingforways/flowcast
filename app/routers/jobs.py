from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.job import RenderJob
from app.schemas.job import JobList, JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=JobList)
async def list_jobs(
    status: str | None = Query(None),
    episode_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    q = select(RenderJob).order_by(RenderJob.created_at.desc())
    if status:
        q = q.where(RenderJob.status == status)
    if episode_id:
        q = q.where(RenderJob.episode_id == episode_id)

    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await session.execute(q.limit(limit))).scalars().all()
    return JobList(items=list(items), total=total)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)):
    job = await session.get(RenderJob, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job
