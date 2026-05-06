from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preferences import AppPreferences

UI_FONTS: dict[str, dict] = {
    "cantarell": {
        "label": "Cantarell",
        "css": "'Cantarell', system-ui, -apple-system, sans-serif",
    },
    "montserrat": {
        "label": "Montserrat",
        "css": "'Montserrat', system-ui, sans-serif",
    },
    "lato": {
        "label": "Lato",
        "css": "'Lato', system-ui, sans-serif",
    },
    "ubuntu": {
        "label": "Ubuntu",
        "css": "'Ubuntu', system-ui, sans-serif",
    },
}

UI_FONT_SIZES: dict[str, dict] = {
    "S":   {"label": "S",   "px": 14},
    "M":   {"label": "M",   "px": 16},
    "L":   {"label": "L",   "px": 17},
    "XL":  {"label": "XL",  "px": 19},
    "XXL": {"label": "XXL", "px": 21},
}

_ui_font: str = "cantarell"
_ui_font_size: str = "L"


async def init_preferences(session: AsyncSession) -> None:
    global _ui_font, _ui_font_size
    pref = (await session.execute(select(AppPreferences))).scalar_one_or_none()
    if pref is None:
        pref = AppPreferences(id=1, ui_font="cantarell", ui_font_size="L")
        session.add(pref)
        await session.commit()
    _ui_font = pref.ui_font
    _ui_font_size = pref.ui_font_size


def get_ui_font() -> str:
    return _ui_font


def get_ui_font_size() -> str:
    return _ui_font_size


def set_preferences(font: str, size: str) -> None:
    global _ui_font, _ui_font_size
    _ui_font = font
    _ui_font_size = size
