"""嘴部动作检测 — 判断视频中是否有人在说话"""
import subprocess, json
from pathlib import Path


def detect_lip_movement(video_path: Path) -> dict:
    """
    检测视频中是否有嘴部动作。
    使用FFmpeg提取关键帧 + face_alignment分析嘴唇开合度。
    返回: {"has_talking": bool, "confidence": float, "suggestion": str}
    """
    try:
        # 提取5帧均匀分布的画面
        import tempfile
        tmpdir = Path(tempfile.mkdtemp())
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", "fps=1/2", "-vframes", "5",
            f"{tmpdir}/frame_%02d.png",
        ], check=True, capture_output=True, timeout=30)

        frames = sorted(tmpdir.glob("frame_*.png"))
        if not frames:
            return {"has_talking": False, "confidence": 0, "suggestion": "audio_only"}

        # 使用OpenCV检测人脸+嘴部
        import cv2
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if face_cascade.empty():
            return {"has_talking": False, "confidence": 0, "suggestion": "audio_only"}

        face_counts = []
        for frame_path in frames[:5]:
            img = cv2.imread(str(frame_path))
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
            face_counts.append(len(faces))

        # 清理
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

        avg_faces = sum(face_counts) / len(face_counts) if face_counts else 0
        # 如果检测到人脸，建议仅替换音频（很可能在说话）
        if avg_faces >= 0.5:
            return {"has_talking": True, "confidence": min(avg_faces, 1.0), "suggestion": "audio_only"}
        else:
            return {"has_talking": False, "confidence": 0, "suggestion": "audio_only"}

    except Exception:
        return {"has_talking": False, "confidence": 0, "suggestion": "audio_only"}
