from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preferences import AppPreferences

# Available UI fonts — exclude Bebas Neue (all-caps, not suitable for UI text)
UI_FONTS: dict[str, dict] = {
    "cantarell": {
        "label": "Cantarell",
        "css": "'Cantarell', system-ui, -apple-system, sans-serif",
        "file": None,
        "format": None,
    },
    "montserrat": {
        "label": "Montserrat",
        "css": "'Montserrat', system-ui, sans-serif",
        "file": "audiogram/Montserrat-Bold.otf",
        "format": "opentype",
    },
    "lato": {
        "label": "Lato",
        "css": "'Lato', system-ui, sans-serif",
        "file": "audiogram/Lato-Bold.ttf",
        "format": "truetype",
    },
    "ubuntu": {
        "label": "Ubuntu",
        "css": "'Ubuntu', system-ui, sans-serif",
        "file": "audiogram/Ubuntu-Bold.ttf",
        "format": "truetype",
    },
}

_ui_font: str = "cantarell"


async def init_preferences(session: AsyncSession) -> None:
    global _ui_font
    pref = (await session.execute(select(AppPreferences))).scalar_one_or_none()
    if pref is None:
        pref = AppPreferences(id=1, ui_font="cantarell")
        session.add(pref)
        await session.commit()
    _ui_font = pref.ui_font


def get_ui_font() -> str:
    return _ui_font


def set_ui_font(font: str) -> None:
    global _ui_font
    _ui_font = font
