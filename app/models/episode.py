from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guid: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)

    # Podcast this episode belongs to
    podcast_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("podcasts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Keep feed_url for reference / legacy
    feed_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mp3_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    duration_secs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pub_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Local paths after processing
    mp3_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    render_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # YouTube
    youtube_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # State machine: discovered → downloaded → rendered → published | failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="discovered", index=True)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    podcast: Mapped[Optional["Podcast"]] = relationship("Podcast", foreign_keys=[podcast_id], lazy="selectin")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Episode id={self.id} status={self.status!r} title={self.title!r}>"
