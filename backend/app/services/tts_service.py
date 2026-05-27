"""TTS语音合成 — 硅基流动CosyVoice（免费声音复刻）+ Edge-TTS（免费预设）"""
import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
import requests
from app.config import AUDIO_DIR, SILICONFLOW_API_KEY

SF_TTS_URL = "https://api.siliconflow.cn/v1/audio/speech"
SF_UPLOAD_URL = "https://api.siliconflow.cn/v1/uploads/audio/voice"
SF_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
SF_VOICE_CACHE = AUDIO_DIR.parent / "sf_voice_cache.json"

MINIMAX_API_KEY = "sk-api-ZNMkMxUy-FT0Cp0Rmx9X9xNta5OdkRmapbwdammrJtzu3virBa6gEXI5BqH4oV72Mg7iWH3GCAjpYgIDqDAsr5ml8_KX1O6LJLFb7gJUrDVVXfoC44CeQLY"
MINIMAX_TTS_URL = "https://api.minimaxi.com/v1/t2a_v2"
MINIMAX_UPLOAD_URL = "https://api.minimaxi.com/v1/files/upload"
MINIMAX_CLONE_URL = "https://api.minimaxi.com/v1/voice_clone"

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
MINIMAX_VOICES = VOICE_LIST


def _parse_srt(srt_path: str) -> list[dict]:
    """解析SRT字幕文件，返回 [{\"start\": 1.2, \"end\": 3.5, \"text\": \"...\"}, ...]"""
    import re
    subtitles = []
    try:
        content = Path(srt_path).read_text(encoding="utf-8")
        blocks = content.strip().split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                time_match = re.match(r"(\d+:\d+:\d+[\.,]\d+)\s*-->\s*(\d+:\d+:\d+[\.,]\d+)", lines[1])
                if time_match:
                    def _to_sec(t):
                        t = t.replace(",", ".")
                        h, m, s = t.split(":")
                        return int(h) * 3600 + int(m) * 60 + float(s)
                    start = _to_sec(time_match.group(1))
                    end = _to_sec(time_match.group(2))
                    text = "".join(lines[2:]).strip()
                    if text:
                        subtitles.append({"start": start, "end": end, "text": text})
    except Exception as e:
        print(f"SRT parse failed: {e}")
    return subtitles


def _load_voice_cache() -> dict:
    """加载声音URI缓存"""
    if SF_VOICE_CACHE.exists():
        try:
            return json.loads(SF_VOICE_CACHE.read_text())
        except Exception:
            return {}
    return {}


def _save_voice_cache(cache: dict):
    SF_VOICE_CACHE.write_text(json.dumps(cache, ensure_ascii=False))


def _preprocess_audio(input_path: Path) -> Path:
    """预处理参考音频：降噪→16kHz单声道→去静音→音量归一化"""
    output_path = input_path.with_suffix(".wav")
    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(input_path),
            "-af", "afftdn,highpass=f=80,lowpass=f=8000,silenceremove=start_periods=1:stop_periods=-1:stop_threshold=-35dB,loudnorm",
            "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
            str(output_path),
        ], capture_output=True, text=True, timeout=60)
        if output_path.exists() and output_path.stat().st_size > 1000:
            return output_path
    except Exception as e:
        print(f"Audio preprocessing failed: {e}")
    return input_path


def _upload_voice_to_siliconflow(audio_path: Path, voice_name: str, ref_text: str = "", sf_api_key: str = "") -> str | None:
    """上传参考音频到硅基流动，注册自定义声音，返回voice URI。

    使用硅基流动的 /v1/uploads/audio/voice 接口，
    上传后获得 voice URI 如 speech:name:id:hash，后续TTS直接用此URI。
    sf_api_key 优先于系统环境变量，支持多用户各自配置Key。
    """
    api_key = sf_api_key or SILICONFLOW_API_KEY
    if not api_key or len(api_key) < 10:
        print("SiliconFlow API Key not configured, skipping voice registration")
        return None

    # 预处理音频
    cleaned = _preprocess_audio(audio_path)

    try:
        audio_b64 = base64.b64encode(cleaned.read_bytes()).decode()
        data_uri = f"data:audio/wav;base64,{audio_b64}"

        body = {
            "model": SF_MODEL,
            "customName": voice_name,
            "audio": data_uri,
        }
        if ref_text:
            body["text"] = ref_text
        else:
            body["text"] = "这是一段用于声音复刻的参考音频，用于提取说话人的音色特征"

        r = requests.post(SF_UPLOAD_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body, timeout=120)
        if r.status_code == 200:
            result = r.json()
            uri = result.get("uri") or result.get("voice") or result.get("voice_uri")
            if uri:
                print(f"SiliconFlow voice registered: {voice_name} -> {uri[:50]}...")
                return uri
            print(f"Upload response missing URI: {json.dumps(result, ensure_ascii=False)[:300]}")
        else:
            print(f"SiliconFlow upload failed: {r.status_code} {r.text[:300]}")

    except Exception as e:
        print(f"SiliconFlow upload error: {e}")

    finally:
        # 清理预处理文件
        if cleaned != audio_path and cleaned.exists():
            cleaned.unlink(missing_ok=True)

    return None


def _get_or_create_sf_voice(audio_path: Path, voice_name: str, ref_text: str = "", sf_api_key: str = "") -> str | None:
    """获取或创建硅基流动自定义声音URI（带缓存）"""
    cache = _load_voice_cache()

    # 用音频hash+key做缓存key（不同用户的同音频对应不同URI）
    audio_hash = hashlib.md5(audio_path.read_bytes()).hexdigest()[:16]
    key_tag = hashlib.md5((sf_api_key or SILICONFLOW_API_KEY).encode()).hexdigest()[:6]
    cache_key = f"{voice_name}_{audio_hash}_{key_tag}"

    if cache_key in cache:
        cached_uri = cache[cache_key]
        print(f"Using cached SF voice: {cached_uri[:50]}...")
        return cached_uri

    uri = _upload_voice_to_siliconflow(audio_path, voice_name, ref_text, sf_api_key)
    if uri:
        cache[cache_key] = uri
        if len(cache) > 20:
            oldest = list(cache.keys())[0]
            del cache[oldest]
        _save_voice_cache(cache)
    return uri


def clone_voice(audio_path: Path, voice_name: str, sf_api_key: str = "") -> str | None:
    """语音复刻：优先硅基流动CosyVoice（免费），失败降级MiniMax"""
    # 读取参考文本（ASR转写结果）
    ref_text = ""
    ref_text_path = audio_path.with_suffix(".txt")
    if ref_text_path.exists():
        try:
            ref_text = ref_text_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # 硅基流动CosyVoice（首选，免费）
    uri = _get_or_create_sf_voice(audio_path, voice_name, ref_text, sf_api_key)
    if uri:
        return uri

    # MiniMax兜底
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
                          "need_noise_reduction": True, "need_volume_normalization": True,
                          "language_boost": "Chinese"},
                    timeout=120)
                if resp2.json().get("base_resp", {}).get("status_code") == 0:
                    return voice_name
    except Exception as e:
        print(f"MiniMax clone failed: {e}")

    return None


def text_to_speech(text: str, voice: str = "alex",
                   reference_sample: str | None = None,
                   return_subtitles: bool = False,
                   sf_api_key: str = "") -> Path | tuple[Path, list[dict]]:
    """文字转语音。CosyVoice自定义声音 > Edge-TTS预设音色。
    sf_api_key 可传入用户自己的硅基Key（来自请求头），优先于系统Key。"""

    # 解析参考音频路径
    ref_path = None
    if reference_sample:
        ref_path = Path(reference_sample)
        if not ref_path.is_absolute():
            ref_path = AUDIO_DIR.parent / reference_sample

    # 缓存key
    ref_tag = ""
    if ref_path and ref_path.exists():
        ref_tag = hashlib.md5(ref_path.read_bytes()).hexdigest()[:8]
    cache_hash = hashlib.md5(f"cosy|{text}|{voice}|{ref_tag}".encode()).hexdigest()
    cache_path = AUDIO_DIR / f"tts_{cache_hash}.mp3"
    if cache_path.exists():
        return cache_path if not return_subtitles else (cache_path, [])

    subtitles = []

    # ── 自定义声音：voice是硅基流动URI → 直接用 ──
    if voice.startswith("speech:") or voice.startswith("cosyvoice:"):
        _key = sf_api_key or SILICONFLOW_API_KEY
        if _key and len(_key) >= 10:
            try:
                body = {
                    "model": SF_MODEL,
                    "input": text,
                    "voice": voice,
                    "response_format": "mp3",
                    "speed": 1.0,
                }
                r = requests.post(SF_TTS_URL,
                    headers={"Authorization": f"Bearer {_key}", "Content-Type": "application/json"},
                    json=body, timeout=90)
                if r.status_code == 200 and len(r.content) > 100:
                    cache_path.write_bytes(r.content)
                    return cache_path if not return_subtitles else (cache_path, subtitles)
                print(f"SF voice TTS failed: {r.status_code} {r.text[:200]}")
            except Exception as e:
                print(f"SF voice TTS error: {e}")
        else:
            print("SiliconFlow API Key not configured, cannot use custom voice")

    # ── 有参考音频但voice不是URI → 尝试即时复刻 ──
    if ref_path and ref_path.exists() and not voice.startswith("speech:"):
        # 尝试用参考音频即时合成（inline reference_audio，可能不被硅基支持）
        _key2 = sf_api_key or SILICONFLOW_API_KEY
        if _key2 and len(_key2) >= 10:
            try:
                ref_b64 = base64.b64encode(ref_path.read_bytes()).decode()
                body = {
                    "model": SF_MODEL,
                    "input": text,
                    "voice": f"{SF_MODEL}:alex",
                    "response_format": "mp3",
                    "reference_audio": ref_b64,
                }
                r = requests.post(SF_TTS_URL,
                    headers={"Authorization": f"Bearer {_key2}", "Content-Type": "application/json"},
                    json=body, timeout=90)
                if r.status_code == 200 and len(r.content) > 100:
                    cache_path.write_bytes(r.content)
                    return cache_path if not return_subtitles else (cache_path, subtitles)
                print(f"CosyVoice inline clone failed: {r.status_code} {r.text[:200]}")
            except Exception as e:
                print(f"CosyVoice inline clone error: {e}")

    # ── 预设音色 → Edge-TTS（微软免费，自带文本对齐）──
    edge_voice = voice if voice.startswith("zh-CN") else "zh-CN-YunxiNeural"
    try:
        tmp_mp3 = tempfile.mktemp(suffix=".mp3")
        tmp_srt = tempfile.mktemp(suffix=".srt")
        result = subprocess.run([
            "edge-tts", "--voice", edge_voice, "--text", text,
            "--write-media", tmp_mp3,
            "--write-subtitles", tmp_srt,
        ], capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and Path(tmp_mp3).exists():
            data = Path(tmp_mp3).read_bytes()
            Path(tmp_mp3).unlink(missing_ok=True)

            # 解析SRT字幕
            srt_data = _parse_srt(tmp_srt) if Path(tmp_srt).exists() else []
            Path(tmp_srt).unlink(missing_ok=True)

            if return_subtitles and srt_data:
                subtitles = srt_data

            cache_path.write_bytes(data)
            return cache_path if not return_subtitles else (cache_path, subtitles)
        Path(tmp_mp3).unlink(missing_ok=True)
        Path(tmp_srt).unlink(missing_ok=True)
        print(f"Edge-TTS failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"Edge-TTS error: {e}")

    raise RuntimeError(f"TTS failed for text: {text[:50]}...")
