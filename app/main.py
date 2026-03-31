"""Flowcast — self-hosted audiogram generator."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth.limiter import limiter
from app.auth.session import is_fully_authenticated
from app.config import settings
from app.database import init_db
from app.routers import auth, episodes, jobs, podcasts, templates, ui, youtube
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_PUBLIC_PREFIXES = ("/login", "/2fa", "/logout", "/static", "/health")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.validate_secrets()
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
    version="0.5.2",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Explicit CORS — no cross-origin requests allowed
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)
    if not is_fully_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    return await call_next(request)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(ui.router)
app.include_router(podcasts.router)
app.include_router(episodes.router)
app.include_router(templates.router)
app.include_router(jobs.router)
app.include_router(youtube.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
