from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EpisodeOut(BaseModel):
    id: int
    guid: str
    title: str
    description: Optional[str]
    mp3_url: str
    duration_secs: Optional[int]
    pub_date: Optional[datetime]
    mp3_path: Optional[str]
    render_path: Optional[str]
    youtube_id: Optional[str]
    status: str
    error_msg: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EpisodeList(BaseModel):
    items: list[EpisodeOut]
    total: int
    page: int
    per_page: int
