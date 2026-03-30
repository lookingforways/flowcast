"""Login, 2FA, and logout routes."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.auth.session import (
    clear_session,
    get_session,
    is_fully_authenticated,
    is_password_verified,
    set_session,
)
from app.auth.totp import get_qr_code_base64, is_2fa_configured, verify_token
from app.config import settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if is_fully_authenticated(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == settings.admin_username and password == settings.admin_password:
        response = RedirectResponse("/2fa", status_code=302)
        set_session(response, {"authenticated": True, "totp_verified": False})
        return response
    return RedirectResponse("/login?error=Credenciales+incorrectas", status_code=302)


@router.get("/2fa", response_class=HTMLResponse)
async def totp_page(request: Request, error: str = ""):
    if not is_password_verified(request):
        return RedirectResponse("/login", status_code=302)
    if is_fully_authenticated(request):
        return RedirectResponse("/", status_code=302)

    first_time = not is_2fa_configured()
    qr_code = get_qr_code_base64()  # Creates secret if needed

    return templates.TemplateResponse(
        "totp_verify.html",
        {
            "request": request,
            "error": error,
            "first_time": first_time,
            "qr_code": qr_code,
        },
    )


@router.post("/2fa")
async def totp_submit(
    request: Request,
    token: str = Form(...),
):
    if not is_password_verified(request):
        return RedirectResponse("/login", status_code=302)

    if verify_token(token.strip()):
        session = get_session(request)
        response = RedirectResponse("/", status_code=302)
        set_session(response, {"authenticated": True, "totp_verified": True})
        return response

    return RedirectResponse("/2fa?error=Código+incorrecto,+intentá+de+nuevo", status_code=302)


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    clear_session(response)
    return response
