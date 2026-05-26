"""FFmpeg 命令封装——所有视频处理操作统一在此"""
import os
import subprocess
import shutil
from pathlib import Path

# 确保 FFmpeg 可在 PATH 中找到（处理 winget 安装后 PATH 未刷新的情况）
_FFMPEG_BIN = None


def _find_ffmpeg() -> str:
    """查找 FFmpeg bin 目录"""
    global _FFMPEG_BIN
    if _FFMPEG_BIN:
        return _FFMPEG_BIN

    # 先检查 PATH
    if shutil.which("ffmpeg"):
        _FFMPEG_BIN = ""
        return ""

    # 搜索常见安装位置
    search_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages",
        Path("C:/Program Files"),
        Path("C:/ffmpeg"),
    ]
    for base in search_paths:
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            if "ffmpeg.exe" in files and root.endswith("bin"):
                _FFMPEG_BIN = root
                os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")
                return root
            # 限制搜索深度
            if len(Path(root).parts) - len(base.parts) > 6:
                dirs.clear()

    return ""


# 模块加载时自动查找 FFmpeg
_find_ffmpeg()


def check_ffmpeg() -> bool:
    """检查 FFmpeg 是否可用"""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def get_media_duration(file_path: Path) -> float:
    """获取音视频时长（秒）"""
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(file_path)],
        capture_output=True, text=True, timeout=10,
    )
    out = result.stdout.strip()
    if not out:
        raise RuntimeError(f"无法获取时长: {file_path}")
    return float(out)


def image_to_video(image_path: Path, audio_path: Path, output_path: Path, duration: float | None = None):
    """静态图片 + 音频 → 视频（图片循环显示）"""
    dur = duration or get_media_duration(audio_path)
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(dur),
        "-shortest",
        str(output_path),
    ], check=True, timeout=300)


def concat_media(file_list: list[Path], output_path: Path):
    """拼接多个图片/视频为连续时间线，每段时长按音频比例分配"""
    # 使用 concat demuxer
    concat_txt = output_path.with_suffix(".concat.txt")
    lines = []
    for f in file_list:
        lines.append(f"file '{f.as_posix()}'")
    concat_txt.write_text("\n".join(lines), encoding="utf-8")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ], check=True, timeout=300)
    concat_txt.unlink(missing_ok=True)


def concat_with_crossfade(file_list: list[Path], output_path: Path, fade_dur: float = 0.5):
    """拼接多个视频片段，片段间交叉淡入淡出（比硬切更流畅）

    逐对 xfade：先合并前两个，结果再和第三个合并，以此类推。
    每轮都 fps=25 + settb=1/25 归一化，避免时间基错乱导致时长膨胀。
    """
    import shutil
    n = len(file_list)
    if n <= 1:
        shutil.copy2(str(file_list[0]), str(output_path))
        return

    durations = [get_media_duration(f) for f in file_list]
    work_dir = output_path.parent

    # 当前累积视频 = 第一个片段（归一化到 25fps）
    current = work_dir / f"_xfade_0_{output_path.stem}.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(file_list[0]),
        "-vf", "fps=25,settb=1/25",
        "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(current),
    ], check=True, timeout=120)
    cumulative_dur = durations[0]

    for i in range(1, n):
        next_in = file_list[i]
        dur_next = durations[i]
        offset = cumulative_dur - fade_dur
        prev = current
        current = work_dir / f"_xfade_{i}_{output_path.stem}.mp4"

        # 当前累积 + 下一个片段 → 归一化后 xfade
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(prev),
            "-i", str(next_in),
            "-filter_complex",
            f"[0:v]fps=25,settb=1/25[v0];[1:v]fps=25,settb=1/25[v1];"
            f"[v0][v1]xfade=transition=fade:duration={fade_dur}:offset={offset:.3f}[v]",
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-an",
            "-r", "25",
            str(current),
        ], check=True, timeout=300)

        # 清理中间文件（保留最后一个 current 即最终输出）
        if i > 1:
            prev.unlink(missing_ok=True)
        cumulative_dur = cumulative_dur + dur_next - fade_dur

    # 最终输出
    if current != output_path:
        shutil.move(str(current), str(output_path))
    # 清理第一个中间文件
    first_tmp = work_dir / f"_xfade_0_{output_path.stem}.mp4"
    first_tmp.unlink(missing_ok=True)


def mix_audio_bgm(speech_path: Path, bgm_path: Path, output_path: Path, bgm_volume: float = 0.3):
    """语音 + 背景音乐混音"""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(speech_path),
        "-i", str(bgm_path),
        "-filter_complex",
        f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ], check=True, timeout=120)


def burn_subtitles(video_path: Path, subtitle_path: Path, output_path: Path, format: str = "srt"):
    """将字幕烧录到视频，支持 SRT 和 ASS 格式"""
    import shutil

    # FFmpeg字幕滤镜对中文路径敏感，在outputs目录用简单文件名处理
    work_dir = output_path.parent
    tmp_video = work_dir / f"_in_{output_path.stem[:12]}.mp4"
    tmp_sub = work_dir / f"_sub_{output_path.stem[:12]}.{format}"
    shutil.copy2(video_path, tmp_video)
    shutil.copy2(subtitle_path, tmp_sub)

    # 先用subtitles滤镜（对ASS/SRT都兼容），失败回退到ass/drawtext
    vf_filter = f"subtitles={tmp_sub.name}"

    try:
        # 需要cd到工作目录，因为字幕滤镜对绝对路径处理有问题
        import os
        orig_cwd = os.getcwd()
        os.chdir(str(work_dir))
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", tmp_video.name,
                "-vf", vf_filter,
                "-c:a", "copy",
                output_path.name,
            ], check=True, timeout=300)
        finally:
            os.chdir(orig_cwd)
    except subprocess.CalledProcessError as e:
        # subtitles滤镜失败时，ASS回退到ass滤镜，SRT回退到默认
        if format == "ass":
            os.chdir(str(work_dir))
            try:
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", tmp_video.name,
                    "-vf", f"ass={tmp_sub.name}",
                    "-c:a", "copy",
                    output_path.name,
                ], check=True, timeout=300)
            finally:
                os.chdir(orig_cwd)
        else:
            raise e
    finally:
        tmp_video.unlink(missing_ok=True)
        tmp_sub.unlink(missing_ok=True)


def apply_blur(input_path: Path, output_path: Path, strength: int = 8):
    """给视频/图片添加模糊效果（用于背景素材）"""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"boxblur={strength}:1",
        "-c:a", "copy",
        "-preset", "veryfast",
        str(output_path),
    ], check=True, timeout=300)


def audio_video_merge(video_path: Path, audio_path: Path, output_path: Path):
    """视频画面 + 独立音频轨道合并"""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        str(output_path),
    ], check=True, timeout=300)


def generate_virtual_host_clip(
    image_path: Path,
    output_path: Path,
    duration: float,
    width: int,
    height: int,
):
    """虚拟主播：单张照片+微动呼吸感（缓慢zoom+微晃+亮度微变）"""
    fps = 25
    frames = max(int(duration * fps), 1)
    # 极微小的zoom：1.0 → 1.02
    zoom_step = 0.02 / frames
    # 微小平移：模拟身体轻晃
    pan_px = max(2, int(width * 0.01))
    pan_step = pan_px * 2 / frames

    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='1+{zoom_step:.6f}*on':"
        f"x='iw/2-(iw/zoom/2)+{pan_step:.3f}*sin(on*0.05)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"d=1:s={width}x{height}:fps={fps},"
        f"eq=brightness=0.01*sin(on*0.08)"  # 亮度微变模拟呼吸
    )
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "25", "-loop", "1", "-i", str(image_path),
        "-t", str(duration), "-an",
        "-vf", f"{vf},fps=25,settb=1/25",
        "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage",
        "-pix_fmt", "yuv420p", "-r", "25", str(output_path),
    ], check=True, timeout=120)


def generate_ken_burns_clip(
    image_path: Path,
    output_path: Path,
    duration: float,
    width: int,
    height: int,
    animation_type: str,
):
    """Ken Burns 效果：静态图片 → 动态视频片段

    animation_type 可选:
        zoom_in   - 缓慢放大
        zoom_out  - 缓慢缩小
        pan_left  - 从左向右平移
        pan_right - 从右向左平移
        pan_up    - 从下向上平移
        pan_down  - 从上向下平移
    """
    fps = 25
    frames = max(int(duration * fps), 1)

    # zoompan 滤镜表达式
    if animation_type == "zoom_in":
        step = 0.2 / frames
        vf = (
            f"zoompan=z='1+{step:.6f}*on':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "zoom_out":
        step = 0.2 / frames
        vf = (
            f"zoompan=z='1.2-{step:.6f}*on':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "pan_left":
        vf = (
            f"zoompan=z=1.1:"
            f"x='(iw-iw/zoom)*on/{frames}':"
            f"y='(ih-ih/zoom)/2':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "pan_right":
        vf = (
            f"zoompan=z=1.1:"
            f"x='(iw-iw/zoom)*({frames}-on)/{frames}':"
            f"y='(ih-ih/zoom)/2':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "pan_up":
        vf = (
            f"zoompan=z=1.1:"
            f"x='(iw-iw/zoom)/2':"
            f"y='(ih-ih/zoom)*on/{frames}':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "pan_down":
        vf = (
            f"zoompan=z=1.1:"
            f"x='(iw-iw/zoom)/2':"
            f"y='(ih-ih/zoom)*({frames}-on)/{frames}':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "zoom_in_slow":
        step = 0.12 / frames
        vf = (
            f"zoompan=z='1+{step:.6f}*on':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "zoom_out_slow":
        step = 0.12 / frames
        vf = (
            f"zoompan=z='1.12-{step:.6f}*on':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "zoom_in_fast":
        step = 0.35 / frames
        vf = (
            f"zoompan=z='1+{step:.6f}*on':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "zoom_out_fast":
        step = 0.35 / frames
        vf = (
            f"zoompan=z='1.35-{step:.6f}*on':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "diagonal_lr":
        vf = (
            f"zoompan=z=1.15:"
            f"x='(iw-iw/zoom)*on/{frames}':"
            f"y='(ih-ih/zoom)*on/{frames}':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    elif animation_type == "diagonal_rl":
        vf = (
            f"zoompan=z=1.15:"
            f"x='(iw-iw/zoom)*({frames}-on)/{frames}':"
            f"y='(ih-ih/zoom)*on/{frames}':"
            f"d=1:s={width}x{height}:fps={fps}"
        )
    else:
        # 兜底：无动画静态图
        subprocess.run([
            "ffmpeg", "-y", "-framerate", "25", "-loop", "1", "-i", str(image_path),
            "-t", str(duration), "-an",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps=25",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-r", "25", str(output_path),
        ], check=True, timeout=60)
        return

    # zoompan 会拉伸图片到 s=wxh，所以先 crop 到目标比例再 zoompan
    pre_filter = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-framerate", "25", "-i", str(image_path),
        "-t", str(duration), "-an",
        "-vf", f"{pre_filter},fps=25,settb=1/25,{vf}",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-pix_fmt", "yuv420p", "-r", "25", str(output_path),
    ], check=True, timeout=120)
