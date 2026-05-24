"""AI文本改写 — 通义千问（DashScope OpenAI兼容接口）"""
import hashlib
import os
import time
from openai import OpenAI
from app.config import DASHSCOPE_BASE_URL

def _get_client():
    """获取OpenAI客户端（优先用用户Key）"""
    try:
        from app.main import get_user_key
        key = get_user_key("dashscope") or os.getenv("DASHSCOPE_API_KEY", "")
    except Exception:
        key = os.getenv("DASHSCOPE_API_KEY", "")
    if not key:
        raise RuntimeError("请先在系统设置中配置通义千问 API Key")
    return OpenAI(api_key=key, base_url=DASHSCOPE_BASE_URL)

# 简单内存缓存：key → (expire_time, result)
_cache: dict[str, tuple[float, str]] = {}


def _cache_key(text: str, style: str) -> str:
    return hashlib.md5(f"{text}|{style}".encode()).hexdigest()


def _get_cached(text: str, style: str) -> str | None:
    key = _cache_key(text, style)
    entry = _cache.get(key)
    if entry:
        expire, result = entry
        if time.time() < expire:
            return result
        del _cache[key]
    return None


def _set_cache(text: str, style: str, result: str, ttl: int = 1800):
    key = _cache_key(text, style)
    _cache[key] = (time.time() + ttl, result)


STYLE_PROMPTS = {
    "similar": "请改写以下文案，保持原意和核心观点不变，调整表达方式、更换部分词汇和句式，使内容具有新鲜感。直接输出改写后的文案，不要加任何解释。",
    "original": "请对以下文案进行创意改写，可以大幅调整结构和表达方式，但保留核心信息点。加入更生动的描述，使其读起来像原创内容。直接输出改写后的文案，不要加任何解释。",
    "aggressive": "请对以下文案进行激进改写，仅保留核心事实和关键信息点，完全重新组织语言和结构，换一种全新的表达风格。可以使用不同的叙事角度。直接输出改写后的文案，不要加任何解释。",
}


def generate_titles(text: str, count: int = 5) -> list[str]:
    """为文案生成爆款标题"""
    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "你是爆款标题专家。根据文案内容生成多个吸引眼球的标题，每个标题≤30字。输出JSON数组：[\"标题1\",\"标题2\",...]"},
            {"role": "user", "content": f"根据以下内容生成{count}个爆款标题：\n{text[:1500]}"},
        ],
        temperature=0.9, max_tokens=500,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    import json
    return json.loads(raw)


def rewrite_text(text: str, style: str = "similar", target_word_count: int | None = None) -> str:
    """AI改写文案，style: similar/original/aggressive，支持目标字数"""
    cache_key = f"{text}|{style}|{target_word_count or ''}"
    cached = _get_cached(cache_key, "rewrite")
    if cached:
        return cached

    prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["similar"])
    if target_word_count and target_word_count > 0:
        prompt += f" 请控制改写后的字数在 {target_word_count} 字左右，可以适当浮动 ±10%。"

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "你是一个专业自媒体文案改写助手，擅长在不改变核心意思的前提下优化文案表达。"},
            {"role": "user", "content": f"{prompt}\n\n原文案：\n{text}"},
        ],
        temperature=0.8,
        max_tokens=2048,
    )

    result = response.choices[0].message.content.strip()
    _set_cache(cache_key, "rewrite", result)
    return result


def analyze_persona_style(persona_data: dict) -> dict:
    """AI分析用户人设，生成专属内容风格模板"""
    import json

    prompt = f"""你是一个内容风格分析师。根据以下用户信息，分析并生成该用户的专属内容创作风格模板。

用户信息：
- 行业：{persona_data.get('industry', '未填写')}
- 角色/职位：{persona_data.get('role', '未填写')}
- 性格：{persona_data.get('personality', '未填写')}
- 兴趣爱好：{persona_data.get('hobbies', '未填写')}
- 内容风格偏好：{persona_data.get('content_style', '未填写')}
- 目标受众：{persona_data.get('target_audience', '未填写')}

请输出JSON格式：
{{
  "style_name": "给这个风格起个名字（如：幽默科普风、沉稳专业风）",
  "tone": "语气描述（如：亲切口语化、严肃学术化）",
  "sentence_length": "句子长度偏好（短句快节奏/中长句娓道来/长短结合）",
  "openings": ["3种适合该用户的开头方式"],
  "closings": ["3种适合该用户的结尾方式"],
  "transition_phrases": ["5个该用户风格的过渡金句"],
  "taboo_words": ["该用户应避免的词汇或表达"],
  "keywords": ["6-8个该用户内容领域的核心关键词"],
  "writing_tips": "给该用户的3条内容创作建议",
  "ideal_video_duration": "适合的视频时长（秒）"
}}

只输出JSON。"""

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "system", "content": "你是内容风格分析师，擅长根据用户特征生成专属内容创作模板。只输出JSON。"},
                  {"role": "user", "content": prompt}],
        temperature=0.5, max_tokens=800,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(raw)


def extract_keywords_and_mood(text: str) -> dict:
    """从文案中提取搜索关键词和内容情绪，用于自动匹配素材和BGM"""
    import json

    cached = _get_cached(text, "keywords")
    if cached:
        return json.loads(cached)

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": """你是一个视频素材匹配助手。仔细分析文案内容，提取能精准匹配视频素材的搜索关键词。
输出JSON格式：
{
  "keywords_en": ["k1", "k2", "k3", "k4", "k5"],
  "keywords_cn": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
  "mood": "epic/warm/sad/inspiring/calm/suspense",
  "mood_cn": "史诗/温暖/悲伤/激昂/平静/悬疑",
  "scene_type": "landscape/historical/abstract/nature/urban/people/technology"
}
要求：
- keywords_en用英文具体名词（如 ancient china, battlefield, dynasty），不要抽象词，利于搜索视频素材
- keywords_cn用中文具体词
- 关键词要覆盖文案中的核心场景、人物、地点、氛围元素
- 只输出JSON，不要其他内容。"""},
            {"role": "user", "content": f"分析这段文案：\n{text[:500]}"},
        ],
        temperature=0.3,
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()
    # 清理可能的markdown包裹
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    result = json.loads(raw)
    _set_cache(text, "keywords", json.dumps(result, ensure_ascii=False))
    return result


def plan_visual_materials(text: str) -> dict:
    """AI导演分镜：吃透全文→规划每个视觉段落的素材方案

    返回:
    {
      "overall_theme": "主题",
      "mood": "情绪",
      "segments": [
        {
          "text_ref": "对应文案开头几字",
          "visual_desc": "detailed English visual description for AI image generation",
          "source": "ai_image" | "video_search",
          "keywords_cn": ["搜索关键词"],
          "keywords_en": ["search keywords"]
        },
        ...
      ]
    }
    """
    import json

    cached = _get_cached(text, "visual_plan")
    if cached:
        return json.loads(cached)

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": """你是视频导演。请仔细阅读口播文案，理解主题、情绪和叙事结构，然后为文案规划视觉素材方案。

步骤：
1. 先通读全文，理解：这是什么主题？什么年代/场景？有哪些核心视觉元素？情绪的起承转合？
2. 把文案分成5-8个视觉段落，每个段落需要不同的素材
3. 对每个段落判断：如果是古代/历史/奇幻/抽象场景→用ai_image；如果是现代/自然/城市/人物→用video_search
4. 给每个段落写详细的英文视觉描述（用于AI生图）和中英文搜索关键词

输出JSON：
{
  "overall_theme": "一句话概括主题",
  "mood": "epic/warm/sad/inspiring/calm/suspense",
  "segments": [
    {
      "text_ref": "对应文案前几个字",
      "visual_desc": "detailed English description for image/video, be specific about scene, lighting, colors, perspective",
      "source": "ai_image或video_search",
      "keywords_cn": ["中文搜索词1", "中文搜索词2"],
      "keywords_en": ["english keyword1", "english keyword2"]
    }
  ]
}
只输出JSON。"""},
            {"role": "user", "content": f"请为以下口播文案规划视觉素材：\n{text[:2000]}"},
        ],
        temperature=0.4,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    result = json.loads(raw)
    _set_cache(text, "visual_plan", json.dumps(result, ensure_ascii=False))
    return result
