"""全局配置"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"

# 上传子目录
IMAGES_DIR = UPLOADS_DIR / "images"
AUDIO_DIR = UPLOADS_DIR / "audio"
VIDEOS_DIR = UPLOADS_DIR / "videos"
VOICES_DIR = UPLOADS_DIR / "voices"
OUTPUTS_DIR = UPLOADS_DIR / "outputs"

# 确保目录存在
for d in [IMAGES_DIR, AUDIO_DIR, VIDEOS_DIR, VOICES_DIR, OUTPUTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 数据库
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data.db'}?journal_mode=WAL")

# Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# AI API（通义千问，兼容OpenAI格式）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# AutoDL GPU算力云
AUTODL_TOKEN = os.getenv("AUTODL_TOKEN", "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOjk5NTMxMywidXVpZCI6IjYzODQzMGJkZTk2YmExZTUiLCJ0ZW5hbnQiOiJhdXRvZGwiLCJhdWQiOiJkZXZlbG9wX2FwaSJ9.-LyD53JK4-NU_HPk0IHaNdEZulBG4szioA1ipAuE4WeBkx5OlFA_9i17Wpxn8JtveJzAnjqIUZk41E2HhVuR7g")
AUTODL_API_BASE = "https://private.autodl.com"

# TTS配置（硅基流动）—— 用户通过前端设置页传入自己的Key
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
TTS_MODEL = "FunAudioLLM/CosyVoice2-0.5B"
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "siliconflow")

# ── 用户自定义Key（通过请求头传入，优先于默认值）──
def get_user_api_keys(request=None) -> dict:
    """从请求头提取用户自己的API Key，优先于系统默认值"""
    keys = {
        "dashscope": DASHSCOPE_API_KEY,
        "siliconflow": SILICONFLOW_API_KEY,
    }
    if request:
        for key, header in [("dashscope", "X-DashScope-Key"), ("siliconflow", "X-SiliconFlow-Key")]:
            val = request.headers.get(header, "").strip()
            if val and len(val) > 10:
                keys[key] = val
    return keys

# GPU 服务（Wav2Lip / SadTalker）——换实例时改这里
WAV2LIP_API = os.getenv("WAV2LIP_API", "http://localhost:8080")
SADTALKER_API = os.getenv("SADTALKER_API", "http://localhost:8090")

# AutoDL SSH（处理完自动关 GPU 省电）
GPU_SSH_HOST = os.getenv("GPU_SSH_HOST", "connect.bjb2.seetacloud.com")
GPU_SSH_PORT = int(os.getenv("GPU_SSH_PORT", "22593"))
GPU_SSH_USER = os.getenv("GPU_SSH_USER", "root")
GPU_SSH_PASSWORD = os.getenv("GPU_SSH_PASSWORD", "JiZzn2ma6Iic")

# CORS
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://localhost:8000"]
