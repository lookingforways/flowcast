"""Flowcast — self-hosted audiogram generator."""
from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.limiter import limiter
from app.auth.session import is_fully_authenticated
from app.config import settings
from app.database import init_db
from app.routers import auth, episodes, jobs, podcasts, proxy, templates, ui, youtube
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_PUBLIC_PREFIXES = ("/login", "/2fa", "/logout", "/static", "/health", "/favicon.ico")

# SHA-384 hash of Bootstrap 5.3.3 bundle (allows it in script-src without CDN whitelist)
_BOOTSTRAP_JS_HASH = "sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"

# Max body size for login/2fa forms (2 KB — well above any legitimate use)
_MAX_FORM_BODY = 2048


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
    version="0.6.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        {"detail": "Demasiados intentos. Reintentá en un momento."},
        status_code=429,
        headers={"Retry-After": "60"},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse({"detail": "Solicitud inválida"}, status_code=400)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Error"}, status_code=exc.status_code)
    if exc.status_code == 404:
        return RedirectResponse("/", status_code=302)
    return JSONResponse({"detail": "Error"}, status_code=exc.status_code)


# ── CORS — no cross-origin requests allowed ───────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ── Security headers + nonce (outermost middleware) ───────────────────────────
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Generate a fresh nonce for every request
    nonce = secrets.token_hex(16)
    request.state.csp_nonce = nonce

    # Block oversized bodies on auth form endpoints before FastAPI reads them
    if request.method == "POST" and request.url.path in ("/login", "/2fa"):
        content_length = int(request.headers.get("content-length", 0))
        if content_length > _MAX_FORM_BODY:
            return JSONResponse({"detail": "Solicitud inválida"}, status_code=400)

    response = await call_next(request)

    # Cache-Control: prevent caching of auth pages (may contain CSRF tokens)
    if request.url.path in ("/login", "/2fa"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' '{_BOOTSTRAP_JS_HASH}'; "
        f"style-src 'self' 'unsafe-inline' 'nonce-{nonce}' cdn.jsdelivr.net; "
        "font-src cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "upgrade-insecure-requests"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["server"] = ""
    return response


# ── Auth guard ────────────────────────────────────────────────────────────────
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
app.include_router(proxy.router)
app.include_router(ui.router)
app.include_router(podcasts.router)
app.include_router(episodes.router)
app.include_router(templates.router)
app.include_router(jobs.router)
app.include_router(youtube.router)


@app.get("/health")
@limiter.limit("30/minute")
async def health(request: Request):
    return {"status": "ok"}
