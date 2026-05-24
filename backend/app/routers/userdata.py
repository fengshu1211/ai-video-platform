"""用户素材上传 + 数据导出"""
import os
import shutil
import zipfile
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.models.database import get_db, User, UserPersona
from app.config import UPLOADS_DIR, OUTPUTS_DIR

router = APIRouter(prefix="/api/userdata", tags=["userdata"])

# 素材自动分类规则
CATEGORY_RULES = {
    "人物": ["人", "脸", "自拍", "本人", "me", "selfie", "portrait", "person", "face"],
    "产品": ["产品", "商品", "板材", "柜", "家具", "product", "goods"],
    "场景": ["工地", "工厂", "店", "办公室", "site", "factory", "office", "shop"],
    "素材": ["背景", "素材", "截图", "壁纸", "background", "material", "wallpaper"],
}


def _classify_material(filename: str) -> str:
    """根据文件名自动分类"""
    lower = filename.lower()
    for cat, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return "未分类"


# ── 上传素材 ──
@router.post("/upload-materials")
async def upload_materials(
    user_id: int = Form(...),
    category: str = Form(""),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """批量上传用户行业素材，自动分类存储"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    user_dir = UPLOADS_DIR / "user_materials" / str(user_id)
    cat = category or _classify_material(files[0].filename if files else "")
    cat_dir = user_dir / cat
    cat_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for file in files:
        if not file.filename:
            continue
        ext = Path(file.filename).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi", ".webm"):
            continue
        file_cat = category or _classify_material(file.filename)
        file_cat_dir = user_dir / file_cat
        file_cat_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{ts}_{file.filename}"
        path = file_cat_dir / safe_name
        content = await file.read()
        path.write_bytes(content)
        saved.append({"filename": safe_name, "category": file_cat, "size": len(content),
                      "path": str(path.relative_to(UPLOADS_DIR))})

    # 自动同步到平台存储
    try:
        from app.services.sync_service import auto_sync_material
        for f in saved:
            auto_sync_material(user_id, f["path"], f["category"])
    except Exception:
        pass

    return {"code": 0, "message": f"已上传 {len(saved)} 个文件", "files": saved}


# ── 导出用户数据 ──
@router.get("/export")
def export_user_data(user_id: int, db: Session = Depends(get_db)):
    """导出用户所有数据为ZIP（素材+视频+人设JSON）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    export_dir = OUTPUTS_DIR / f"export_{user_id}"
    export_dir.mkdir(parents=True, exist_ok=True)

    # 人设数据
    persona = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
    user_data = {
        "phone": user.phone,
        "display_name": user.display_name,
        "created_at": str(user.created_at),
    }
    if persona:
        user_data["persona"] = {
            "industry": persona.industry, "role": persona.role,
            "personality": persona.personality, "hobbies": persona.hobbies,
            "content_style": persona.content_style,
            "target_audience": persona.target_audience,
            "ai_style_template": json.loads(persona.ai_style_template or "{}"),
        }
    (export_dir / "profile.json").write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 用户素材
    user_materials = UPLOADS_DIR / "user_materials" / str(user_id)
    if user_materials.exists():
        shutil.copytree(user_materials, export_dir / "materials", dirs_exist_ok=True)

    # 视频作品
    video_dir = export_dir / "videos"
    video_dir.mkdir(exist_ok=True)
    for video in OUTPUTS_DIR.glob("final_tts_*.mp4"):
        shutil.copy2(video, video_dir / video.name)

    # 打包ZIP
    zip_path = OUTPUTS_DIR / f"export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(export_dir):
            for f in files:
                full = Path(root) / f
                zf.write(full, full.relative_to(export_dir))

    shutil.rmtree(export_dir, ignore_errors=True)
    return {"code": 0, "message": "导出成功", "download_url": f"/uploads/outputs/{zip_path.name}"}


# ── 我的素材列表 ──
@router.get("/materials")
def list_user_materials(user_id: int, category: str = ""):
    user_dir = UPLOADS_DIR / "user_materials" / str(user_id)
    if not user_dir.exists():
        return {"code": 0, "files": [], "categories": []}

    files = []
    categories = set()
    for cat_dir in user_dir.iterdir():
        if cat_dir.is_dir():
            categories.add(cat_dir.name)
            if not category or category == cat_dir.name:
                for f in cat_dir.iterdir():
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov"):
                        files.append({
                            "filename": f.name,
                            "category": cat_dir.name,
                            "url": f"/uploads/user_materials/{user_id}/{cat_dir.name}/{f.name}",
                            "size": f.stat().st_size,
                            "is_video": f.suffix.lower() in (".mp4", ".mov", ".avi", ".webm"),
                        })

    return {"code": 0, "files": sorted(files, key=lambda x: x["filename"], reverse=True),
            "categories": sorted(categories)}


# ── 平台管理：手动触发全量同步 ──
@router.post("/sync-all")
def trigger_sync():
    from app.services.sync_service import sync_all_users
    result = sync_all_users()
    return {"code": 0, "message": "同步完成", "result": result}


# ── 平台管理：查看同步状态 ──
@router.get("/sync-status")
def sync_status():
    from app.services.sync_service import SYNC_ROOT, SYNC_ENABLED
    sync_dir = Path(SYNC_ROOT)
    stats = {"enabled": SYNC_ENABLED, "root": SYNC_ROOT, "exists": sync_dir.exists()}
    if sync_dir.exists():
        for sub in ["materials", "videos"]:
            sub_dir = sync_dir / sub
            if sub_dir.exists():
                count = sum(1 for _ in sub_dir.rglob("*") if _.is_file())
                stats[sub] = count
    return {"code": 0, "stats": stats}
