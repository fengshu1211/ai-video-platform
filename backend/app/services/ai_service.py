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


def get_persona_context(user_id: int = None) -> str:
    """读取用户人设AI风格模板，生成一段注入AI的上下文"""
    if not user_id:
        return ""
    try:
        import sqlite3, json
        conn = sqlite3.connect("data.db")
        rows = conn.execute(
            "SELECT ai_style_template, industry, specialization, author_name, personality, content_style, target_audience "
            "FROM user_personas WHERE user_id=? LIMIT 1", (user_id,)
        ).fetchall()
        conn.close()
        if not rows or not rows[0][0]:
            return ""
        tmpl = json.loads(rows[0][0]) if isinstance(rows[0][0], str) else rows[0][0]
        ind, spec, author, pers, style, aud = rows[0][1], rows[0][2], rows[0][3], rows[0][4], rows[0][5], rows[0][6]

        parts = []
        if author:
            parts.append(f"作者署名: {author}")
        if ind:
            parts.append(f"行业: {ind}" + (f"/{spec}" if spec else ""))
        if pers:
            parts.append(f"性格: {pers}")
        if style:
            parts.append(f"内容风格: {style}")
        if aud:
            parts.append(f"目标受众: {aud}")
        if tmpl.get("tone"):
            parts.append(f"语气: {tmpl['tone']}")
        if tmpl.get("sentence_length"):
            parts.append(f"句长偏好: {tmpl['sentence_length']}")
        if tmpl.get("writing_tips"):
            parts.append(f"创作要点: {tmpl['writing_tips']}")
        if tmpl.get("taboo_words"):
            parts.append(f"避免词汇: {', '.join(tmpl['taboo_words'])}")
        if tmpl.get("openings"):
            parts.append(f"开头参考: {tmpl['openings'][0]}")
        if tmpl.get("closings"):
            parts.append(f"结尾参考: {tmpl['closings'][0]}")

        return "\n".join(parts) if parts else ""
    except Exception:
        return ""


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

MARKETING_STYLES = {
    "ogilvy": {
        "name": "研究驱动风",
        "desc": "数据支撑+事实说服+利益导向",
        "prompt": "采用David Ogilvy风格改写：1.用具体数据开头制造冲击感；2.每段用事实和研究支撑观点；3.强调产品/内容的实际利益而非空洞形容词；4.结尾给出明确结论。",
        "opening": "用令人惊讶的具体数字/事实开头",
        "structure": "事实→数据→利益→结论",
    },
    "halbert": {
        "name": "直复营销风",
        "desc": "情感钩子+紧迫感+行动号召",
        "prompt": "采用Gary Halbert风格改写：1.用极度吸引人的情感钩子开场；2.制造问题紧迫感让读者停不下来；3.穿插具体案例和故事；4.结尾给出强烈的行动号召。",
        "opening": "用让人无法抗拒的好奇心钩子开头",
        "structure": "钩子→故事→紧迫感→行动",
    },
    "schwartz": {
        "name": "欲望引导风",
        "desc": "先造欲望+再给方案+层层递进",
        "prompt": "采用Eugene Schwartz风格改写：1.先放大读者的渴望和欲望；2.描绘理想状态的美好画面；3.再给出实现路径；4.最后点出你的核心观点是唯一答案。",
        "opening": "先描绘读者最渴望的理想状态",
        "structure": "欲望→画面→路径→答案",
    },
    "aida": {
        "name": "AIDA经典风",
        "desc": "注意→兴趣→欲望→行动",
        "prompt": "采用AIDA框架改写：1.Attention：用一个令人震惊的事实/问题引起注意；2.Interest：展开细节让读者产生兴趣；3.Desire：描绘好处激发想要的情绪；4.Action：结尾给出明确的下一步。",
        "opening": "用一个让人无法忽视的事实吸引注意",
        "structure": "注意→兴趣→欲望→行动",
    },
    "pas": {
        "name": "痛点解决风",
        "desc": "戳痛点+放大焦虑+给出解药",
        "prompt": "采用PAS框架改写：1.Problem：直戳读者最痛的困扰；2.Agitate：用场景描述放大这种痛苦；3.Solve：给出你的解决方案/核心观点。让读者感到你懂他们的痛苦。",
        "opening": "直戳读者最焦虑的具体痛点",
        "structure": "痛点→放大→解药→升华",
    },
}


def generate_titles(text: str, count: int = 5, user_id: int = None) -> list[str]:
    """为文案生成爆款标题（自动注入人设风格）"""
    persona_ctx = get_persona_context(user_id)
    system = "你是爆款标题专家。根据文案内容生成多个吸引眼球的标题，每个标题≤30字。"
    if persona_ctx:
        system += f" 标题要符合以下创作者风格：{persona_ctx}"
    system += " 输出JSON数组：[\"标题1\",\"标题2\",...]"

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "user", "content": system},
            {"role": "user", "content": f"根据以下内容生成{count}个爆款标题：\n{text[:1500]}"},
        ],
        temperature=0.9, max_tokens=500,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    import json
    return json.loads(raw)


def rewrite_text(text: str, style: str = "similar", target_word_count: int | None = None,
                 user_id: int = None, marketing_style: str = "") -> str:
    """AI改写文案，自动注入用户人设风格+营销大师框架"""
    cache_key = f"{text}|{style}|{target_word_count or ''}|{user_id or ''}|{marketing_style}"
    cached = _get_cached(cache_key, "rewrite")
    if cached:
        return cached

    prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["similar"])
    if target_word_count and target_word_count > 0:
        prompt += f" 请控制改写后的字数在 {target_word_count} 字左右，可以适当浮动 ±10%。"

    # 营销风格注入
    if marketing_style and marketing_style in MARKETING_STYLES:
        ms = MARKETING_STYLES[marketing_style]
        prompt += f"\n\n[营销框架] {ms['prompt']}"

    persona_ctx = get_persona_context(user_id)
    system = "你是一个专业自媒体文案改写助手。"
    if persona_ctx:
        system += f" 请严格遵循以下创作者风格：\n{persona_ctx}"

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "user", "content": system},
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
- 细分领域：{persona_data.get('specialization', '未填写')}
- 署名名称：{persona_data.get('author_name', '未填写')}
- 核心特色/擅长领域：{persona_data.get('features', '未填写')}
- 角色/职位：{persona_data.get('role', '未填写')}
- 性格：{persona_data.get('personality', '未填写')}
- 产品特点/卖点：{persona_data.get('features', '未填写')}
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
        messages=[{"role": "user", "content": "你是内容风格分析师，擅长根据用户特征生成专属内容创作模板。只输出JSON。"},
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
            {"role": "user", "content": """你是一个视频素材匹配助手。仔细分析文案内容，提取能精准匹配视频素材的搜索关键词。
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


def plan_visual_materials(text: str, user_id: int = None) -> dict:
    """AI导演分镜：吃透全文→规划每个视觉段落的素材方案（注入人设风格）

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

    persona_ctx = get_persona_context(user_id)
    director_system = """你是视频导演。请仔细阅读口播文案，理解主题、情绪和叙事结构，然后为文案规划视觉素材方案。"""

    if persona_ctx:
        director_system += f"\n\n创作者风格（视觉素材要匹配此风格）：\n{persona_ctx}"

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "user", "content": director_system + """

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
