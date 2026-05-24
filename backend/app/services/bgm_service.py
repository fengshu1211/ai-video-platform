"""BGM自动匹配 — 根据内容情绪选择背景音乐"""
# 情绪到BGM的映射（后续可替换为真实BGM文件路径）
MOOD_BGM_MAP = {
    "epic": None,       # 史诗 → 待用户上传或联网获取
    "warm": None,       # 温暖
    "sad": None,        # 悲伤
    "inspiring": None,  # 激昂
    "calm": None,       # 平静
    "suspense": None,   # 悬疑
}

# BGM文件名模板（用户上传的BGM命名规则：bgm_史诗.mp3, bgm_温暖.mp3 等）
BGM_PREFIX = "bgm_"


def get_bgm_for_mood(mood: str, bgm_dir: str | None = None) -> str | None:
    """根据情绪返回匹配的BGM路径，没有则返回None（不配BGM）"""
    if not bgm_dir:
        from app.config import AUDIO_DIR
        bgm_dir = str(AUDIO_DIR)

    import os
    # 按文件名匹配：bgm_史诗.mp3, bgm_激昂.mp3 等
    mood_to_filename = {
        "epic": ["bgm_史诗", "bgm_epic", "bgm_宏大"],
        "warm": ["bgm_温暖", "bgm_warm", "bgm_温馨"],
        "sad": ["bgm_悲伤", "bgm_sad", "bgm_伤感"],
        "inspiring": ["bgm_激昂", "bgm_inspiring", "bgm_激励"],
        "calm": ["bgm_平静", "bgm_calm", "bgm_宁静"],
        "suspense": ["bgm_悬疑", "bgm_suspense", "bgm_紧张"],
    }

    candidates = mood_to_filename.get(mood, [])
    for ext in (".mp3", ".wav", ".m4a", ".ogg"):
        for name in candidates:
            path = os.path.join(bgm_dir, name + ext)
            if os.path.exists(path):
                return path

    return None


def list_bgm_files(bgm_dir: str | None = None) -> list[str]:
    """列出可用的BGM文件"""
    if not bgm_dir:
        from app.config import AUDIO_DIR
        bgm_dir = str(AUDIO_DIR)

    import os
    files = []
    if os.path.exists(bgm_dir):
        for f in os.listdir(bgm_dir):
            if f.startswith("bgm_") and f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg")):
                files.append(f)
    return files
