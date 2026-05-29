"""即梦CLI 5.0 — AI精准生图，替代Pexels搜索"""
import json
import subprocess
import httpx
from pathlib import Path
from app.config import IMAGES_DIR, OUTPUTS_DIR

DREAMINA = "C:/Users/43453/bin/dreamina.exe"


def generate_scene_images(script_text: str, count: int = 5,
                          ratio: str = "16:9", resolution: str = "4k") -> list[Path]:
    """分析文案关键场景 → 生成即梦提示词 → CLI生图 → 下载 → 返回路径"""
    import hashlib
    prompts = _extract_scene_prompts(script_text, count)
    if not prompts:
        return []
    # 用文案哈希区分不同文案的缓存
    content_hash = hashlib.md5(script_text.encode()).hexdigest()[:8]

    images = []
    for i, prompt in enumerate(prompts[:count]):
        try:
            img = _dreamina_text2image(prompt, f"{content_hash}_scene_{i}", ratio, resolution)
            if img:
                images.append(img)
        except Exception as e:
            print(f"Dreamina scene {i} failed: {e}")
    return images


def _extract_scene_prompts(text: str, count: int) -> list[str]:
    """AI分析文案，提取关键场景的英文即梦提示词"""
    from openai import OpenAI
    from app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
    resp = client.chat.completions.create(
        model="qwen-plus",
        messages=[{
            "role": "user",
            "content": """你是历史纪录片的视觉导演。根据文案提取关键场景，为每个场景写即梦5.0的英文提示词。
格式：主体描述+场景环境+光影氛围+镜头语言+画质标签。
风格要求：Cinematic, historical documentary, realistic, 8K, masterpiece, ancient China.
只输出JSON数组，不要任何解释。"""},
            {"role": "user", "content": f"根据文案提取{count}个关键场景的即梦提示词（英文）：\n{text[:2000]}"},
        ], temperature=0.7, max_tokens=1500,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        data = json.loads(raw)
    except Exception:
        return []
    # 兼容 [\"str\"] 和 [{\"prompt\":\"str\"}] 两种格式
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return [item.get("prompt", item.get("text", str(item))) for item in data]
        return [str(item) for item in data]
    return []


def _dreamina_text2image(prompt: str, name: str,
                         ratio: str = "16:9", resolution: str = "4k") -> Path | None:
    """调用即梦CLI生图 → 下载 → 返回本地路径"""
    output_dir = IMAGES_DIR / "dreamina"
    output_dir.mkdir(exist_ok=True)
    out_path = output_dir / f"{name}.png"

    if out_path.exists():
        return out_path

    try:
        r = subprocess.run([
            DREAMINA, "text2image",
            "--prompt", prompt,
            "--ratio", ratio,
            "--resolution_type", resolution,
            "--model_version", "5.0",
            "--poll", "90",
        ], capture_output=True, text=True, timeout=120)

        data = json.loads(r.stdout)
        if data.get("gen_status") != "success":
            return None

        images = data.get("result_json", {}).get("images", [])
        if not images:
            return None

        # 下载第一张图（质量最高）
        url = images[0]["image_url"]
        resp = httpx.get(url, timeout=60, follow_redirects=True)
        if resp.status_code == 200:
            out_path.write_bytes(resp.content)
            return out_path
    except Exception as e:
        print(f"Dreamina error: {e}")
    return None
