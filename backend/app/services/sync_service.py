"""平台数据自动同步——用户素材+视频定期同步到指定存储位置（含质量过滤）"""
import os
import shutil
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from app.config import UPLOADS_DIR, OUTPUTS_DIR, BASE_DIR

# 质量门槛
MIN_IMG_WIDTH = 720           # 图片最小宽度
MIN_IMG_HEIGHT = 720          # 图片最小高度
MIN_IMG_KB = 30               # 图片最小30KB
MIN_VIDEO_WIDTH = 720         # 视频最小宽度
MIN_VIDEO_HEIGHT = 720        # 视频最小高度
MIN_VIDEO_MB = 1              # 视频最小1MB
BLUR_THRESHOLD = 15           # 模糊度阈值（方差<此值判定为模糊）

# 同步目标：本地文件夹 或 网盘映射路径（修改 SYNC_ROOT 即可）
SYNC_ROOT = os.getenv("SYNC_ROOT", str(BASE_DIR / "sync_storage"))
SYNC_ENABLED = os.getenv("SYNC_ENABLED", "1") == "1"


def sync_all_users():
    """全量同步：所有用户素材+视频+信息"""
    if not SYNC_ENABLED:
        return {"status": "disabled"}

    sync_dir = Path(SYNC_ROOT)
    sync_dir.mkdir(parents=True, exist_ok=True)

    result = {"users": 0, "materials": 0, "videos": 0, "errors": []}

    try:
        # 用户信息汇总
        db = sqlite3.connect(str(BASE_DIR / "data.db"))
        users = db.execute("SELECT id, phone, display_name, created_at FROM users").fetchall()
        user_list = []
        for u in users:
            user_list.append({"id": u[0], "phone": u[1], "name": u[2], "created_at": u[3]})
        (sync_dir / "users.json").write_text(json.dumps(user_list, ensure_ascii=False, indent=2), encoding="utf-8")
        result["users"] = len(user_list)

        # 用户人设数据
        personas = db.execute("SELECT user_id, industry, role, personality, hobbies, content_style, target_audience, ai_style_template FROM user_personas").fetchall()
        persona_list = []
        for p in personas:
            persona_list.append({"user_id": p[0], "industry": p[1], "role": p[2],
                                "personality": p[3], "hobbies": p[4],
                                "content_style": p[5], "target_audience": p[6]})
        (sync_dir / "personas.json").write_text(json.dumps(persona_list, ensure_ascii=False, indent=2), encoding="utf-8")
        db.close()
    except Exception as e:
        result["errors"].append(f"DB error: {e}")

    # 用户素材
    user_mat_dir = UPLOADS_DIR / "user_materials"
    if user_mat_dir.exists():
        for user_dir in user_mat_dir.iterdir():
            if user_dir.is_dir():
                dest = sync_dir / "materials" / user_dir.name
                try:
                    _mirror_dir(user_dir, dest)
                    result["materials"] += sum(1 for _ in dest.rglob("*") if _.is_file())
                except Exception as e:
                    result["errors"].append(f"Mirror {user_dir.name}: {e}")

    # 视频作品
    video_dest = sync_dir / "videos"
    video_dest.mkdir(parents=True, exist_ok=True)
    for video in OUTPUTS_DIR.glob("final_tts_*.mp4"):
        try:
            shutil.copy2(video, video_dest / video.name)
            result["videos"] += 1
        except Exception as e:
            result["errors"].append(f"Video {video.name}: {e}")

    # 同步日志
    log_entry = {"time": datetime.now().isoformat(), "result": result}
    log_file = sync_dir / "sync_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return result


def _check_image_quality(path: Path) -> tuple[bool, str]:
    """检查图片质量：分辨率≥720p、大小≥30KB、不模糊"""
    ext = path.suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'):
        return True, ""  # 非图片不检查

    size_kb = path.stat().st_size / 1024
    if size_kb < MIN_IMG_KB:
        return False, f"文件太小({size_kb:.0f}KB<{MIN_IMG_KB}KB)"

    try:
        from PIL import Image
        img = Image.open(path)
        w, h = img.size
        if w < MIN_IMG_WIDTH or h < MIN_IMG_HEIGHT:
            return False, f"分辨率过低({w}x{h}<{MIN_IMG_WIDTH}x{MIN_IMG_HEIGHT})"

        # 模糊检测：缩小到100x100，算像素方差
        thumb = img.convert('L').resize((100, 100))
        import statistics
        pixels = list(thumb.getdata())
        variance = statistics.variance(pixels)
        if variance < BLUR_THRESHOLD:
            return False, f"画面模糊(方差{variance:.0f}<{BLUR_THRESHOLD})"
    except Exception:
        pass  # 无法检测时放行

    return True, ""


def _check_video_quality(path: Path) -> tuple[bool, str]:
    """检查视频质量：分辨率≥720p、大小≥1MB"""
    ext = path.suffix.lower()
    if ext not in ('.mp4', '.mov', '.avi', '.webm', '.mkv'):
        return True, ""

    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb < MIN_VIDEO_MB:
        return False, f"视频太小({size_mb:.1f}MB<{MIN_VIDEO_MB}MB)"

    try:
        import subprocess
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=10)
        if r.stdout.strip():
            w, h = map(int, r.stdout.strip().split(","))
            if w < MIN_VIDEO_WIDTH or h < MIN_VIDEO_HEIGHT:
                return False, f"分辨率过低({w}x{h}<{MIN_VIDEO_WIDTH}x{MIN_VIDEO_HEIGHT})"
    except Exception:
        pass  # 无法检测时放行

    return True, ""


def auto_sync_material(user_id: int, file_path: str, category: str):
    """单个素材上传后立即同步一份到存储（质量不达标则跳过）"""
    if not SYNC_ENABLED:
        return
    try:
        src = UPLOADS_DIR / file_path
        if not src.exists():
            return

        # 质量过滤
        ok, reason = _check_image_quality(src)
        if not ok:
            _log_skip(user_id, file_path, reason)
            return

        dest = Path(SYNC_ROOT) / "materials" / str(user_id) / category / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    except Exception:
        pass


def _log_skip(user_id: int, path: str, reason: str):
    """记录被过滤掉的素材"""
    try:
        log_dir = Path(SYNC_ROOT) / "rejected"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "rejected.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | user={user_id} | {path} | {reason}\n")
    except Exception:
        pass


def auto_sync_video(video_path: str):
    """视频生成后立即同步一份（质量不达标跳过）"""
    if not SYNC_ENABLED:
        return
    try:
        src = Path(video_path)
        if not src.is_absolute():
            src = OUTPUTS_DIR.parent / video_path
        if not src.exists():
            return

        ok, reason = _check_video_quality(src)
        if not ok:
            _log_skip(0, video_path, reason)
            return

        dest = Path(SYNC_ROOT) / "videos" / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    except Exception:
        pass


def _mirror_dir(src: Path, dest: Path):
    """增量镜像目录"""
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_file():
            target = dest / item.name
            if not target.exists() or item.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(item, target)
        elif item.is_dir():
            _mirror_dir(item, dest / item.name)
