"""AI图片生成 — 通义万相（仅做风景/场景保底，人物交给即梦）"""
import hashlib
import os
import re
from pathlib import Path
import httpx
from app.config import IMAGES_DIR


def generate_image(prompt: str, aspect_ratio: str = "9:16") -> Path | None:
    """生成一张AI图片（风景/场景类，避免人物）"""
    # 质量提示词：强调场景、光影、避免人物
    quality_tags = "cinematic lighting, 8k resolution, photorealistic, landscape photography, no humans, no people, no faces"
    full_prompt = f"{prompt}, {quality_tags}"
    cache_key = hashlib.md5(full_prompt.encode()).hexdigest()[:12]
    cache_path = IMAGES_DIR / f"ai_{cache_key}.png"
    if cache_path.exists():
        return cache_path

    # 画面比例（通义万相支持的尺寸）
    size_map = {"9:16": "720*1280", "16:9": "1280*720", "1:1": "1024*1024"}
    size = size_map.get(aspect_ratio, "720*1280")

    try:
        from dashscope import ImageSynthesis
        try:
            from app.main import get_user_key
            api_key = get_user_key("dashscope") or os.getenv("DASHSCOPE_API_KEY", "")
        except Exception:
            api_key = os.getenv("DASHSCOPE_API_KEY", "")
        r = ImageSynthesis.call(
            model="wanx2.1-t2i-turbo",
            api_key=api_key,
            prompt=full_prompt,
            n=1,
            size=size,
        )
        if r.status_code == 200 and r.output.results:
            img_url = r.output.results[0].url
            resp = httpx.get(img_url, timeout=60)
            resp.raise_for_status()
            cache_path.write_bytes(resp.content)
            return cache_path
    except Exception as e:
        print(f"[image_service] 通义万相生成失败 [{prompt[:40]}...]: {e}")
    return None


def generate_scene_images(script_text: str, count: int = 5,
                          aspect_ratio: str = "9:16") -> list[Path]:
    """根据文案内容生成场景图片（纯风景/场景，避免人物）"""
    segments = [s.strip() for s in re.split(r"[。！？\n]", script_text) if s.strip() and len(s.strip()) > 10]
    if len(segments) > count:
        merged = []
        chunk_size = max(1, len(segments) // count)
        for i in range(0, len(segments), chunk_size):
            merged.append("。".join(segments[i:i + chunk_size]))
        segments = merged[:count]

    images = []
    for seg in segments[:count]:
        # 用segment前100字作为prompt（去掉引号）
        clean_prompt = seg[:100].replace('"', '').replace('"', '').replace('"', '')
        img = generate_image(clean_prompt, aspect_ratio=aspect_ratio)
        if img:
            images.append(img)

    return images
