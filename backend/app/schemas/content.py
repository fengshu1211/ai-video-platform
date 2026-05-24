"""内容改写相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RewriteRequest(BaseModel):
    original_text: str
    style: str = "similar"  # similar / original / aggressive
    topic_id: Optional[int] = None
    source_url: Optional[str] = None
    target_word_count: Optional[int] = None


class ScrapeRequest(BaseModel):
    url: str
    platform: str  # douyin / kuaishou / xiaohongshu


class ScriptOut(BaseModel):
    id: int
    topic_id: Optional[int] = None
    original_text: str
    rewritten_text: str
    rewrite_prompt: Optional[str] = None
    style: str
    word_count: int
    is_approved: int
    source_type: str
    source_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScriptUpdate(BaseModel):
    rewritten_text: Optional[str] = None
    is_approved: Optional[int] = None
