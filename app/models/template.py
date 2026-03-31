from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Background image
    background_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Waveform configuration
    waveform_color: Mapped[str] = mapped_column(String(16), default="#00FF88", nullable=False)
    # Waveform mode: cline | p2p | line | point | showfreqs
    waveform_mode: Mapped[str] = mapped_column(String(16), default="cline", nullable=False)
    waveform_x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    waveform_y: Mapped[int] = mapped_column(Integer, default=810, nullable=False)
    waveform_w: Mapped[int] = mapped_column(Integer, default=1920, nullable=False)
    waveform_h: Mapped[int] = mapped_column(Integer, default=270, nullable=False)

    # Title text
    title_font_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    title_font_size: Mapped[int] = mapped_column(Integer, default=64, nullable=False)
    title_color: Mapped[str] = mapped_column(String(16), default="#FFFFFF", nullable=False)
    title_x: Mapped[str] = mapped_column(String(128), default="(w-text_w)/2", nullable=False)
    title_y: Mapped[int] = mapped_column(Integer, default=680, nullable=False)

    # Optional watermark / logo overlay
    watermark_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    watermark_x: Mapped[str] = mapped_column(String(64), default="w-overlay_w-40", nullable=False)
    watermark_y: Mapped[str] = mapped_column(String(64), default="40", nullable=False)
    watermark_scale: Mapped[int] = mapped_column(Integer, default=200, nullable=False)  # px width

    show_duration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} name={self.name!r} default={self.is_default}>"
