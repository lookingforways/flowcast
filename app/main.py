"""Flowcast — self-hosted audiogram generator."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import episodes, jobs, podcasts, templates, ui, youtube
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.ensure_dirs()
    await init_db()
    await _ensure_default_template()
    start_scheduler()
    logger.info("Flowcast started. Visit %s", settings.app_base_url)
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Flowcast stopped.")


async def _ensure_default_template() -> None:
    """Create a default template if none exists."""
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.template import Template

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Template).limit(1))
        if result.scalar_one_or_none() is None:
            tmpl = Template(name="Default", is_default=True)
            session.add(tmpl)
            await session.commit()
            logger.info("Created default template")


app = FastAPI(
    title="Flowcast",
    description="Self-hosted audiogram generator for podcasts",
    version="0.2.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(ui.router)
app.include_router(podcasts.router)
app.include_router(episodes.router)
app.include_router(templates.router)
app.include_router(jobs.router)
app.include_router(youtube.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
