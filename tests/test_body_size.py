"""Tests for body-size and chunked transfer-encoding guards (B-03)."""
import asyncio

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_MAX_FORM_BODY = 2048


def _make_app():
    """Minimal app replicating the body-guard logic from security_middleware."""
    app = FastAPI()

    @app.middleware("http")
    async def body_guard(request: Request, call_next):
        if request.method == "POST" and request.url.path in ("/login", "/2fa"):
            if "chunked" in request.headers.get("transfer-encoding", "").lower():
                return JSONResponse({"detail": "Solicitud inválida"}, status_code=400)
            if int(request.headers.get("content-length", 0)) > _MAX_FORM_BODY:
                return JSONResponse({"detail": "Solicitud inválida"}, status_code=400)
        if request.method == "PATCH" and request.url.path == "/api/preferences":
            if "chunked" in request.headers.get("transfer-encoding", "").lower():
                return JSONResponse({"detail": "Solicitud inválida"}, status_code=400)
            if int(request.headers.get("content-length", 0)) > _MAX_FORM_BODY:
                return JSONResponse({"detail": "Solicitud inválida"}, status_code=400)
        return await call_next(request)

    @app.post("/login")
    async def _login(): return JSONResponse({"ok": True})

    @app.post("/2fa")
    async def _twofa(): return JSONResponse({"ok": True})

    @app.patch("/api/preferences")
    async def _prefs(): return JSONResponse({"ok": True})

    return app


async def _call(app, method: str, path: str, headers: dict) -> int:
    """Drive an ASGI app directly and return the HTTP status code."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "server": ("testserver", 80),
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    received: list = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(event):
        received.append(event)

    await app(scope, receive, send)
    return next(e["status"] for e in received if e["type"] == "http.response.start")


_app = _make_app()


def _run(coro):
    return asyncio.run(coro)


def test_chunked_login_rejected():
    assert _run(_call(_app, "POST", "/login", {"transfer-encoding": "chunked"})) == 400


def test_chunked_2fa_rejected():
    assert _run(_call(_app, "POST", "/2fa", {"transfer-encoding": "chunked"})) == 400


def test_chunked_preferences_rejected():
    assert _run(_call(_app, "PATCH", "/api/preferences", {"transfer-encoding": "chunked"})) == 400


def test_normal_login_allowed():
    assert _run(_call(_app, "POST", "/login", {"content-length": "20"})) == 200


def test_oversized_login_rejected():
    assert _run(_call(_app, "POST", "/login", {"content-length": str(_MAX_FORM_BODY + 1)})) == 400
