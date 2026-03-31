from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _validate_feed_url(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    from urllib.parse import urlparse
    parsed = urlparse(v)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("feed_url must use http or https scheme")
    if not parsed.netloc:
        raise ValueError("feed_url must include a valid hostname")
    return v


class PodcastCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    feed_url: str
    description: Optional[str] = Field(None, max_length=2000)
    youtube_playlist_id: Optional[str] = Field(None, max_length=64)
    default_template_id: Optional[int] = None
    is_active: bool = True

    @field_validator("feed_url")
    @classmethod
    def validate_feed_url(cls, v: str) -> str:
        return _validate_feed_url(v)  # type: ignore[return-value]


class PodcastUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    feed_url: Optional[str] = None
    description: Optional[str] = Field(None, max_length=2000)
    youtube_playlist_id: Optional[str] = Field(None, max_length=64)

    @field_validator("feed_url")
    @classmethod
    def validate_feed_url(cls, v: Optional[str]) -> Optional[str]:
        return _validate_feed_url(v)
    default_template_id: Optional[int] = None
    is_active: Optional[bool] = None


class PodcastOut(BaseModel):
    id: int
    name: str
    feed_url: str
    description: Optional[str]
    youtube_playlist_id: Optional[str]
    default_template_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
