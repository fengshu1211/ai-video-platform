"""HyperFrames 渲染服务：生成HTML → 准备素材 → 调用HF渲染 → 返回视频路径"""

import os, json, shutil, tempfile, subprocess, random
from pathlib import Path

BGM_DIR = Path(__file__).parent.parent.parent / "uploads" / "bgm"
HF_TEMPLATE = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=720, height=1280\" />
  <script src=\"https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js\"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: 720px; height: 1280px; overflow: hidden; background: #000; }}
    .scene {{ position: absolute; inset: 0; }}
    .bg-video, .bg-img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
    .overlay {{ position: absolute; inset: 0; background: rgba(0,0,0,0.25); }}
    .caption {{
      position: absolute; left: 60px; right: 60px; text-align: center; z-index: 10;
      font-family: 'Microsoft YaHei', sans-serif;
      font-size: 40px; font-weight: 700; line-height: 1.3;
      color: #fff; text-shadow: 0 3px 14px rgba(0,0,0,0.8);
      top: 46%; transform: translateY(-50%);
    }}
    .price {{
      position: absolute; left: 50%; top: 55%; transform: translate(-50%, -50%);
      font-size: 58px; font-weight: 900; color: #ffb800; z-index: 10;
      text-shadow: 0 4px 24px rgba(255,184,0,0.5);
    }}
    .brand-bar {{
      position: absolute; bottom: 90px; left: 0; right: 0; text-align: center; z-index: 10;
      font-size: 20px; color: rgba(255,255,255,0.5); letter-spacing: 4px;
    }}
  </style>
</head>
<body>
  <div id=\"root\" data-composition-id=\"main\" data-start=\"0\" data-duration=\"{duration}\" data-width=\"720\" data-height=\"1280\">
    <audio src=\"assets/audio.mp3\" data-track-index=\"10\" data-start=\"0\" data-duration=\"{duration}\"></audio>
    {scenes}
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    var tl = gsap.timeline({{ paused: true }});
    {animations}
    window.__timelines[\"main\"] = tl;
  </script>
</body>
</html>
"""


def _mix_audio(tts_path: str, bgm_path: str, output_path: str, bgm_vol: float = 0.1):
    """混音：口播100% + BGM指定音量"""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tts_path, "-i", bgm_path,
        "-filter_complex", f"[1:a]volume={bgm_vol}[bgm];[0:a][bgm]amix=inputs=2:duration=first:normalize=0",
        "-b:a", "128k", output_path,
    ], check=True, capture_output=True, timeout=30)


def _split_video_for_segments(video_path: str, num_segments: int, work_dir: Path) -> list[str]:
    """将长视频切成N段，匹配文案段落数。返回assets中的文件名列表。"""
    from app.utils.ffmpeg_utils import get_media_duration
    total_dur = get_media_duration(Path(video_path))
    per_seg = total_dur / num_segments
    video_files = []
    ext = Path(video_path).suffix
    for i in range(num_segments):
        start = i * per_seg
        out_name = f"vseg_{i}{ext}"
        out_path = work_dir / "assets" / out_name
        subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.1f}",
            "-i", video_path, "-t", f"{per_seg:.1f}",
            "-an", "-c:v", "copy", str(out_path),
        ], check=True, capture_output=True, timeout=30)
        video_files.append(out_name)
    return video_files


def _split_script(text: str) -> list[str]:
    """把文案拆成2-4段，用于HyperFrames场景切换"""
    import re
    parts = [s.strip() for s in re.split(r"[。！？]", text) if s.strip() and len(s.strip()) > 3]
    if not parts:
        return [text]
    if len(parts) > 4:
        # 合并中间部分，保留开头+结尾
        mid = "".join(parts[1:-1])
        parts = [parts[0], mid[:40], parts[-1]]
    return parts


def generate_hf_video(
    script_text: str,
    tts_audio_path: str,
    material_paths: list[str],
    bgm_vol: float = 0.1,
    brand: str = "圣栎美家",
    work_dir: str | None = None,
) -> Path:
    """生成HyperFrames视频。

    Args:
        script_text: 文案全文
        tts_audio_path: TTS音频文件路径
        material_paths: 素材路径（图片/视频）
        bgm_vol: BGM相对音量（0-1，默认0.1）
        brand: 品牌名
        work_dir: 工作目录（None则自动创建临时目录）
    Returns:
        输出视频路径
    """
    from app.utils.ffmpeg_utils import get_media_duration

    # 工作目录
    if work_dir is None:
        work_dir = tempfile.mkdtemp(prefix="hf_")
    work = Path(work_dir)
    assets = work / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    # 1. 素材准备
    scenes_data = []
    materials = material_paths or []
    script_parts = _split_script(script_text)

    # 智能素材处理：长视频自动分段，短视频/图片直接使用
    num_parts = len(script_parts)
    # 先分类素材
    vid_mats = []
    img_mats = []
    for mat in materials:
        mat_path = Path(mat)
        if not mat_path.is_absolute():
            mat_path = Path(__file__).parent.parent.parent / "uploads" / mat
        if mat_path.exists():
            if mat_path.suffix.lower() in (".mp4", ".mov", ".avi", ".webm"):
                vid_mats.append(str(mat_path))
            else:
                img_mats.append(str(mat_path))

    # 视频处理：长视频分段，短视频直接去音轨
    video_segments = []  # 存 (asset_name, is_in_assets)
    if len(vid_mats) == 1 and num_parts > 1:
        # 单个长视频→按文案段落数切段，结果直接在assets里
        segs = _split_video_for_segments(vid_mats[0], num_parts, work)
        video_segments = [(s, True) for s in segs]
    elif vid_mats:
        for v in vid_mats[:num_parts]:
            ext = Path(v).suffix
            aname = f"v_{len(video_segments)}{ext}"
            subprocess.run(["ffmpeg", "-y", "-i", v,
                "-an", "-c:v", "copy", str(assets / aname)],
                check=True, capture_output=True, timeout=15)
            video_segments.append((aname, True))

    img_cycle = img_mats if img_mats else ["D:/HuaweiMoveData/Users/43453/Desktop/IMG_0153(1).png"]
    for i, part in enumerate(script_parts):
        if i < len(video_segments):
            aname, _ = video_segments[i]
            scenes_data.append({"media": aname, "type": "video", "text": part})
        else:
            src = img_cycle[i % len(img_cycle)]
            ext = Path(src).suffix
            aname = f"scene_{i}{ext}"
            shutil.copy2(src, str(assets / aname))
            scenes_data.append({"media": aname, "type": "image", "text": part})

    # 2. 音频混音
    bgm_files = list(BGM_DIR.glob("*.mp3"))
    bgm_path = str(random.choice(bgm_files)) if bgm_files else None
    if bgm_path:
        _mix_audio(tts_audio_path, bgm_path, str(assets / "audio.mp3"), bgm_vol)
    else:
        shutil.copy2(tts_audio_path, str(assets / "audio.mp3"))

    # 3. 音频时长
    duration = max(get_media_duration(Path(tts_audio_path)) - 0.1, 1.0)
    per_scene = duration / max(len(scenes_data), 1)

    # 4. 生成HTML
    scenes_html = ""
    anims = []
    for i, sd in enumerate(scenes_data):
        start = i * per_scene
        dur = per_scene
        tag = "video" if sd["type"] == "video" else "img"
        media_tag = f'<{tag} class="bg-{tag}" src="assets/{sd["media"]}"'
        if sd["type"] == "video":
            media_tag += ' muted playsinline'
        media_tag += ' />' if tag == "img" else '></video>'

        has_price = any(c in sd["text"] for c in "0123456789元每平仅需出厂价")
        cid = f"c{i}"
        price_html = ""
        price_anim = ""
        if has_price:
            # 提取价格数字用于金色大字展示
            import re
            pm = re.search(r'\d+元[^\s，。]*', sd["text"])
            price_text = pm.group(0) if pm else sd["text"][:15]
            price_html = f'\n      <div class=\"price\" id=\"p{i}\">{price_text}</div>'
            price_anim = f'.from("#p{i}", {{ opacity: 0, scale: 0.5, duration: 0.4, ease: \"back.out(1.7)\" }}, {start + 0.4:.1f})'
        scenes_html += f"""
    <div class=\"scene\" data-track-index=\"0\" data-start=\"{start:.2f}\" data-duration=\"{dur:.2f}\">
      {media_tag}
      <div class=\"overlay\"></div>
      <div class=\"caption\" id=\"{cid}\">{sd["text"]}</div>{price_html}
      <div class=\"brand-bar\">{brand}</div>
    </div>"""
        anims.append(f'.from("#{cid}", {{ opacity: 0, y: 20, duration: 0.5 }}, {start + 0.2:.1f})')
        if price_anim:
            anims.append(price_anim)

    html = HF_TEMPLATE.format(
        duration=f"{duration:.1f}",
        scenes=scenes_html,
        animations="tl" + "".join(anims) + ";",
    )
    (work / "index.html").write_text(html, encoding="utf-8")

    # 5. 渲染（用shell=True让Windows找到npx）
    result = subprocess.run(
        "npx hyperframes render",
        cwd=str(work),
        capture_output=True, text=True, timeout=600, shell=True,
    )
    # 找输出文件
    renders_dir = work / "renders"
    videos = sorted(renders_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if videos:
        return videos[0]

    raise RuntimeError(f"HF render failed: {result.stderr[-500:]}")
