from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.preferences import AppPreferences
from app.services.preferences import UI_FONTS, UI_FONT_SIZES, set_preferences

router = APIRouter(tags=["preferences"])


@router.patch("/api/preferences")
async def update_preferences(request: Request, session: AsyncSession = Depends(get_session)):
    body = await request.json()
    font = body.get("ui_font", "")
    size = body.get("ui_font_size", "")
    if font not in UI_FONTS:
        raise HTTPException(400, "Fuente no válida")
    if size not in UI_FONT_SIZES:
        raise HTTPException(400, "Tamaño no válido")

    pref = (await session.execute(select(AppPreferences))).scalar_one_or_none()
    if pref is None:
        pref = AppPreferences(id=1, ui_font=font, ui_font_size=size)
        session.add(pref)
    else:
        pref.ui_font = font
        pref.ui_font_size = size
    await session.commit()

    set_preferences(font, size)
    return {"ui_font": font, "ui_font_size": size}
