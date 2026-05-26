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


@router.post("/generate-recommended")
def generate_recommended(user_id: int):
    """根据用户人设，用即梦AI生成推荐素材"""
    import sqlite3, json, subprocess, time

    db_path = str(UPLOADS_DIR.parent / "data.db")
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT ai_keywords, industry, specialization FROM user_personas WHERE user_id=? LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()

    if not row or not row[0]:
        return {"code": 1, "message": "请先设置创作人设"}

    keywords = json.loads(row[0]) if isinstance(row[0], str) else (row[0] or [])
    industry = row[1] or ""
    spec = row[2] or ""

    # 构建生图提示词
    prompts = []
    style_map = {
        "历史": "historical documentary, ancient China, cinematic lighting, photorealistic, 8K",
        "家居": "interior design, home renovation, modern Chinese style, natural light, photorealistic, 8K",
        "科技": "tech product photography, clean background, studio lighting, 8K, photorealistic",
        "美食": "food photography, Chinese cuisine, warm lighting, shallow depth of field, 8K",
    }
    base_style = ""
    for k, v in style_map.items():
        if k in industry or k in spec:
            base_style = v
            break
    if not base_style:
        base_style = "photorealistic, cinematic lighting, 8K, high quality"

    for kw in keywords[:5]:
        prompt = f"{kw}, {base_style}"
        prompts.append(prompt)

    # 生图：本地Dreamina优先，服务器Pexels兜底
    user_dir = UPLOADS_DIR / "user_materials" / str(user_id) / "AI推荐"
    user_dir.mkdir(parents=True, exist_ok=True)
    results = []
    dreamina_path = "C:/Users/43453/bin/dreamina.exe"
    use_dreamina = Path(dreamina_path).exists()

    for i, prompt in enumerate(prompts[:3]):
        try:
            if use_dreamina:
                # 即梦AI生图（Windows本地）
                r = subprocess.run([
                    dreamina_path, "text2image", "--prompt", prompt[:200],
                    "--ratio", "9:16", "--resolution_type", "2k",
                    "--model_version", "5.0", "--poll", "60",
                ], capture_output=True, text=True, timeout=90)
                data = json.loads(r.stdout)
                if data.get("gen_status") == "success":
                    img_url = data["result_json"]["images"][0]["image_url"]
                else:
                    continue
            else:
                # 服务器兜底：Pexels搜图
                from app.services.material_service import search_images
                imgs = search_images(prompt[:80], per_page=1)
                if imgs:
                    img_url = imgs[0]["download_url"]
                else:
                    continue

            import httpx
            resp = httpx.get(img_url, timeout=60)
            if resp.status_code == 200:
                ext = ".png" if use_dreamina else ".jpg"
                fname = f"ai_recommend_{i+1}{ext}"
                fpath = user_dir / fname
                fpath.write_bytes(resp.content)
                results.append({
                    "name": f"{keywords[i] if i < len(keywords) else 'AI素材'}",
                    "filename": fname,
                    "path": f"user_materials/{user_id}/AI推荐/{fname}",
                    "size": len(resp.content),
                })
            time.sleep(1)
        except Exception as e:
            print(f"Image gen failed: {e}")

    return {"code": 0, "message": f"已生成{len(results)}张素材", "files": results}


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
