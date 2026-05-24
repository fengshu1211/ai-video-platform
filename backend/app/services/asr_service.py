"""语音识别 — 硅基流动 SenseVoiceSmall"""
import httpx
from pathlib import Path
from app.config import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL


def transcribe_audio(audio_path: Path) -> str:
    """将音频文件转写为文本（用于声音克隆的参考文本）"""
    with open(audio_path, "rb") as f:
        resp = httpx.post(
            f"{SILICONFLOW_BASE_URL}/audio/transcriptions",
            headers={"Authorization": f"Bearer {SILICONFLOW_API_KEY}"},
            files={"file": (audio_path.name, f, "audio/mpeg")},
            data={"model": "FunAudioLLM/SenseVoiceSmall"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
