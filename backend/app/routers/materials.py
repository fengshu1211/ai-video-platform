"""素材搜索与下载 API"""
from fastapi import APIRouter, HTTPException
from app.services.material_service import search_videos, download_video

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
