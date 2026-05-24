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

    # 追踪记录
    track = AsyncTask(task_type="video_generation", ref_id=project_id, status="pending", progress=0, progress_message="后台生成中...")
    db.add(track)
    db.commit()

    # 子进程执行（传入用户自定义API Key）
    import subprocess as _sp, sys as _sys, os as _os
    backend_dir = Path(__file__).resolve().parent.parent.parent
    env = {**_os.environ,
           "DASHSCOPE_API_KEY": _user_keys.dashscope if hasattr(_user_keys, 'dashscope') else "",
           "SILICONFLOW_API_KEY": _user_keys.siliconflow if hasattr(_user_keys, 'siliconflow') else ""}
    from app.main import _user_keys
    env["DASHSCOPE_API_KEY"] = getattr(_user_keys, 'dashscope', '') or _os.getenv("DASHSCOPE_API_KEY", "")
    env["SILICONFLOW_API_KEY"] = getattr(_user_keys, 'siliconflow', '') or _os.getenv("SILICONFLOW_API_KEY", "")
    proc = _sp.run(
        [_sys.executable, "-u", "-c",
         f"import sys; sys.path.insert(0, r'{backend_dir}'); "
         f"from app.tasks.video_tasks import _run_video_generation; "
         f"print('RESULT:' + str(_run_video_generation({project_id})))"],
        cwd=str(backend_dir),
        capture_output=True, text=True, timeout=600,
        env=env,
    )
    out = (proc.stdout or "")[-300:]
    err = (proc.stderr or "")[-300:]
    return {"code": 0, "message": "视频生成完成",
            "data": {"project_id": project_id, "task_id": track.id,
                     "stdout": out, "stderr": err}}


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
