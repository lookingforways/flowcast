from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str
    waveform_color: str = "#00FF88"
    waveform_mode: str = "cline"
    waveform_x: int = 0
    waveform_y: int = 810
    waveform_w: int = 1920
    waveform_h: int = 270
    title_font: str = "liberation"
    title_font_size: int = 64
    title_color: str = "#FFFFFF"
    title_x: str = "(w-text_w)/2"
    title_y: int = 680
    watermark_x: str = "w-overlay_w-40"
    watermark_y: str = "40"
    watermark_scale: int = 200
    show_duration: bool = True


class TemplateUpdate(TemplateCreate):
    name: Optional[str] = None


class TemplateOut(BaseModel):
    id: int
    name: str
    is_default: bool
    background_path: Optional[str]
    waveform_color: str
    waveform_mode: str
    waveform_x: int
    waveform_y: int
    waveform_w: int
    waveform_h: int
    title_font_path: Optional[str]
    title_font: str
    title_font_size: int
    title_color: str
    title_x: str
    title_y: int
    watermark_path: Optional[str]
    watermark_x: str
    watermark_y: str
    watermark_scale: int
    show_duration: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
