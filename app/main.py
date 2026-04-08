"""Flowcast — self-hosted audiogram generator."""
from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
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

# /static/ requires auth except CSS/JS/fonts (needed by login + 2FA before auth).
_PUBLIC_PREFIXES = ("/login", "/2fa", "/logout", "/favicon.ico", "/robots.txt", "/.well-known/", "/static/css/", "/static/js/", "/static/fonts/")

# Max body size for login/2fa forms (2 KB — well above any legitimate use)
_MAX_FORM_BODY = 2048

_404_HTML = (
    "<!doctype html><html lang='es'><head><meta charset='UTF-8'>"
    "<title>404 — Flowcast</title></head><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
    "<h1>404</h1><p>Página no encontrada.</p><a href='/'>Volver al inicio</a></body></html>"
)
_500_HTML = (
    "<!doctype html><html lang='es'><head><meta charset='UTF-8'>"
    "<title>Error — Flowcast</title></head><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
    "<h1>Error</h1><p>Algo salió mal. Intentá de nuevo.</p><a href='/'>Volver al inicio</a></body></html>"
)


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
    version="0.9.6",
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
        return HTMLResponse(_404_HTML, status_code=404)
    return JSONResponse({"detail": "Error"}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    logger.error("Unhandled exception for %s %s", request.method, request.url.path, exc_info=exc)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Error interno"}, status_code=500)
    return HTMLResponse(_500_HTML, status_code=500)


# ── CORS — no cross-origin requests allowed ───────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ── Auth guard (registered first = innermost, called after security headers) ──
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)
    if not is_fully_authenticated(request):
        if path.startswith("/api/"):
            return JSONResponse({"detail": "No autenticado"}, status_code=401)
        if path.startswith("/static/"):
            return Response(status_code=403)
        return RedirectResponse("/login", status_code=302)
    return await call_next(request)


# ── Security headers + nonce (registered last = outermost, wraps everything) ─
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

    # Cache-Control
    path = request.url.path
    if path in ("/login", "/2fa"):
        # Auth pages contain CSRF tokens — never cache
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    elif path.startswith("/static/"):
        # Static assets are content-addressed (versioned via filenames) — safe to cache 1 year
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"style-src 'self' 'nonce-{nonce}'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-src https://www.youtube.com; "
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
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["server"] = ""
    return response


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(proxy.router)
app.include_router(ui.router)
app.include_router(podcasts.router)
app.include_router(episodes.router)
app.include_router(templates.router)
app.include_router(jobs.router)
app.include_router(youtube.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@app.get("/.well-known/security.txt", include_in_schema=False)
async def security_txt():
    from datetime import datetime, timezone
    expires = datetime.now(timezone.utc).replace(year=datetime.now().year + 1).strftime("%Y-%m-%dT00:00:00.000Z")
    content = (
        f"Contact: mailto:support@lookingforways.com\n"
        f"Expires: {expires}\n"
        f"Preferred-Languages: es, en\n"
        f"Canonical: {settings.app_base_url}/.well-known/security.txt\n"
        f"Scope: {settings.app_base_url}\n"
    )
    return PlainTextResponse(content)


@app.get("/health")
@limiter.limit("30/minute")
async def health(request: Request):
    return JSONResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})
