"""平台数据自动同步——用户素材+视频定期同步到指定存储位置"""
import os
import shutil
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from app.config import UPLOADS_DIR, OUTPUTS_DIR, BASE_DIR

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


def auto_sync_material(user_id: int, file_path: str, category: str):
    """单个素材上传后立即同步一份到存储"""
    if not SYNC_ENABLED:
        return
    try:
        src = UPLOADS_DIR / file_path
        if src.exists():
            dest = Path(SYNC_ROOT) / "materials" / str(user_id) / category / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    except Exception:
        pass


def auto_sync_video(video_path: str):
    """视频生成后立即同步一份"""
    if not SYNC_ENABLED:
        return
    try:
        src = Path(video_path)
        if not src.is_absolute():
            src = OUTPUTS_DIR.parent / video_path
        if src.exists():
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
