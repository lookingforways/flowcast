from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PodcastCreate(BaseModel):
    name: str
    feed_url: str
    description: Optional[str] = None
    youtube_playlist_id: Optional[str] = None
    default_template_id: Optional[int] = None
    is_active: bool = True


class PodcastUpdate(BaseModel):
    name: Optional[str] = None
    feed_url: Optional[str] = None
    description: Optional[str] = None
    youtube_playlist_id: Optional[str] = None
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
