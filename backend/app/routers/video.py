"""视频项目 API"""
import threading
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.models.database import get_db, VideoProject, AsyncTask
from app.schemas.video import VideoProjectCreate, VideoProjectUpdate, VideoProjectOut
from app.config import OUTPUTS_DIR

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/projects", response_model=VideoProjectOut)
def create_project(data: VideoProjectCreate, db: Session = Depends(get_db)):
    project = VideoProject(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[VideoProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(VideoProject).order_by(VideoProject.created_at.desc()).all()


@router.get("/projects/{project_id}", response_model=VideoProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(404, "视频项目不存在")
    return project


@router.patch("/projects/{project_id}", response_model=VideoProjectOut)
def update_project(project_id: int, data: VideoProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(404, "视频项目不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(project, key, val)
    db.commit()
    db.refresh(project)
    return project


@router.post("/projects/{project_id}/generate")
def generate_video(project_id: int, db: Session = Depends(get_db)):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(404, "视频项目不存在")
    if not project.script_id:
        raise HTTPException(400, "请先选择文案")

    # 检查 FFmpeg
    from app.utils.ffmpeg_utils import check_ffmpeg
    if not check_ffmpeg():
        return {
            "code": 1,
            "message": "FFmpeg 未安装，请先安装 FFmpeg。Windows: winget install ffmpeg",
            "data": {"project_id": project_id, "task_id": None},
        }

    # 检查是否已有进行中的任务
    existing = db.query(AsyncTask).filter(
        AsyncTask.ref_id == project_id,
        AsyncTask.task_type == "video_generation",
        AsyncTask.status.in_(["pending", "processing", "pending_worker"]),
    ).first()
    if existing:
        return {"code": 0, "message": "任务已在后台生成中", "data": {"project_id": project_id, "task_id": existing.id}}

    # 追踪记录
    track = AsyncTask(task_type="video_generation", ref_id=project_id, status="pending", progress=0, progress_message="正在准备素材...")
    db.add(track)
    db.commit()
    db.refresh(track)
    task_id = track.id
    db.close()

    # 服务器先做TTS（轻活，几秒钟）
    from app.tasks.video_tasks import _prepare_and_delegate
    threading.Thread(target=_prepare_and_delegate, args=(project_id, task_id), daemon=True).start()

    return {"code": 0, "message": "任务已提交",
            "data": {"project_id": project_id, "task_id": task_id}}


@router.get("/projects/{project_id}/output")
def download_output(project_id: int, db: Session = Depends(get_db)):
    """下载/播放生成的视频"""
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project or not project.output_path:
        raise HTTPException(404, "视频文件不存在")
    file_path = OUTPUTS_DIR.parent / project.output_path
    if not file_path.exists():
        raise HTTPException(404, "视频文件已被删除")
    return FileResponse(file_path, media_type="video/mp4")


@router.post("/projects/{project_id}/collect")
def toggle_collect(project_id: int, db: Session = Depends(get_db)):
    """收藏/取消收藏成品视频"""
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(404, "视频项目不存在")
    project.collected = 1 if project.collected == 0 else 0
    db.commit()
    return {"code": 0, "collected": project.collected, "message": "已收藏" if project.collected else "已取消收藏"}


@router.get("/library", response_model=list[VideoProjectOut])
def list_library(db: Session = Depends(get_db)):
    """成品视频库"""
    return db.query(VideoProject).filter(
        VideoProject.status == "completed",
        VideoProject.collected == 1,
    ).order_by(VideoProject.created_at.desc()).all()


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(404, "视频项目不存在")
    db.delete(project)
    db.commit()
    return {"code": 0, "message": "已删除"}
