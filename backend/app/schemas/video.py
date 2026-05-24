"""视频项目相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VideoProjectCreate(BaseModel):
    title: str
    script_id: Optional[int] = None
    voice_id: Optional[int] = None
    bgm_path: Optional[str] = None
    bgm_volume: float = 0.3
    material_paths_json: str = "[]"
    aspect_ratio: str = "9:16"
    subtitle_enabled: int = 1
    lip_sync_enabled: int = 0
    lip_sync_mode: str = "pip"
    image_animation_type: Optional[str] = None
    subtitle_animation: str = "fade"
    collected: int = 0


class VideoProjectUpdate(BaseModel):
    title: Optional[str] = None
    bgm_path: Optional[str] = None
    bgm_volume: Optional[float] = None
    material_paths_json: Optional[str] = None
    subtitle_enabled: Optional[int] = None
    lip_sync_enabled: Optional[int] = None
    lip_sync_mode: Optional[str] = None
    image_animation_type: Optional[str] = None
    subtitle_animation: str = "fade"
    collected: int = 0


class VideoProjectOut(BaseModel):
    id: int
    title: str
    script_id: Optional[int] = None
    voice_id: Optional[int] = None
    bgm_path: Optional[str] = None
    bgm_volume: float
    material_paths_json: str
    subtitle_enabled: int
    lip_sync_enabled: int = 0
    lip_sync_mode: str = "pip"
    image_animation_type: Optional[str] = None
    subtitle_animation: str = "fade"
    collected: int = 0
    aspect_ratio: str = "9:16"
    status: str
    output_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
