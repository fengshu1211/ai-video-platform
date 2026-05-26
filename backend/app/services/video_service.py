"""视频合成管线——编排TTS + FFmpeg全流程"""
import json
import re
import shutil
import subprocess
from pathlib import Path
from app.config import OUTPUTS_DIR, IMAGES_DIR, VIDEOS_DIR
from app.utils.ffmpeg_utils import (
    image_to_video, concat_media, concat_with_crossfade, mix_audio_bgm,
    audio_video_merge, get_media_duration,
)


def _clean_spoken_text(text: str) -> str:
    """去掉口播不应念出的括号/标记内容：（）()【】[] """
    import re
    # 中文括号 （...）
    text = re.sub(r'（[^）]*）', '', text)
    # 英文括号 (...)
    text = re.sub(r'\([^)]*\)', '', text)
    # 中文方括号 【...】
    text = re.sub(r'【[^】]*】', '', text)
    # 英文字母标记如 [图1] [注]
    text = re.sub(r'\[[^\]]*\]', '', text)
    # 清理多余空格和连续标点
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'，,', '，', text)
    text = re.sub(r'。。', '。', text)
    return text


def generate_video(
    script_text: str,
    voice_id: str,
    custom_voice_sample: str | None = None,
    bgm_path: str | None = None,
    bgm_volume: float = 0.3,
    material_paths: list[str] | None = None,
    lip_sync_video: str | None = None,
    lip_sync_mode: str = "pip",
    aspect_ratio: str = "9:16",
    subtitle_enabled: bool = True,
    subtitle_animation: str = "fade",
    image_animation_type: str | None = None,
    progress_callback=None,
) -> Path:
    """视频生成完整管线"""
    from app.services.tts_service import text_to_speech

    def report(percent: int, msg: str):
        if progress_callback:
            progress_callback(percent, msg)

    RESOLUTIONS = {
        "9:16": (1080, 1920),
        "16:9": (1920, 1080),
        "1:1": (1080, 1080),
    }
    width, height = RESOLUTIONS.get(aspect_ratio, (1080, 1920))
    VIDEO_SCALE = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    IMAGE_SCALE = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"

    # 去括号内容（口播不念方向提示、图片标注等）
    spoken_text = _clean_spoken_text(script_text)
    report(5, "正在合成语音...")
    tts_result = text_to_speech(spoken_text, voice_id, reference_sample=custom_voice_sample, return_subtitles=True)
    if isinstance(tts_result, tuple):
        speech_path, mini_subtitles = tts_result
    else:
        speech_path, mini_subtitles = tts_result, []
    speech_duration = get_media_duration(speech_path)
    report(25, f"语音合成完成（{speech_duration:.1f}秒）")

    if lip_sync_video:
        lip_path = Path(lip_sync_video)
        if not lip_path.is_absolute():
            lip_path = OUTPUTS_DIR.parent / lip_sync_video
        if lip_sync_mode == "auto_align":
            report(28, "正在自动对齐视频速度...")
            video_dur = get_media_duration(lip_path)
            ratio = speech_duration / max(video_dur, 0.1)

            # 速度比提醒：太极端效果不好
            if ratio > 2.5:
                report(30, f"⚠ 原视频偏短({video_dur:.0f}s)，建议录制更长视频获得更好效果")
            elif ratio < 0.4:
                report(30, f"⚠ 原视频偏长({video_dur:.0f}s)，建议录制{int(speech_duration*1.2)}秒左右的视频")

            aligned = OUTPUTS_DIR / f"aligned_{lip_path.stem}.mp4"
            from subprocess import run
            # 改进：中等画质+轻微降噪+人脸区域优先裁剪
            vf_parts = [f"setpts={ratio:.4f}*PTS"]
            # 如果变速后有明显伪影，加轻微降噪
            if ratio > 1.8 or ratio < 0.6:
                vf_parts.append("hqdn3d=2:1:3:3")
            vf_parts.append(VIDEO_SCALE)
            vf_str = ",".join(vf_parts)

            run(["ffmpeg","-y","-i",str(lip_path),"-an",
                "-vf",vf_str,
                "-c:v","libx264","-preset","medium","-crf","22",
                "-pix_fmt","yuv420p",str(aligned)], check=True, timeout=120)
            lip_sync_video = str(aligned.relative_to(aligned.parent.parent))
            report(32, f"自动对齐完成（视频{ratio:.2f}x变速）")
        elif lip_sync_mode == "audio_only":
            report(28, "正在替换音频...")
            muted = OUTPUTS_DIR / f"muted_{lip_path.stem}.mp4"
            from subprocess import run
            run(["ffmpeg","-y","-i",str(lip_path),"-an","-c:v","copy",str(muted)], check=True, timeout=30)
            lip_sync_video = str(muted.relative_to(muted.parent.parent))
            report(32, "音频替换完成")
        elif lip_sync_mode == "digital_human":
            report(28, "正在生成数字人...")
            try:
                from app.services.wav2lip_service import process_sadtalker
                if lip_path.suffix.lower() in ('.jpg','.jpeg','.png','.gif','.bmp','.webp'):
                    ds_out = process_sadtalker(lip_path, speech_path)
                    if ds_out:
                        lip_sync_video = str(ds_out.relative_to(ds_out.parent.parent))
                        report(32, "数字人生成完成")
                else:
                    from subprocess import run as srun
                    frame = OUTPUTS_DIR / f"frame_{lip_path.stem}.jpg"
                    srun(["ffmpeg","-y","-i",str(lip_path),"-vframes","1","-q:v","2",str(frame)], check=True, timeout=30)
                    ds_out = process_sadtalker(frame, speech_path)
                    frame.unlink(missing_ok=True)
                    if ds_out:
                        lip_sync_video = str(ds_out.relative_to(ds_out.parent.parent))
                        report(32, "数字人生成完成")
            except Exception as e:
                print(f"SadTalker error: {e}")
        else:
            report(28, "正在进行口型同步...")
            try:
                from app.services.wav2lip_service import process_lip_sync, is_available
                if is_available():
                    if lip_path.exists():
                        preprocessed = OUTPUTS_DIR / f"pre_{lip_path.stem}.mp4"
                        from subprocess import run
                        run(["ffmpeg","-y","-i",str(lip_path),"-vf","format=yuv420p","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(preprocessed)], check=True, timeout=60)
                        ls_out = process_lip_sync(preprocessed, speech_path)
                        preprocessed.unlink(missing_ok=True)
                        if ls_out:
                            lip_sync_video = str(ls_out.relative_to(ls_out.parent.parent))
                            report(32, "口型同步完成")
            except Exception as e:
                print(f"Lip-sync error: {e}")

    report(30, "正在处理素材...")
    materials = material_paths or []
    if not materials:
        black_bg = IMAGES_DIR / "_black_bg.png"
        if not black_bg.exists():
            from subprocess import run
            run(["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x1a1a2e:s={width}x{height}:d=1","-frames:v","1",str(black_bg)], check=True, timeout=10)
        materials = [str(black_bg.relative_to(black_bg.parent.parent))]

    report(45, "正在处理音频...")
    final_audio = speech_path
    if bgm_path:
        bgm_full = Path(bgm_path)
        if not bgm_full.is_absolute():
            bgm_full = OUTPUTS_DIR.parent / bgm_path
        if bgm_full.exists():
            mixed_audio = OUTPUTS_DIR / f"mixed_{speech_path.stem}.m4a"
            mix_audio_bgm(speech_path, bgm_full, mixed_audio, bgm_volume)
            final_audio = mixed_audio
            report(55, "BGM混音完成")

    report(60, "正在合成视频画面...")
    material_clips = []
    valid_mats = []
    for mat in materials:
        mat_path = Path(mat)
        if not mat_path.is_absolute():
            mat_path = OUTPUTS_DIR.parent / mat
        if mat_path.exists():
            valid_mats.append(mat_path)

    import random as _random
    ANIM_TYPES = [
        "zoom_in_slow", "zoom_out_slow", "pan_left", "pan_right",
        "pan_up", "pan_down", "zoom_in_fast", "zoom_out_fast",
        "diagonal_lr", "diagonal_rl",
    ]
    per_dur = speech_duration / max(len(valid_mats), 1)
    for i, mat_path in enumerate(valid_mats):
        ext = mat_path.suffix.lower()
        if ext in (".jpg",".jpeg",".png",".gif",".bmp",".webp"):
            clip = OUTPUTS_DIR / f"clip_{i}_{mat_path.stem}.mp4"
            # 随机选动画，相邻不重复
            anim = image_animation_type or _random.choice(ANIM_TYPES)
            report(62, f"正在生成图片动画（{anim}）...")
            from app.utils.ffmpeg_utils import generate_ken_burns_clip
            generate_ken_burns_clip(mat_path, clip, per_dur, width, height, anim)
            material_clips.append(clip)
        elif ext in (".mp4",".mov",".avi",".webm",".mkv"):
            trimmed = OUTPUTS_DIR / f"trim_{i}_{mat_path.stem}.mp4"
            from subprocess import run
            run(["ffmpeg","-y","-i",str(mat_path),"-t",str(per_dur),"-an",
                "-vf",f"{VIDEO_SCALE},fps=25,settb=1/25",
                "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
                "-r","25",str(trimmed)], check=True, timeout=60)
            material_clips.append(trimmed)

    if not material_clips:
        fallback = OUTPUTS_DIR / "_fallback.mp4"
        from subprocess import run
        run(["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x1a1a2e:s={width}x{height}:d={speech_duration}","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(fallback)], check=True, timeout=60)
        material_clips.append(fallback)

    if len(material_clips) > 1:
        merged_video = OUTPUTS_DIR / f"merged_{speech_path.stem}.mp4"
        try:
            concat_with_crossfade(material_clips, merged_video, fade_dur=1.5)
        except Exception:
            # 帧率不一致时回退硬切
            concat_media(material_clips, merged_video)
    else:
        merged_video = material_clips[0]

    report(75, "正在合并音视频...")
    temp_output = OUTPUTS_DIR / f"temp_{speech_path.stem}.mp4"
    audio_video_merge(merged_video, final_audio, temp_output)
    report(85, "音视频合并完成")

    if lip_sync_video:
        report(88, "正在合成口型视频...")
        lip_path = Path(lip_sync_video)
        if not lip_path.is_absolute():
            lip_path = OUTPUTS_DIR.parent / lip_sync_video
        if lip_path.exists():
            pip_output = OUTPUTS_DIR / f"pip_{speech_path.stem}.mp4"
            from subprocess import run
            if lip_sync_mode == "full":
                # 全屏：对口型视频铺满，合成TTS音频
                run(["ffmpeg","-y","-i",str(lip_path),"-i",str(final_audio),
                    "-vf",VIDEO_SCALE,"-map","0:v","-map","1:a",
                    "-c:v","libx264","-c:a","aac","-ar","44100","-b:a","192k",
                    "-preset","veryfast",str(pip_output)], check=True, timeout=120)
            elif lip_sync_mode == "digital_human":
                # 数字人：SadTalker视频+合成TTS音频，-shortest对齐
                run(["ffmpeg","-y","-i",str(lip_path),"-i",str(final_audio),
                    "-vf",VIDEO_SCALE,"-map","0:v","-map","1:a",
                    "-c:v","libx264","-c:a","aac","-ar","44100","-b:a","192k",
                    "-shortest","-preset","veryfast",str(pip_output)], check=True, timeout=120)
            else:
                scale = 0.25
                ow = int(width * scale)
                oh = int(height * scale)
                ox = width - ow - 20
                oy = height - oh - 20
                run(["ffmpeg","-y","-i",str(temp_output),"-i",str(lip_path),
                    "-filter_complex",f"[1:v]scale={ow}:{oh}:force_original_aspect_ratio=decrease[ov];[0:v][ov]overlay={ox}:{oy}",
                    "-map","0:a","-c:a","copy","-preset","veryfast",str(pip_output)], check=True, timeout=120)
            temp_output = pip_output
            report(90, "口型视频合成完成")

    # 7. 字幕 — 纯白字淡入淡出，简单可靠
    mode_suffix = f"_{lip_sync_mode}_{aspect_ratio.replace(':', 'x')}" if lip_sync_video else ""
    final_output = OUTPUTS_DIR / f"final_{speech_path.stem}{mode_suffix}.mp4"
    if subtitle_enabled:
        report(90, "正在生成字幕...")
        sub_list = _split_text_to_subtitles(spoken_text, speech_duration)
        # 强制最后一条延伸到结尾
        if sub_list:
            sub_list[-1]["end"] = speech_duration
        if sub_list:
            vf = _build_drawtext_vf(sub_list, width, height, speech_duration)
            try:
                subprocess.run(["ffmpeg","-y","-i",str(temp_output),"-vf",vf,"-c:a","copy","-preset","veryfast",str(final_output)], check=True, timeout=300)
            except subprocess.CalledProcessError:
                shutil.move(str(temp_output), str(final_output))
        else:
            shutil.move(str(temp_output), str(final_output))
    else:
        shutil.move(str(temp_output), str(final_output))

    # 8. 片头片尾淡入淡出
    if speech_duration > 3:
        faded = OUTPUTS_DIR / f"faded_{speech_path.stem}{mode_suffix}.mp4"
        try:
            subprocess.run(["ffmpeg","-y","-i",str(final_output),
                "-vf",f"fade=in:0:25,fade=out:st={speech_duration-1:.2f}:d=1",
                "-c:a","copy","-preset","veryfast",str(faded)], check=True, timeout=120)
            final_output.unlink()
            shutil.move(str(faded), str(final_output))
        except subprocess.CalledProcessError:
            pass

    report(100, "视频生成完成")
    return final_output


def _build_karaoke_ass(subtitles: list[dict], width: int, height: int,
                       total_dur: float, spoken_text: str = "") -> Path | None:
    """生成卡拉OK字幕ASS文件：逐字高亮，跟着口播节奏走。

    优先用MiniMax的句子级时间戳，逐字均匀分配每个字的时间。
    屏幕最多2-3行，当前行高亮显示（黄色），已读完变灰色。
    返回 ASS 文件路径，失败返回 None。
    """
    from app.config import OUTPUTS_DIR

    if not subtitles:
        return None

    # 归一化时间戳
    norm_subs = _normalize_subtitles(subtitles)
    if not norm_subs:
        return None

    # 如果MiniMax只返回一大段，按句子拆分后均匀分配时间
    if len(norm_subs) == 1 and len(norm_subs[0]["text"]) > 30:
        raw = [s.strip() for s in re.split(r"[。！？\n]", norm_subs[0]["text"]) if s.strip()]
        if raw:
            full_start = norm_subs[0]["start"]
            full_end = norm_subs[0]["end"]
            dur_per = (full_end - full_start) / len(raw)
            norm_subs = [
                {"start": full_start + i * dur_per, "end": full_start + (i+1) * dur_per, "text": s}
                for i, s in enumerate(raw)
            ]

    # 与drawtext完全一致的保守参数，确保不出屏
    is_vertical = height > width
    if is_vertical:
        font_size = 38
        max_chars_per_line = 12
        max_lines = 2
    else:
        font_size = max(36, int(height * 0.028))
        max_chars_per_line = max(14, int((width - 120) / (font_size * 1.1)))
        max_lines = 3
    margin_v = int(height * 0.08)
    margin_h = 60
    line_height = int(font_size * 1.5)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Upper,Microsoft YaHei,{font_size},&H0000FFFF,&H00FFFF00,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,2,2,{margin_h},{margin_h},{margin_v},1
Style: Lower,Microsoft YaHei,{font_size},&H0000FFFF,&H00FFFF00,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,2,2,{margin_h},{margin_h},{margin_v+line_height},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 逐句处理：每句按字数均匀分配时间，\|k 标签实现逐字扫描
    events = []
    for sub in norm_subs:
        text = sub["text"]
        start = sub["start"]
        end = sub["end"]
        dur = max(end - start, 0.1)
        chars = list(text)

        # 按 max_chars_per_line 拆行，硬上限 max_lines 行
        raw_lines = _wrap_text(text, max_chars_per_line)
        if len(raw_lines) > max_lines:
            raw_lines = raw_lines[:max_lines]
            raw_lines[-1] = raw_lines[-1][:max_chars_per_line - 1] + "…"
        n_lines = len(raw_lines)
        chars_total = sum(len(L) for L in raw_lines)

        # 每行逐字扫描时长，以及扫完后留0.3s静置
        hold_cs = 30
        prev_karaoke_cs = 0  # 前几行已用的卡拉OK时间（cs）
        for li, line in enumerate(raw_lines):
            line_dur = dur * len(line) / chars_total if chars_total > 0 else dur / n_lines
            per_char_cs = max(1, int(line_dur * 100 / len(line))) if line else 10
            parts = []
            if li > 0 and prev_karaoke_cs > 0:
                # 下行延迟：等上行扫完再开始，用空格吸收延迟
                parts.append(f"{{\\k{prev_karaoke_cs}}} ")
            for ch in line:
                parts.append(f"{{\\k{per_char_cs}}}{_escape_ass(ch)}")
            prev_karaoke_cs += len(line) * per_char_cs
            events.append({
                "start": start, "end": end + hold_cs / 100.0,
                "style": "Upper" if li == 0 else "Lower",
                "text": "".join(parts),
            })

    # 末尾强制补齐：最后一条字幕延伸到视频结尾，不留空白
    if events:
        events[-1]["end"] = max(events[-1]["end"], total_dur)

    # 组装ASS内容
    ass_lines = [header]
    for ev in events:
        t = f"Dialogue: 0,{_ass_time(ev['start'])},{_ass_time(ev['end'])},{ev['style']},,0,0,0,,{ev['text']}"
        ass_lines.append(t)

    # 写入临时ASS文件
    import uuid
    ass_path = OUTPUTS_DIR / f"_karaoke_{uuid.uuid4().hex[:8]}.ass"
    ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
    return ass_path


def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape_ass(s: str) -> str:
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _normalize_subtitles(subtitles: list[dict]) -> list[dict]:
    result = []
    for sub in subtitles:
        start = sub.get("start_time", sub.get("start", sub.get("time_begin", 0)))
        end = sub.get("end_time", sub.get("end", sub.get("time_end", 0)))
        text = sub.get("text", sub.get("sentence", ""))
        if not text:
            continue
        if end > 100:  # MiniMax 毫秒值判断（只看结束时间）
            start /= 1000.0
            end /= 1000.0
        result.append({"start": float(start), "end": float(end), "text": str(text)})
    return result


def _split_text_to_subtitles(text: str, total_duration: float) -> list[dict]:
    """按句子拆分，短句自动合并（避免出现2-3个字的字幕）"""
    raw = [s.strip() for s in re.split(r"[。！？\n]", text) if s.strip()]
    if not raw:
        return [{"start": 0, "end": total_duration, "text": text.strip()}]

    MIN_CHARS = 6  # 每段最少字数，太短则合并到下一段
    merged = []
    buf = ""
    for s in raw:
        buf += s + "。"
        if len(buf) >= MIN_CHARS:
            merged.append(buf.rstrip("。"))
            buf = ""
    if buf.strip():
        merged.append(buf.rstrip("。"))

    dur_per = total_duration / len(merged)
    return [{"start": i * dur_per, "end": min((i+1) * dur_per, total_duration), "text": s}
            for i, s in enumerate(merged)]


def _escape_drawtext(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """每行不超过 max_chars"""
    if len(text) <= max_chars:
        return [text]
    lines = []
    for i in range(0, len(text), max_chars):
        lines.append(text[i:i + max_chars])
    return lines


def _build_drawtext_vf(subtitles: list[dict], width: int, height: int, total_dur: float = 999) -> str:
    """drawtext白字淡入淡出，简单可靠"""
    is_vertical = height > width
    if is_vertical:
        font_size = 38
        max_chars = 12
        max_lines = 2
    else:
        font_size = max(28, int(height * 0.035))
        max_chars = max(16, int(width * 0.85 / font_size))
        max_lines = 3

    fontfile = "C\\:/Windows/Fonts/simhei.ttf"
    line_height = int(font_size * 1.3)
    y_base = int(height * 0.78)
    pre_buffer = 0.0
    post_buffer = 0.10

    timed_segments = []
    for sub in subtitles:
        lines = _wrap_text(sub["text"], max_chars)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1][:max_chars - 1] + "…"
        seg_start = max(0, sub["start"] - pre_buffer)
        seg_end = min(sub["end"] + post_buffer, total_dur)
        timed_segments.append({"lines": lines, "start": seg_start, "end": seg_end})

    filters = []
    for seg in timed_segments:
        seg_lines = seg["lines"]
        start = seg["start"]
        end = seg["end"]
        dur = end - start
        n_lines = len(seg_lines)

        for li, line in enumerate(seg_lines):
            txt = _escape_drawtext(line)
            row_y = y_base + li * line_height - (n_lines - 1) * line_height // 2

            # 白字淡入淡出
            fade_dur = min(0.3, dur * 0.15) if dur > 0.4 else 0
            if fade_dur > 0:
                alpha_expr = f"if(lt(t-{start:.2f},{fade_dur:.2f}),(t-{start:.2f})/{fade_dur:.2f},if(lt(t,{end:.2f}-{fade_dur:.2f}),1,({end:.2f}-t)/{fade_dur:.2f}))"
                alpha_part = f"alpha='{alpha_expr}':"
            else:
                alpha_part = ""

            f = (
                f"drawtext=fontfile='{fontfile}':"
                f"text='{txt}':"
                f"fontsize={font_size}:"
                f"fontcolor=white:"
                f"borderw=3:bordercolor=black:"
                f"x=(w-tw)/2:"
                f"y={row_y}:"
                f"{alpha_part}"
                f"enable='between(t,{start:.2f},{end:.2f})'"
            )
            filters.append(f)

    return ",".join(filters)
    # 竖屏16字/行/3行（608px≈屏宽56%），横屏自适应
    is_vertical = height > width
    if is_vertical:
        font_size = 38
        max_chars = 16
        max_lines = 3
    else:
        font_size = max(28, int(height * 0.035))
        max_chars = max(20, int(width * 0.85 / font_size))
        max_lines = 3

    fontfile = "C\\:/Windows/Fonts/simhei.ttf"
    line_height = int(font_size * 1.3)
    y_base = int(height * 0.78)

    pre_buffer = 0.0
    post_buffer = 0.10
    timed_segments = []
    for sub in subtitles:
        text = sub["text"]
        lines = _wrap_text(text, max_chars)
        # 硬上限
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1][:max_chars - 1] + "…"

        seg_start = max(0, sub["start"] - pre_buffer)
        seg_end = min(sub["end"] + post_buffer, total_dur)
        timed_segments.append({"lines": lines, "start": seg_start, "end": seg_end})

    filters = []
    for seg in timed_segments:
        seg_lines = seg["lines"]
        start = seg["start"]
        end = seg["end"]
        dur = end - start
        fade_dur = min(0.3, dur * 0.2) if dur > 0.4 else 0
        n_lines = len(seg_lines)

        for li, line in enumerate(seg_lines):
            txt = _escape_drawtext(line)
            row_y = y_base + li * line_height - (n_lines - 1) * line_height // 2

            if fade_dur > 0:
                alpha_expr = f"if(lt(t-{start:.2f},{fade_dur:.2f}),(t-{start:.2f})/{fade_dur:.2f},if(lt(t,{end:.2f}-{fade_dur:.2f}),1,({end:.2f}-t)/{fade_dur:.2f}))"
                alpha_part = f"alpha='{alpha_expr}':"
            else:
                alpha_part = ""

            f = (
                f"drawtext=fontfile='{fontfile}':"
                f"text='{txt}':"
                f"fontsize={font_size}:"
                f"fontcolor=white:"
                f"borderw=3:"
                f"bordercolor=black:"
                f"shadowx=2:shadowy=2:shadowcolor=black@0.6:"
                f"x=(w-tw)/2:"
                f"y={row_y}:"
                f"{alpha_part}"
                f"enable='between(t,{start:.2f},{end:.2f})'"
            )
            filters.append(f)
    return ",".join(filters)
