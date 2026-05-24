"""异步任务相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TaskOut(BaseModel):
    id: int
    task_type: str
    ref_id: Optional[int] = None
    celery_task_id: Optional[str] = None
    status: str
    progress: int
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    result_json: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
