"""GPU服务 — Wav2Lip对口型 + SadTalker数字人"""
import httpx
from pathlib import Path
from app.config import (
    OUTPUTS_DIR,
    WAV2LIP_API,
    SADTALKER_API,
    GPU_SSH_HOST,
    GPU_SSH_PORT,
    GPU_SSH_USER,
    GPU_SSH_PASSWORD,
)


def process_sadtalker(photo_path: Path, audio_path: Path, output_path: Path | None = None) -> Path | None:
    """SadTalker：照片+音频→数字人说话视频"""
    if not output_path:
        output_path = OUTPUTS_DIR / f"sadtalker_{photo_path.stem}_{audio_path.stem}.mp4"
    try:
        with open(photo_path, "rb") as pf, open(audio_path, "rb") as af:
            resp = httpx.post(f"{SADTALKER_API}/process",
                files={"photo": (photo_path.name, pf), "audio": (audio_path.name, af)},
                timeout=600)
        if resp.status_code == 200:
            output_path.write_bytes(resp.content)
            return output_path
    except Exception as e:
        print(f"SadTalker error: {e}")
    return None


def process_lip_sync(video_path: Path, audio_path: Path, output_path: Path | None = None) -> Path | None:
    """调用Wav2Lip API进行口型同步，完成后自动关GPU"""
    if not output_path:
        output_path = OUTPUTS_DIR / f"lipsync_{video_path.stem}_{audio_path.stem}.mp4"

    try:
        with open(video_path, "rb") as vf, open(audio_path, "rb") as af:
            resp = httpx.post(f"{WAV2LIP_API}/process",
                files={"video": (video_path.name, vf), "audio": (audio_path.name, af)},
                timeout=600
            )
        if resp.status_code == 200:
            output_path.write_bytes(resp.content)
            # 处理完自动关GPU省电
            _auto_shutdown_gpu()
            return output_path
    except Exception as e:
        print(f"Wav2Lip error: {e}")
    return None


def _auto_shutdown_gpu():
    """通过SSH自动关闭GPU实例"""
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            GPU_SSH_HOST,
            port=GPU_SSH_PORT,
            username=GPU_SSH_USER,
            password=GPU_SSH_PASSWORD,
            timeout=5,
        )
        ssh.exec_command("shutdown -h now 2>/dev/null &", timeout=5)
        ssh.close()
    except Exception:
        pass


def is_available() -> bool:
    """检查Wav2Lip GPU服务是否可用"""
    try:
        r = httpx.get(f"{WAV2LIP_API}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False
