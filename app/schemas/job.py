from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobOut(BaseModel):
    id: int
    episode_id: int
    template_id: int
    status: str
    ffmpeg_cmd: Optional[str]
    ffmpeg_log: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_msg: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class JobList(BaseModel):
    items: list[JobOut]
    total: int
