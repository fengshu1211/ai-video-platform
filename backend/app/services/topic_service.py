"""爆款选题分析 — 真实搜索 + AI分析"""
import json
import os
from openai import OpenAI
from app.config import DASHSCOPE_BASE_URL

def _get_client():
    try:
        from app.main import get_user_key
        key = get_user_key("dashscope") or os.getenv("DASHSCOPE_API_KEY", "")
    except Exception:
        key = os.getenv("DASHSCOPE_API_KEY", "")
    if not key:
        raise RuntimeError("请先在系统设置中配置通义千问 API Key")
    return OpenAI(api_key=key, base_url=DASHSCOPE_BASE_URL)


def _search_web(keyword: str, max_results: int = 5) -> list[dict]:
    """真实网络搜索，返回标题+摘要"""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(keyword, max_results=max_results):
                results.append({"title": r["title"], "body": r["body"][:200], "href": r["href"]})
        return results
    except Exception:
        return []


def generate_hot_topics(track_name: str, count: int = 8) -> list[dict]:
    """真实搜索+AI分析生成爆款选题"""
    import random
    # 多样化的搜索词，每次随机组合避免重复
    platforms = ["抖音 热门", "B站 爆款", "小红书 热搜", "视频号 热门", "百度热搜"]
    angles = ["最新", "本周", "2025", "揭秘", "冷知识", "反差", "颠覆认知", "考古新发现", "历史真相"]
    queries = []
    for _ in range(4):
        plat = random.choice(platforms)
        angle = random.choice(angles)
        queries.append(f"{track_name} {angle} {plat}")
    raw_results = []
    for q in queries:
        raw_results.extend(_search_web(q, max_results=4))

    # AI基于真实搜索数据生成选题
    search_context = ""
    if raw_results:
        search_context = "以下是从网络搜索到的当前热门内容参考：\n"
        for i, r in enumerate(raw_results[:12]):
            search_context += f"{i+1}. {r['title']} —— {r['body'][:100]}\n"
    else:
        search_context = f"请根据你对{track_name}赛道的了解生成选题"

    response = _get_client().chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": f"""你是自媒体选题分析专家。基于真实的网络搜索数据，结合{track_name}赛道特点，生成可能成为爆款的选题。
输出JSON数组：
[{{"title": "选题标题", "platform": "douyin|bilibili|xiaohongshu", "analysis": "基于真实数据的爆款原因分析（50字内）", "metrics": {{"views": "预估播放量", "likes": "预估点赞", "comments": "预估评论"}}}}]
标题要有吸引力，每个选题标注适合的平台。只输出JSON数组。"""},
            {"role": "user", "content": f"为【{track_name}】赛道生成{count}个当前最可能成为爆款的选题\n\n{search_context}"},
        ],
        temperature=0.8, max_tokens=3000,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(raw)
