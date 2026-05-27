"""智能剪辑服务：场景检测、节拍对齐、自动构图"""
import subprocess
import json
import tempfile
from pathlib import Path
import numpy as np


def detect_scenes(video_path: Path, threshold: float = 0.35) -> list[float]:
    """用 FFmpeg 场景检测，返回切分时间点列表（秒）"""
    result = subprocess.run([
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ], capture_output=True, text=True, timeout=60)
    times = [0.0]
    for line in result.stderr.split("\n"):
        if "pts_time:" in line:
            try:
                t = float(line.split("pts_time:")[1].split()[0])
                if t > 1.0:  # 跳过开头1秒内的小变化
                    times.append(t)
            except ValueError:
                pass
    return times


def detect_beats(audio_path: Path, min_interval: float = 0.4) -> list[float]:
    """用波形能量检测节拍点，返回节拍时间列表（秒）"""
    # 用 FFmpeg 提取单声道 8kHz 原始采样
    raw = tempfile.mktemp(suffix=".raw")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(audio_path),
            "-ac", "1", "-ar", "8000", "-f", "s16le", raw,
        ], capture_output=True, check=True, timeout=30)

        samples = np.fromfile(raw, dtype=np.int16).astype(np.float32)
        if len(samples) < 1000:
            return []

        # 分帧计算短时能量
        frame_size = 1600  # 200ms @ 8kHz
        hop = 800  # 100ms hop

        energy = []
        for i in range(0, len(samples) - frame_size, hop):
            frame = samples[i:i+frame_size]
            energy.append(np.sqrt(np.mean(frame ** 2)))
        energy = np.array(energy)
        if len(energy) < 3:
            return []

        # 归一化
        energy = (energy - np.mean(energy)) / max(np.std(energy), 1e-6)

        # 检测峰值（能量超过阈值且是局部最大）
        threshold = 0.5
        beats = []
        last_beat = -min_interval
        for i in range(1, len(energy) - 1):
            t = i * hop / 8000.0
            if (energy[i] > threshold and
                energy[i] > energy[i-1] and
                energy[i] > energy[i+1] and
                t - last_beat >= min_interval):
                beats.append(t)
                last_beat = t

        return beats
    except Exception as e:
        print(f"[editing] 节拍检测失败: {e}")
        return []
    finally:
        Path(raw).unlink(missing_ok=True)


def smart_segment_duration(segment_count: int, total_duration: float,
                           beat_times: list[float] | None = None) -> list[dict]:
    """智能分段时长：优先对齐节拍点，否则按黄金分割变速"""
    if segment_count <= 1:
        return [{"start": 0, "duration": total_duration}]

    # 有节拍信息时对齐节拍
    if beat_times and len(beat_times) >= segment_count:
        beats = [0] + [b for b in beat_times if b < total_duration] + [total_duration]
        segments = []
        for i in range(segment_count):
            start = segments[-1]["start"] + segments[-1]["duration"] if segments else 0
            # 找最近的节拍点作为切分点
            target = (i + 1) * total_duration / segment_count
            closest = min(beats, key=lambda b: abs(b - target))
            dur = max(1.5, min(8.0, closest - start))
            segments.append({"start": start, "duration": dur})
        return segments

    # 无节拍：变速节奏（短→长→短，更有节奏感）
    durations = []
    for i in range(segment_count):
        # 中间段稍长，首尾段稍短
        position = i / max(segment_count - 1, 1)
        weight = 0.8 + 0.4 * (1 - abs(position - 0.5) * 2)  # 0.8~1.2
        durations.append(weight)
    total_weight = sum(durations)
    return [{"start": sum(d[:i]) * total_duration / total_weight,
             "duration": d * total_duration / total_weight}
            for i, d in enumerate(durations)]


def auto_frame_to_vertical(video_path: Path, output_path: Path) -> Path:
    """自动构图到9:16竖屏（中心裁剪）"""
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0",
        "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ], capture_output=True, check=True, timeout=120)
    return output_path
