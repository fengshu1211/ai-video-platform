"""选题/赛道相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TrackCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TrackOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HotTopicOut(BaseModel):
    id: int
    track_id: int
    platform: Optional[str] = None
    title: str
    source_url: Optional[str] = None
    metrics_json: str
    ai_analysis: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
