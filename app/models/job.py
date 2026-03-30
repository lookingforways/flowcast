from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(Integer, ForeignKey("episodes.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("templates.id"), nullable=False)

    # queued | running | done | failed
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)

    ffmpeg_cmd: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ffmpeg_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    episode: Mapped["Episode"] = relationship("Episode", foreign_keys=[episode_id])  # type: ignore[name-defined]
    template: Mapped["Template"] = relationship("Template", foreign_keys=[template_id])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<RenderJob id={self.id} episode_id={self.episode_id} status={self.status!r}>"
