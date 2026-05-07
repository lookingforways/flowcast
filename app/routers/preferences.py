from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.preferences import AppPreferences
from app.services.preferences import set_preferences

router = APIRouter(tags=["preferences"])


class PreferencesUpdate(BaseModel):
    ui_font: Literal["cantarell", "montserrat", "lato", "ubuntu"]
    ui_font_size: Literal["S", "M", "L", "XL", "XXL"]
    ui_font_weight: Literal["normal", "bold"] = "normal"


@router.patch("/api/preferences")
async def update_preferences(body: PreferencesUpdate, session: AsyncSession = Depends(get_session)):
    pref = (await session.execute(select(AppPreferences))).scalar_one_or_none()
    if pref is None:
        pref = AppPreferences(id=1, ui_font=body.ui_font, ui_font_size=body.ui_font_size, ui_font_weight=body.ui_font_weight)
        session.add(pref)
    else:
        pref.ui_font = body.ui_font
        pref.ui_font_size = body.ui_font_size
        pref.ui_font_weight = body.ui_font_weight
    await session.commit()

    set_preferences(body.ui_font, body.ui_font_size, body.ui_font_weight)
    return {"ui_font": body.ui_font, "ui_font_size": body.ui_font_size, "ui_font_weight": body.ui_font_weight}
