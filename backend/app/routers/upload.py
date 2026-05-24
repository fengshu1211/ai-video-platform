"""文件上传 API"""
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File
from app.config import IMAGES_DIR, AUDIO_DIR, VIDEOS_DIR, VOICES_DIR

router = APIRouter(prefix="/api/upload", tags=["upload"])

# 允许的文件扩展名
ALLOWED_EXT = {
    "images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"},
    "audio": {".mp3", ".wav", ".aac", ".ogg", ".m4a", ".flac"},
    "videos": {".mp4", ".mov", ".avi", ".webm", ".mkv"},
    "voices": {".mp3", ".wav", ".m4a", ".ogg"},
}

TYPE_DIR_MAP = {
    "images": IMAGES_DIR,
    "audio": AUDIO_DIR,
    "videos": VIDEOS_DIR,
    "voices": VOICES_DIR,
}


def get_upload_dir(file_type: str) -> Path:
    return TYPE_DIR_MAP.get(file_type, IMAGES_DIR)


@router.post("/file")
async def upload_file(file: UploadFile = File(...), file_type: str = "images"):
    """通用文件上传，file_type: images / audio / videos / voices"""
    if file_type not in TYPE_DIR_MAP:
        return {"code": 1, "message": f"不支持的文件类型：{file_type}"}

    ext = Path(file.filename).suffix.lower()
    allowed = ALLOWED_EXT.get(file_type, set())
    if ext not in allowed:
        return {"code": 1, "message": f"不支持的文件格式：{ext}，允许：{allowed}"}

    upload_dir = get_upload_dir(file_type)
    new_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / new_name

    content = await file.read()
    file_path.write_bytes(content)

    return {
        "code": 0,
        "message": "上传成功",
        "data": {
            "filename": file.filename,
            "saved_name": new_name,
            "path": str(file_path.relative_to(upload_dir.parent)),
            "size": len(content),
        },
    }


@router.post("/bgm")
async def upload_bgm(file: UploadFile = File(...)):
    """上传BGM，等同于音频上传"""
    return await upload_file(file, file_type="audio")


@router.delete("/files")
def delete_file(path: str):
    """删除已上传的素材文件"""
    from app.config import UPLOADS_DIR
    file_path = UPLOADS_DIR / path
    if file_path.exists() and file_path.is_file():
        file_path.unlink()
        return {"code": 0, "message": "已删除"}
    return {"code": 1, "message": "文件不存在"}


@router.get("/files")
def list_uploaded_files():
    """列出已上传的素材文件"""
    files = []
    for ftype, d in [("images", IMAGES_DIR), ("videos", VIDEOS_DIR)]:
        if d.exists():
            for f in sorted(d.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file() and f.suffix.lower() in ('.jpg','.jpeg','.png','.gif','.webp','.bmp','.mp4','.mov','.avi','.webm','.mkv'):
                    files.append({
                        "name": f.name,
                        "path": f"{ftype}/{f.name}",
                        "type": "image" if f.suffix.lower() in ('.jpg','.jpeg','.png','.gif','.webp','.bmp') else "video",
                        "size": f.stat().st_size,
                    })
    return {"code": 0, "data": files[:60]}


@router.post("/materials")
async def upload_materials(files: list[UploadFile] = File(...)):
    """批量上传视频素材"""
    results = []
    for f in files:
        result = await upload_file(f, file_type="videos")
        results.append(result)
    return {"code": 0, "message": f"批量上传完成：{len(results)}个文件", "data": results}
