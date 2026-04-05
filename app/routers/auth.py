"""Login, 2FA, and logout routes."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.limiter import limiter
from app.auth.session import (
    FLASH_COOKIE,
    clear_session,
    get_session,
    is_fully_authenticated,
    is_password_verified,
    read_flash,
    set_flash,
    set_session,
)
from app.auth.totp import get_qr_code_base64, is_2fa_configured, verify_token
from app.config import settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

_MAX_USERNAME = 150
_MAX_PASSWORD = 256


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_fully_authenticated(request):
        return RedirectResponse("/", status_code=302)
    flash = read_flash(request)
    response = templates.TemplateResponse("login.html", {"request": request, "error": flash})
    if flash:
        response.delete_cookie(FLASH_COOKIE)
    return response


@router.post("/login")
@limiter.limit("5/minute")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    valid = (
        len(username) <= _MAX_USERNAME
        and len(password) <= _MAX_PASSWORD
        and username == settings.admin_username
        and password == settings.admin_password
    )
    if valid:
        response = RedirectResponse("/2fa", status_code=302)
        set_session(response, {"authenticated": True, "totp_verified": False})
        return response

    response = RedirectResponse("/login", status_code=302)
    set_flash(response, "Credenciales incorrectas")
    return response


@router.get("/2fa", response_class=HTMLResponse)
async def totp_page(request: Request):
    if not is_password_verified(request):
        return RedirectResponse("/login", status_code=302)
    if is_fully_authenticated(request):
        return RedirectResponse("/", status_code=302)

    first_time = not is_2fa_configured()
    qr_code = get_qr_code_base64()  # Creates secret if needed
    flash = read_flash(request)

    response = templates.TemplateResponse(
        "totp_verify.html",
        {
            "request": request,
            "error": flash,
            "first_time": first_time,
            "qr_code": qr_code,
        },
    )
    if flash:
        response.delete_cookie(FLASH_COOKIE)
    return response


@router.post("/2fa")
async def totp_submit(
    request: Request,
    token: str = Form(...),
):
    if not is_password_verified(request):
        return RedirectResponse("/login", status_code=302)

    if verify_token(token.strip()):
        response = RedirectResponse("/", status_code=302)
        set_session(response, {"authenticated": True, "totp_verified": True})
        return response

    response = RedirectResponse("/2fa", status_code=302)
    set_flash(response, "Código incorrecto, intentá de nuevo")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    clear_session(response)
    return response
