"""视频素材搜索与下载 — Pexels + Pixabay 双源（免版权）"""
import httpx
from pathlib import Path
from app.config import VIDEOS_DIR

PEXELS_KEY = "hEU1qSKp8MeykvCriv7Ccnvf4Zi0WiDpRhtnmaQuBdukO1vKku1XHVa1"
PIXABAY_KEY = "55974660-6a81b5bb44f046952573e1f58"


def search_images(query: str, per_page: int = 8) -> list[dict]:
    """双源搜图：Pexels优先，Pixabay补充"""
    results = _search_pexels_images(query, per_page)
    if len(results) < per_page and PIXABAY_KEY:
        results.extend(_search_pixabay_images(query, per_page - len(results)))
    return results[:per_page]


def _search_pexels_images(query: str, per_page: int = 8) -> list[dict]:
    try:
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": per_page, "orientation": "portrait", "size": "medium"},
            timeout=10,
        )
        resp.raise_for_status()
        return [{"id": f"px_img_{p['id']}", "download_url": p["src"]["large"],
                 "width": p["width"], "height": p["height"],
                 "photographer": p.get("photographer", ""),
                 "avg_color": p.get("avg_color", "")}
                for p in resp.json().get("photos", [])]
    except Exception:
        return []


def _search_pixabay_images(query: str, per_page: int = 5) -> list[dict]:
    try:
        resp = httpx.get(
            "https://pixabay.com/api/",
            params={"key": PIXABAY_KEY, "q": query, "per_page": per_page,
                    "orientation": "vertical", "image_type": "photo", "safesearch": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        return [{"id": f"pb_img_{h['id']}", "download_url": h["largeImageURL"],
                 "width": h["imageWidth"], "height": h["imageHeight"],
                 "photographer": h.get("user", "")}
                for h in resp.json().get("hits", [])]
    except Exception:
        return []


def download_image(url: str, img_id: str) -> Path:
    """下载图片到本地，返回路径"""
    cache_path = VIDEOS_DIR.parent / "images" / f"{img_id}.jpg"
    if cache_path.exists():
        return cache_path
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(resp.content)
    return cache_path


def search_videos(query: str, per_page: int = 8) -> list[dict]:
    """双源搜索：Pexels优先，Pixabay补充"""
    results = _search_pexels(query, per_page)
    if len(results) < per_page and PIXABAY_KEY:
        results.extend(_search_pixabay(query, per_page - len(results)))
    return results[:per_page]


def _search_pexels(query: str, per_page: int = 8) -> list[dict]:
    try:
        resp = httpx.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": per_page, "orientation": "portrait", "size": "medium"},
            timeout=10,
        )
        resp.raise_for_status()
        results = []
        for v in resp.json().get("videos", []):
            best = None
            for vf in v.get("video_files", []):
                if vf.get("width") == 1080 or vf.get("quality") == "hd":
                    best = vf; break
            if not best and v.get("video_files"):
                best = v["video_files"][-1]
            if best:
                results.append({
                    "id": f"px_{v['id']}", "url": v.get("url",""),
                    "download_url": best["link"],
                    "duration": v.get("duration",10),
                    "width": best.get("width",1080), "height": best.get("height",1920),
                })
        return results
    except Exception:
        return []


def _search_pixabay(query: str, per_page: int = 5) -> list[dict]:
    try:
        resp = httpx.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_KEY, "q": query, "per_page": per_page},
            timeout=10,
        )
        resp.raise_for_status()
        results = []
        for v in resp.json().get("hits", []):
            best = None
            for size in ["large","medium","small"]:
                if v.get("videos",{}).get(size):
                    best = v["videos"][size]; break
            if best:
                results.append({
                    "id": f"pb_{v['id']}", "url": v.get("pageURL",""),
                    "download_url": best["url"],
                    "duration": best.get("duration",10),
                    "width": best.get("width",1920), "height": best.get("height",1080),
                })
        return results
    except Exception:
        return []


def download_video(download_url: str, video_id: str) -> Path:
    source = "pexels" if str(video_id).startswith("px_") else "pixabay"
    cache_path = VIDEOS_DIR / f"{source}_{video_id}.mp4"
    if cache_path.exists():
        return cache_path
    resp = httpx.get(download_url, timeout=120)
    resp.raise_for_status()
    cache_path.write_bytes(resp.content)
    return cache_path
