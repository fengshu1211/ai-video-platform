"""语音系统相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VoiceProfileOut(BaseModel):
    id: int
    name: str
    provider: str
    voice_id: str
    gender: Optional[str] = None
    style: Optional[str] = None
    sample_url: Optional[str] = None
    is_custom: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TTSRequest(BaseModel):
    text: str
    voice_id: int
