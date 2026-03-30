from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Podcast(Base):
    __tablename__ = "podcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    feed_url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # YouTube playlist ID (e.g. PLxxxxx) — optional, videos go to channel root if null
    youtube_playlist_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Default template for this podcast's audiograms
    default_template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    default_template: Mapped[Optional["Template"]] = relationship(  # type: ignore[name-defined]
        "Template", foreign_keys=[default_template_id]
    )

    def __repr__(self) -> str:
        return f"<Podcast id={self.id} name={self.name!r}>"
