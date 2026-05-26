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


def _get_persona_prompts(user_id: int) -> tuple[list[str], str]:
    """从人设提取AI生图关键词和风格"""
    import sqlite3, json as _json
    db_path = str(UPLOADS_DIR.parent / "data.db")
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT ai_keywords, industry, specialization FROM user_personas WHERE user_id=? LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return [], ""

    keywords = _json.loads(row[0]) if isinstance(row[0], str) else (row[0] or [])
    industry = row[1] or ""
    spec = row[2] or ""

    style_map = {
        "历史": "historical documentary, ancient China, cinematic lighting, photorealistic, 8K",
        "家居": "interior design, home renovation, modern Chinese style, natural light, 8K",
        "科技": "tech product photography, clean background, studio lighting, 8K",
        "美食": "food photography, Chinese cuisine, warm lighting, shallow depth of field, 8K",
    }
    base_style = ""
    for k, v in style_map.items():
        if k in industry or k in spec:
            base_style = v
            break
    if not base_style:
        base_style = "photorealistic, cinematic lighting, 8K, high quality"

    return keywords[:5], base_style


def _gen_images(prompts: list[str], base_style: str, user_dir: Path, count: int) -> list[dict]:
    """生成图片：Dreamina优先，Pexels兜底"""
    import subprocess as _sp, json as _json, time as _time, httpx as _hx
    dreamina_path = "C:/Users/43453/bin/dreamina.exe"
    use_dreamina = Path(dreamina_path).exists()
    results = []

    for i, kw in enumerate(prompts[:count]):
        prompt = f"{kw}, {base_style}"
        try:
            if use_dreamina:
                r = _sp.run([dreamina_path, "text2image", "--prompt", prompt[:200],
                    "--ratio", "9:16", "--resolution_type", "2k",
                    "--model_version", "5.0", "--poll", "60"],
                    capture_output=True, text=True, timeout=90)
                data = _json.loads(r.stdout)
                if data.get("gen_status") == "success":
                    img_url = data["result_json"]["images"][0]["image_url"]
                else:
                    continue
                ext = ".png"
            else:
                from app.services.material_service import search_images
                imgs = search_images(prompt[:80], per_page=1)
                if not imgs:
                    continue
                img_url = imgs[0]["download_url"]
                ext = ".jpg"

            resp = _hx.get(img_url, timeout=60)
            if resp.status_code == 200:
                fname = f"ai_{i+1}{ext}"
                fpath = user_dir / fname
                fpath.write_bytes(resp.content)
                results.append({
                    "name": f"{kw}",
                    "filename": fname,
                    "path": str(fpath.relative_to(UPLOADS_DIR)),
                    "size": len(resp.content),
                })
            _time.sleep(1)
        except Exception as e:
            print(f"Image gen failed for {kw}: {e}")
    return results


@router.post("/generate-recommended")
def generate_recommended(user_id: int):
    """快速生成3张AI推荐素材"""
    keywords, base_style = _get_persona_prompts(user_id)
    if not keywords:
        return {"code": 1, "message": "请先设置创作人设"}

    user_dir = UPLOADS_DIR / "user_materials" / str(user_id) / "AI推荐"
    user_dir.mkdir(parents=True, exist_ok=True)
    results = _gen_images(keywords, base_style, user_dir, 3)

    # 同步到平台存储
    try:
        from app.services.sync_service import auto_sync_material
        for f in results:
            auto_sync_material(user_id, f["path"], "AI推荐")
    except Exception:
        pass

    return {"code": 0, "message": f"已生成{len(results)}张素材", "files": results}


@router.post("/pre-generate")
def pre_generate(user_id: int):
    """批量预生成10张AI素材（一次性配齐，同步到服务器）"""
    keywords, base_style = _get_persona_prompts(user_id)
    if not keywords:
        return {"code": 1, "message": "请先设置创作人设"}

    user_dir = UPLOADS_DIR / "user_materials" / str(user_id) / "AI推荐"
    user_dir.mkdir(parents=True, exist_ok=True)
    results = _gen_images(keywords, base_style, user_dir, 10)

    # 同步到平台存储
    try:
        from app.services.sync_service import auto_sync_material
        for f in results:
            auto_sync_material(user_id, f["path"], "AI推荐")
    except Exception:
        pass

    return {"code": 0, "message": f"预生成完成：{len(results)}张素材已同步", "files": results}


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
