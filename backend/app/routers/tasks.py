"""任务状态查询 API"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, AsyncTask, VideoProject
from app.schemas.task import TaskOut

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class TaskDoneReq(BaseModel):
    status: str = "completed"
    progress: int = 100
    progress_message: str = ""
    result_json: str = "{}"


@router.get("/")
def list_tasks(ref_type: str | None = None, ref_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(AsyncTask)
    if ref_type:
        q = q.filter(AsyncTask.task_type == ref_type)
    if ref_id:
        q = q.filter(AsyncTask.ref_id == ref_id)
    return q.order_by(AsyncTask.created_at.desc()).limit(20).all()


@router.get("/pending_worker")
def get_pending_worker_tasks(db: Session = Depends(get_db)):
    """返回等待本地渲染Worker处理的任务"""
    tasks = db.query(AsyncTask).filter(
        AsyncTask.task_type == "video_generation",
        AsyncTask.status == "pending_worker",
    ).order_by(AsyncTask.id).limit(5).all()

    result = []
    for t in tasks:
        project = db.query(VideoProject).filter(VideoProject.id == t.ref_id).first()
        if not project:
            continue
        # 读取素材路径
        try:
            materials = json.loads(project.material_paths_json or "[]")
        except Exception:
            materials = []

        result.append({
            "task_id": t.id,
            "project_id": project.id,
            "title": project.title,
            "script_text": "",
            "voice_id": "",
            "materials": materials,
            "aspect_ratio": project.aspect_ratio or "9:16",
            "subtitle_enabled": bool(project.subtitle_enabled),
            "image_animation_type": project.image_animation_type,
            "bgm_volume": project.bgm_volume or 0.3,
        })

        # 获取文案
        if project.script_id:
            from app.models.database import RewrittenScript
            script = db.query(RewrittenScript).filter(RewrittenScript.id == project.script_id).first()
            if script:
                result[-1]["script_text"] = script.rewritten_text or script.original_text

        # 获取语音ID
        if project.voice_id:
            from app.models.database import VoiceProfile
            voice = db.query(VoiceProfile).filter(VoiceProfile.id == project.voice_id).first()
            if voice:
                result[-1]["voice_id"] = voice.voice_id

    return {"count": len(result), "tasks": result}


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.post("/{task_id}/done")
def mark_task_done(task_id: int, req: TaskDoneReq, db: Session = Depends(get_db)):
    task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    task.status = req.status
    task.progress = req.progress
    task.progress_message = req.progress_message
    if req.result_json:
        task.result_json = req.result_json

    # 同步更新项目状态
    project = db.query(VideoProject).filter(VideoProject.id == task.ref_id).first()
    if project:
        if req.status == "completed":
            project.status = "completed"
            try:
                result = json.loads(req.result_json)
                if result.get("output_path"):
                    project.output_path = result["output_path"]
            except Exception:
                pass
        elif req.status == "failed":
            project.status = "failed"

    db.commit()
    return {"code": 0, "message": "updated"}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status in ("pending", "processing"):
        task.status = "failed"
        task.error_message = "用户取消"
        db.commit()
    return {"code": 0, "message": "任务已取消"}
