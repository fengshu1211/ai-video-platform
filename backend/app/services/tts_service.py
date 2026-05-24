"""TTS语音合成 — 硅基流动CosyVoice（免费+声音复刻） + MiniMax兜底"""
import base64
import hashlib
from pathlib import Path
import requests
from app.config import AUDIO_DIR, SILICONFLOW_API_KEY

# 硅基流动 CosyVoice（主力，免费）
SF_TTS_URL = "https://api.siliconflow.cn/v1/audio/speech"
SF_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
SF_DEFAULT_VOICE = f"{SF_MODEL}:alex"

# MiniMax（兜底，付费）
MINIMAX_API_KEY = "sk-api-ZNMkMxUy-FT0Cp0Rmx9X9xNta5OdkRmapbwdammrJtzu3virBa6gEXI5BqH4oV72Mg7iWH3GCAjpYgIDqDAsr5ml8_KX1O6LJLFb7gJUrDVVXfoC44CeQLY"
MINIMAX_TTS_URL = "https://api.minimaxi.com/v1/t2a_v2"
MINIMAX_UPLOAD_URL = "https://api.minimaxi.com/v1/files/upload"
MINIMAX_CLONE_URL = "https://api.minimaxi.com/v1/voice_clone"

# 预置音色（Edge-TTS免费微软中文语音）
VOICE_LIST = [
    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓", "gender": "female", "style": "活泼甜美的少女声"},
    {"id": "zh-CN-XiaoyiNeural", "name": "晓伊", "gender": "female", "style": "温柔知性女声"},
    {"id": "zh-CN-YunxiNeural", "name": "云希", "gender": "male", "style": "温暖磁性的男声"},
    {"id": "zh-CN-YunjianNeural", "name": "云健", "gender": "male", "style": "沉稳有力的男声"},
    {"id": "zh-CN-YunyangNeural", "name": "云扬", "gender": "male", "style": "新闻播报风格"},
    {"id": "zh-CN-YunxiaNeural", "name": "云夏", "gender": "male", "style": "亲切自然的男声"},
    {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "晓北（东北话）", "gender": "female", "style": "东北方言女声"},
    {"id": "zh-CN-shaanxi-XiaoniNeural", "name": "晓妮（陕西话）", "gender": "female", "style": "陕西方言女声"},
]
# 兼容旧导入
MINIMAX_VOICES = VOICE_LIST


def clone_voice(audio_path: Path, voice_name: str) -> str | None:
    """语音复刻：优先MiniMax（持久化voice_id），失败则返回None（TTS时用base64）"""
    # MiniMax正式复刻
    try:
        with open(audio_path, "rb") as f:
            resp = requests.post(MINIMAX_UPLOAD_URL,
                headers={"Authorization": f"Bearer {MINIMAX_API_KEY}"},
                data={"purpose": "voice_clone"},
                files={"file": (audio_path.name, f, "audio/mpeg")},
                timeout=60)
        if resp.status_code == 200:
            file_id = resp.json().get("file", {}).get("file_id", 0)
            if file_id:
                resp2 = requests.post(MINIMAX_CLONE_URL,
                    headers={"Authorization": f"Bearer {MINIMAX_API_KEY}", "Content-Type": "application/json"},
                    json={"file_id": file_id, "voice_id": voice_name,
                          "need_noise_reduction": False, "need_volume_normalization": True,
                          "language_boost": "Chinese"},
                    timeout=120)
                if resp2.json().get("base_resp", {}).get("status_code") == 0:
                    print(f"MiniMax voice cloned: {voice_name}")
                    return voice_name
    except Exception as e:
        print(f"MiniMax clone failed: {e}")

    # MiniMax失败则返回特殊标记，TTS时用CosyVoice base64复刻
    print(f"MiniMax clone unavailable, will use CosyVoice inline cloning")
    return None


def text_to_speech(text: str, voice: str = "alex",
                   reference_sample: str | None = None,
                   return_subtitles: bool = False) -> Path | tuple[Path, list[dict]]:
    """文字转语音。CosyVoice主力（免费），MiniMax兜底"""

    # 解析参考音频
    ref_b64 = None
    if reference_sample:
        ref_path = Path(reference_sample)
        if not ref_path.is_absolute():
            ref_path = AUDIO_DIR.parent / reference_sample
        if ref_path.exists():
            ref_b64 = base64.b64encode(ref_path.read_bytes()).decode()

    ref_tag = hashlib.md5(ref_b64.encode()).hexdigest()[:8] if ref_b64 else ""
    cache_hash = hashlib.md5(f"cosy|{text}|{voice}|{ref_tag}".encode()).hexdigest()
    cache_path = AUDIO_DIR / f"tts_{cache_hash}.mp3"
    if cache_path.exists():
        return cache_path if not return_subtitles else (cache_path, [])

    subtitles = []

    # ── 有参考音频 → CosyVoice复刻（免费）──
    if ref_b64:
        try:
            body = {
                "model": SF_MODEL,
                "input": text,
                "voice": f"{SF_MODEL}:alex",
                "response_format": "mp3",
                "reference_audio": ref_b64,
            }
            r = requests.post(SF_TTS_URL,
                headers={"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"},
                json=body, timeout=90)
            if r.status_code == 200 and len(r.content) > 100:
                cache_path.write_bytes(r.content)
                return cache_path if not return_subtitles else (cache_path, subtitles)
            print(f"CosyVoice clone failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"CosyVoice clone error: {e}")

    # ── 预设音色 → Edge-TTS（微软免费，8种中文语音）──
    edge_voice = voice if voice.startswith("zh-CN") else "zh-CN-YunxiNeural"
    try:
        import subprocess, tempfile
        tmp_mp3 = tempfile.mktemp(suffix=".mp3")
        result = subprocess.run([
            "edge-tts", "--voice", edge_voice, "--text", text,
            "--write-media", tmp_mp3,
        ], capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and Path(tmp_mp3).exists():
            data = Path(tmp_mp3).read_bytes()
            Path(tmp_mp3).unlink(missing_ok=True)
            cache_path.write_bytes(data)
            return cache_path if not return_subtitles else (cache_path, subtitles)
        Path(tmp_mp3).unlink(missing_ok=True)
        print(f"Edge-TTS failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"Edge-TTS error: {e}")

    # 全失败：抛异常
    raise RuntimeError(f"TTS failed for text: {text[:50]}...")
