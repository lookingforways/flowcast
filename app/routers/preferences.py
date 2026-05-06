from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.preferences import AppPreferences
from app.services.preferences import UI_FONTS, set_ui_font

router = APIRouter(tags=["preferences"])


@router.patch("/api/preferences/ui-font")
async def update_ui_font(request: Request, session: AsyncSession = Depends(get_session)):
    body = await request.json()
    font = body.get("font", "")
    if font not in UI_FONTS:
        raise HTTPException(400, "Fuente no válida")

    pref = (await session.execute(select(AppPreferences))).scalar_one_or_none()
    if pref is None:
        pref = AppPreferences(id=1, ui_font=font)
        session.add(pref)
    else:
        pref.ui_font = font
    await session.commit()

    set_ui_font(font)
    return {"ui_font": font}
