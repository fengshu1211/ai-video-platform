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
        "9:16": (720, 1280),
        "16:9": (1280, 720),
        "1:1": (720, 720),
    }
    width, height = RESOLUTIONS.get(aspect_ratio, (720, 1280))
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
        elif lip_sync_mode == "virtual_host":
            report(28, "正在生成虚拟主播...")
            # 单张照片→微动呼吸感（免费，无需GPU）
            lip_path_resolved = Path(lip_sync_video)
            if not lip_path_resolved.is_absolute():
                lip_path_resolved = OUTPUTS_DIR.parent / lip_sync_video
            if lip_path_resolved.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'):
                vh_output = OUTPUTS_DIR / f"virtualhost_{lip_path_resolved.stem}.mp4"
                from app.utils.ffmpeg_utils import generate_virtual_host_clip
                generate_virtual_host_clip(lip_path_resolved, vh_output, speech_duration, width, height)
                lip_sync_video = str(vh_output.relative_to(vh_output.parent.parent))
                report(32, "虚拟主播生成完成（免费）")
            else:
                report(32, "跳过：需要照片格式")

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

    # 最多8段素材（多了编码慢，边际效益低）
    use_mats = valid_mats[:8]
    seg_count = len(use_mats)
    per_dur = speech_duration / max(seg_count, 1)
    for i, mat_path in enumerate(use_mats):
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
            # 先尝试无损快切（不重新编码），失败则完整转码
            try:
                run(["ffmpeg","-y","-ss","0","-i",str(mat_path),
                    "-t",str(per_dur),"-an","-c","copy",
                    "-avoid_negative_ts","make_zero",str(trimmed)],
                    check=True, timeout=15)
            except Exception:
                run(["ffmpeg","-y","-i",str(mat_path),"-t",str(per_dur),"-an",
                    "-vf",f"{VIDEO_SCALE},fps=25,settb=1/25",
                    "-c:v","libx264","-preset","superfast","-pix_fmt","yuv420p",
                    "-r","25",str(trimmed)], check=True, timeout=60)
            material_clips.append(trimmed)

    if not material_clips:
        fallback = OUTPUTS_DIR / "_fallback.mp4"
        from subprocess import run
        run(["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x1a1a2e:s={width}x{height}:d={speech_duration}","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(fallback)], check=True, timeout=60)
        material_clips.append(fallback)

    # 硬切拼接（比xfade快5倍，2核服务器优先）
    merged_video = OUTPUTS_DIR / f"merged_{speech_path.stem}.mp4"
    if len(material_clips) > 1:
        concat_media(material_clips, merged_video)
    else:
        import shutil
        shutil.copy2(str(material_clips[0]), str(merged_video))

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
            if lip_sync_mode in ("full", "virtual_host"):
                # 全屏/虚拟主播：铺满画面，合成TTS音频
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
    # 字幕暂时关闭，直接输出
    shutil.move(str(temp_output), str(final_output))

    # 8. 片头片尾淡入淡出
    # 8. 美化：暗角+增艳+锐化+淡入淡出
    if speech_duration > 1:
        beautified = OUTPUTS_DIR / f"beauty_{speech_path.stem}{mode_suffix}.mp4"
        try:
            vf = (
                f"fade=in:0:25,"
                f"fade=out:st={speech_duration-1:.2f}:d=1,"
                f"vignette=PI/4,"
                f"eq=saturation=1.15:brightness=0.02:contrast=1.05,"
                f"unsharp=5:5:0.8:3:3:0.4"
            )
            subprocess.run(["ffmpeg","-y","-i",str(final_output),
                "-vf",vf,
                "-c:a","copy","-preset","veryfast",str(beautified)], check=True, timeout=120)
            final_output.unlink()
            shutil.move(str(beautified), str(final_output))
        except subprocess.CalledProcessError:
            pass

    report(100, "视频生成完成")
    return final_output


def _whisper_align_v2(audio_path: Path) -> list[dict] | None:
    """用本地 faster-whisper 获取逐词时间戳。不分文本长短，无网络超时。
    返回 [{"word": "明", "start": 1.23, "end": 1.45}, ...]，失败返回 None。
    """
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8",
                             download_root="/tmp/whisper")
        segments, _ = model.transcribe(
            str(audio_path), language="zh",
            word_timestamps=True, beam_size=5,
            vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300),
        )
        words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    w_text = w.word.strip()
                    if w_text:
                        words.append({
                            "word": w_text,
                            "start": w.start,
                            "end": w.end,
                        })
        print(f"[whisper] 对齐完成: {len(words)}字", flush=True)
        return words if words else None
    except Exception as e:
        print(f"[whisper_align] 失败: {e}", flush=True)
        return None


def _merge_word_timestamps(sub_list: list[dict], word_timings: list[dict]) -> list[dict]:
    """将词级时间戳按顺序分配给字幕句子。简单线性推进，不搞复杂匹配。"""
    if not word_timings:
        return sub_list

    wi = 0
    nw = len(word_timings)
    for sub in sub_list:
        text_clean = sub["text"].strip().replace("，", "").replace("。", "").replace("、", "").replace(" ", "").replace("\"", "").replace("\"", "").replace("\n", "")
        chars_needed = len(text_clean)
        sub_words = []
        chars_collected = 0
        start_wi = wi
        while wi < nw and chars_collected < chars_needed:
            w = word_timings[wi]
            w_text = w["word"].replace(" ", "")
            sub_words.append({"word": w["word"], "start": w["start"], "end": w["end"]})
            chars_collected += len(w_text)
            wi += 1
        # 如果最后一个词超出，回退
        if chars_collected > chars_needed + 2 and len(sub_words) > 1:
            sub_words = sub_words[:-1]
            wi -= 1
        if sub_words:
            sub["words"] = sub_words
    return sub_list


def _build_karaoke_ass(subtitles: list[dict], width: int, height: int,
                       total_dur: float, spoken_text: str = "",
                       subtitle_style: str = "golden_glow") -> Path | None:
    """生成简洁卡拉OK字幕ASS文件。单一样式，居中偏下，从上往下排列。"""
    from app.config import OUTPUTS_DIR

    if not subtitles:
        return None

    norm_subs = _normalize_subtitles(subtitles)
    if not norm_subs:
        return None

    # 合并过短字幕
    merged = []
    buf = ""
    buf_start = 0
    for s in norm_subs:
        if len(buf) + len(s["text"]) < 30:
            if not buf:
                buf_start = s["start"]
            buf += s["text"]
        else:
            if buf:
                merged.append({"start": buf_start, "end": s["start"], "text": buf})
            buf = ""
            merged.append(s)
    if buf:
        merged.append({"start": buf_start, "end": norm_subs[-1]["end"], "text": buf})
    if not merged:
        merged = norm_subs

    norm_subs = merged

    # 布局参数（竖屏720x1280）
    is_vertical = height > width
    if is_vertical:
        font_size = 46
        max_chars = 16
        max_lines = 3
    else:
        font_size = max(42, int(height * 0.036))
        max_chars = max(20, int(width / (font_size * 1.2)))
        max_lines = 3
    line_height = int(font_size * 1.4)
    # 底部留白，2行字幕的底边距
    bottom_margin = int(height * 0.12)
    # 上行距底部 = bottom_margin + line_height, 下行距底部 = bottom_margin
    upper_margin = bottom_margin + line_height
    lower_margin = bottom_margin

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Line1,Noto Sans CJK SC,{font_size},&H00FFFFFF,&H00668888,&H00000000,&H66000000,-1,0,0,0,100,100,0,0,1,4,3,2,60,60,{upper_margin},1
Style: Line2,Noto Sans CJK SC,{font_size},&H00FFFFFF,&H00668888,&H00000000,&H44000000,-1,0,0,0,100,100,0,0,1,3,2,2,60,60,{lower_margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for sub in norm_subs:
        text = sub["text"]
        start = sub["start"]
        end = sub["end"]
        dur = max(end - start, 0.3)
        words = sub.get("words")  # Paraformer词级时间戳（可选）

        lines = _wrap_text(text, max_chars)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1][:max_chars-1] + "..."

        # 逐字计时：仅第一行逐字高亮，其他行静态显示
        for li, line in enumerate(lines):
            parts = []
            if li == 0:
                # 第一行：\k 逐字高亮
                if words:
                    wi = 0
                    nw = len(words)
                    for ch in line:
                        if ch in "，。！？、；：""''（）…—":
                            parts.append(f"{{\\k1}}{_escape_ass(ch)}")
                            continue
                        found = False
                        for _ in range(min(3, max(1, nw - wi))):
                            if wi < nw and ch in words[wi]["word"]:
                                w = words[wi]
                                w_dur = max(w["end"] - w["start"], 0.02)
                                w_cs = max(1, int(w_dur * 100 / max(len(w["word"]), 1)))
                                parts.append(f"{{\\k{w_cs}}}{_escape_ass(ch)}")
                                found = True
                                break
                            wi += 1
                        if not found:
                            parts.append(f"{{\\k8}}{_escape_ass(ch)}")
                else:
                    per_char_cs = max(2, int(dur * 100 / max(len(line), 1)))
                    for ch in line:
                        parts.append(f"{{\\k{per_char_cs}}}{_escape_ass(ch)}")
            else:
                # 第二行起：静态显示（无 \k）
                parts = [_escape_ass(ch) for ch in line]

            events.append({
                "start": start,
                "end": end + 0.3,
                "style": "Line1" if li == 0 else "Line2",
                "text": "".join(parts),
            })

    if events:
        events[-1]["end"] = max(events[-1]["end"], total_dur)

    import uuid
    ass_lines = [header]
    for ev in events:
        ass_lines.append(
            f"Dialogue: 0,{_ass_time(ev['start'])},{_ass_time(ev['end'])}"
            f",{ev['style']},,0,0,0,,{ev['text']}"
        )
    ass_path = OUTPUTS_DIR / f"_karaoke_{uuid.uuid4().hex[:8]}.ass"
    ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
    return ass_path


def _ass_highlight_tag(style: str) -> str:
    """返回当前正在念的字的ASS特效标签"""
    if style == "gradient_bar":
        return "{\\bord5\\3c&HAA000000&\\c&H00FFFFFF&}"
    elif style == "pop_in":
        return "{\\fscx115\\fscy115\\c&H0044FF66&}"
    else:  # golden_glow / fade / default
        return "{\\blur2\\bord3\\c&H0044EEFF&}"


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

    # 按字数比例分配时间（中文约4字/秒），比平均分更准
    total_chars = sum(len(s) for s in merged)
    results = []
    t = 0.0
    for s in merged:
        d = total_duration * len(s) / max(total_chars, 1)
        results.append({"start": t, "end": t + d, "text": s})
        t += d
    return results


def _escape_drawtext(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("{", "\\{").replace("}", "\\}").replace("%", "\\%")


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

    import platform as _pf
    fontfile = "C\\:/Windows/Fonts/simhei.ttf" if _pf.system() == "Windows" else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
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
