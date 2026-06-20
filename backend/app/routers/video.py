"""视频项目 API"""
import json, threading
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, VideoProject, AsyncTask
from app.schemas.video import VideoProjectCreate, VideoProjectUpdate, VideoProjectOut
from app.config import OUTPUTS_DIR

router = APIRouter(prefix="/api/video", tags=["video"])


class QuickGenerateReq(BaseModel):
    script: str
    material_ids: list[str] = []
    brand: bool = False
    font_size: int = 68


@router.post("/quick-generate")
def quick_generate(data: QuickGenerateReq, db: Session = Depends(get_db)):
    """快速出片：脚本+素材 → 创建项目+任务，Worker轮询处理"""
    project = VideoProject(
        title=f"快速出片_{data.script[:20]}",
        script_id=0,
        material_paths_json=json.dumps({
            "script": data.script, "material_ids": data.material_ids,
            "brand": data.brand, "font_size": data.font_size,
        }, ensure_ascii=False),
        status="draft",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    task = AsyncTask(
        task_type="quick_video", ref_id=project.id,
        status="pending_worker", progress=0, progress_message="等待本地渲染...",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {"project_id": project.id, "task_id": task.id, "status": "pending_worker"}


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


# ============= BGM / 模板 / 风格 信息 =============

@router.get("/bgms")
def list_bgms():
    """返回可用BGM列表"""
    return {
        "emotional-piano": {"mood": "温馨", "desc": "情感钢琴，温馨经典"},
        "bright-corporate": {"mood": "轻快", "desc": "明亮企业故事"},
        "inspiring-corporate": {"mood": "励志", "desc": "励志管弦乐"},
        "calm-piano": {"mood": "平静", "desc": "平静钢琴曲"},
        "soft-instrumental": {"mood": "柔和", "desc": "柔和器乐"},
        "piano-classical": {"mood": "古典", "desc": "古典钢琴"},
        "upbeat-corporate": {"mood": "积极", "desc": "欢快企业音乐"},
    }

# ============= HyperFrames 渲染接口 =============

class HyperFramesReq(BaseModel):
    video_path: str = ""
    template: str = "product-showcase"
    bgm: str = "emotional-piano"
    style: str = ""
    script: str = ""

@router.post("/hyperframes-generate")
def hyperframes_generate(data: HyperFramesReq, db: Session = Depends(get_db)):
    """调用 HyperFrames 新渲染管线"""
    import subprocess, os, sys, uuid
    from app.config import OUTPUTS_DIR

    project = VideoProject(
        title=f"HF_{data.script[:15] if data.script else '快速出片'}",
        script_id=0,
        material_paths_json=json.dumps(data.model_dump(), ensure_ascii=False),
        status="processing",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    task = AsyncTask(
        task_type="hyperframes", ref_id=project.id,
        status="processing", progress=0, progress_message="渲染中...",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    def _run():
        script_path = Path(__file__).resolve().parent.parent.parent.parent / "make_hf_subtitle.py"
        env = os.environ.copy()
        if data.video_path:
            env["HF_VIDEO"] = data.video_path
        env["HF_TEMPLATE"] = data.template
        env["HF_BGM"] = data.bgm
        if data.style:
            env["HF_STYLE"] = data.style

        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                capture_output=True, text=True, timeout=600,
                env=env,
            )
            out_dir = Path(r"D:\全屋定制\圣栎美家文件夹\测试输出")
            outs = sorted(out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if outs:
                import shutil
                dest = OUTPUTS_DIR / f"hf_{project.id}.mp4"
                shutil.copy2(str(outs[0]), str(dest))
                task.status = "completed"
                task.progress = 100
                task.progress_message = "渲染完成"
                project.status = "completed"
                project.output_path = str(dest)
            else:
                task.status = "failed"
                task.progress_message = "未找到输出文件"
                project.status = "failed"
        except Exception as e:
            task.status = "failed"
            task.progress_message = str(e)[:200]
            project.status = "failed"

        from app.models.database import SessionLocal
        _db = SessionLocal()
        _db.add_all([task, project])
        _db.commit()
        _db.close()

    threading.Thread(target=_run, daemon=True).start()
    return {"project_id": project.id, "task_id": task.id, "status": "processing"}
