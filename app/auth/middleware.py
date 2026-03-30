"""Authentication middleware — redirects unauthenticated requests to /login."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.session import is_fully_authenticated

# Routes that don't require authentication
_PUBLIC_PREFIXES = ("/login", "/2fa", "/logout", "/static", "/health")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public routes through
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # Check authentication
        if not is_fully_authenticated(request):
            return RedirectResponse(f"/login", status_code=302)

        return await call_next(request)
