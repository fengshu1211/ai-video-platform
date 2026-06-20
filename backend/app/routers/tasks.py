"""任务状态查询 API"""
import json, random
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, AsyncTask, VideoProject
from app.schemas.task import TaskOut

# ── 素材自动匹配 ──
MATERIAL_INDEX_PATH = Path(r"D:\全屋定制\圣栎美家文件夹\素材索引.json")
_mat_index_cache = None

def _load_material_index():
    global _mat_index_cache
    if _mat_index_cache is None and MATERIAL_INDEX_PATH.exists():
        with open(MATERIAL_INDEX_PATH, "r", encoding="utf-8") as f:
            _mat_index_cache = json.load(f)
    return _mat_index_cache

def _auto_match_materials(template_id: str, count: int = 3) -> list:
    """根据模板ID自动匹配素材，返回相对路径列表"""
    idx = _load_material_index()
    if not idx or "template_mapping" not in idx:
        return []
    # 获取该模板需要哪些标签
    needed_tags = idx["template_mapping"].get(template_id, [])
    if not needed_tags:
        # 没有匹配规则的模板，随机取3个
        all_mats = idx.get("materials", [])
        return _pick_random(all_mats, count)
    # 按标签权重评分
    scored = []
    for m in idx.get("materials", []):
        score = sum(1 for t in m.get("tags", []) if t in needed_tags)
        if score > 0:
            scored.append((score, m))
    scored.sort(key=lambda x: -x[0])
    best = [m for _, m in scored]
    return _pick_random(best, count)

def _pick_random(items, count):
    if not items:
        return []
    chosen = random.sample(items, min(count, len(items)))
    return [f"_auto/{m['name']}" for m in chosen]

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
        AsyncTask.task_type.in_(["video_generation", "quick_video"]),
        AsyncTask.status == "pending_worker",
    ).order_by(AsyncTask.id).limit(5).all()

    result = []
    for t in tasks:
        project = db.query(VideoProject).filter(VideoProject.id == t.ref_id).first()
        if not project:
            continue
        # 读取素材路径（用户没传就自动匹配）
        try:
            materials = json.loads(project.material_paths_json or "[]")
        except Exception:
            materials = []
        if not materials:
            # 自动匹配
            tmpl_id = ""
            if project.script_id:
                from app.models.database import RewrittenScript
                s = db.query(RewrittenScript).filter(RewrittenScript.id == project.script_id).first()
                if s:
                    tmpl_id = s.style or ""
            auto_mats = _auto_match_materials(tmpl_id, count=4)
            if auto_mats:
                materials = auto_mats
                # 存回项目（下次直接读取）
                project.material_paths_json = json.dumps(auto_mats)
                db.commit()

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

        # 获取文案（quick_video从material_paths_json取）
        if t.task_type == "quick_video":
            try:
                params = json.loads(project.material_paths_json or "{}")
            except Exception:
                params = {}
            result[-1]["script_text"] = params.get("script", "")
            result[-1]["quick_params"] = {
                "brand": params.get("brand", False),
                "font_size": params.get("font_size", 68),
            }
        elif project.script_id:
            from app.models.database import RewrittenScript
            script = db.query(RewrittenScript).filter(RewrittenScript.id == project.script_id).first()
            if script:
                result[-1]["script_text"] = script.rewritten_text or script.original_text
                # 根据模板类型确定品牌
                tmpl_id = script.style or ""
                if "panel" in tmpl_id or "factory" in tmpl_id:
                    result[-1]["brand"] = "纬臻木业"
                else:
                    result[-1]["brand"] = "圣栎美家"

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
