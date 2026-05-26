"""素材搜索与下载 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.services.material_service import search_videos, download_video
from app.config import UPLOADS_DIR

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("/search")
def search_materials(q: str, per_page: int = 8):
    """搜索Pexels免版权视频素材"""
    try:
        results = search_videos(q, per_page)
        return {"code": 0, "data": results}
    except Exception as e:
        raise HTTPException(500, f"素材搜索失败：{e}")


@router.post("/download")
def download_material(url: str, video_id: int):
    """下载指定素材到本地"""
    try:
        path = download_video(url, video_id)
        return {
            "code": 0,
            "data": {
                "path": str(path.relative_to(path.parent.parent)),
                "filename": path.name,
            },
        }
    except Exception as e:
        raise HTTPException(500, f"素材下载失败：{e}")


@router.get("/presets")
def list_presets():
    """列出预置参考素材（按赛道分类）"""
    presets_dir = UPLOADS_DIR / "presets"
    presets = {}
    if presets_dir.exists():
        for cat_dir in sorted(presets_dir.iterdir()):
            if cat_dir.is_dir():
                files = []
                for f in sorted(cat_dir.glob("*")):
                    if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.mp4', '.mov'):
                        files.append({
                            "name": f.stem,
                            "filename": f.name,
                            "path": f"presets/{cat_dir.name}/{f.name}",
                            "category": cat_dir.name,
                        })
                if files:
                    presets[cat_dir.name] = files
    return {"code": 0, "presets": presets}
