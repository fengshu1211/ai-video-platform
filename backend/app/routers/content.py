"""内容改写 API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.models.database import get_db, RewrittenScript
from app.schemas.content import RewriteRequest, ScrapeRequest, ScriptOut, ScriptUpdate
from app.services.ai_service import rewrite_text, generate_titles

router = APIRouter(prefix="/api/content", tags=["content"])

def _get_uid() -> int | None:
    try:
        from app.main import get_current_user_id
        return get_current_user_id()
    except Exception:
        return None


@router.post("/rewrite", response_model=ScriptOut)
def rewrite_content(data: RewriteRequest, db: Session = Depends(get_db)):
    user_id = data.user_id or _get_uid()
    if data.style == "keep":
        rewritten = data.original_text
    else:
        rewritten = rewrite_text(data.original_text, data.style, data.target_word_count, user_id=user_id)

    script = RewrittenScript(
        topic_id=data.topic_id,
        original_text=data.original_text,
        rewritten_text=rewritten,
        style=data.style,
        word_count=len(data.original_text),
        source_url=data.source_url,
        source_type="link" if data.source_url else "manual",
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


@router.post("/scrape")
def scrape_content(data: ScrapeRequest, db: Session = Depends(get_db)):
    """抓取网页正文，B站特殊处理"""
    import httpx, trafilatura, re
    url = data.url
    try:
        # 抖音/快手：无法自动提取字幕，提示手动粘贴
        if any(d in url for d in ['douyin.com','v.douyin','kuaishou.com','v.kuaishou']):
            return {"code": 1, "message": "抖音/快手视频字幕需手动粘贴文案。请将口播文案复制后粘贴到输入框"}
        # B站视频：调用公开API获取标题+简介
        bv_match = re.search(r'(BV\w{10}|av\d+)', url)
        if bv_match and ('bilibili.com' in url or 'b23.tv' in url):
            bvid = bv_match.group(1)
            info = httpx.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"},
                timeout=10).json()
            if info.get("code") == 0:
                vdata = info["data"]
                title = vdata.get("title", "")
                desc = vdata.get("desc", "")
                text = f"{title}\n\n{desc}".strip()
                if len(text) > 20:
                    return {"code": 0, "data": {"url": url, "text": text[:3000], "platform": data.platform}}
            return {"code": 1, "message": "B站视频信息获取失败，请手动粘贴标题和简介"}
        # 通用网页：trafilatura提取正文
        resp = httpx.get(url, timeout=15, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"})
        if resp.status_code == 200 and len(resp.text) > 500:
            text = trafilatura.extract(resp.text, include_links=False, include_images=False)
            if text and len(text) > 50:
                return {"code": 0, "data": {"url": url, "text": text[:3000], "platform": data.platform}}
        return {"code": 1, "message": "无法提取正文，请手动粘贴内容"}
    except Exception as e:
        return {"code": 1, "message": f"抓取失败：{str(e)[:100]}"}


@router.get("/scripts", response_model=list[ScriptOut])
def list_scripts(db: Session = Depends(get_db)):
    return db.query(RewrittenScript).order_by(RewrittenScript.created_at.desc()).limit(50).all()


@router.get("/scripts/{script_id}", response_model=ScriptOut)
def get_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(RewrittenScript).filter(RewrittenScript.id == script_id).first()
    if not script:
        raise HTTPException(404, "文案不存在")
    return script


@router.patch("/scripts/{script_id}", response_model=ScriptOut)
def update_script(script_id: int, data: ScriptUpdate, db: Session = Depends(get_db)):
    script = db.query(RewrittenScript).filter(RewrittenScript.id == script_id).first()
    if not script:
        raise HTTPException(404, "文案不存在")
    if data.rewritten_text is not None:
        script.rewritten_text = data.rewritten_text
    if data.is_approved is not None:
        script.is_approved = data.is_approved
    db.commit()
    db.refresh(script)
    return script


@router.post("/scripts/{script_id}/publish")
def generate_publish_content(script_id: int, db: Session = Depends(get_db)):
    """AI生成适配各平台的发布标题和文案"""
    from openai import OpenAI
    from app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL

    script = db.query(RewrittenScript).filter(RewrittenScript.id == script_id).first()
    if not script:
        raise HTTPException(404, "文案不存在")

    text = script.rewritten_text or script.original_text
    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "system", "content": """为以下视频文案生成4个平台的发布内容。输出JSON格式：
{
  "douyin": {"title": "抖音标题(≤30字，带话题#)", "desc": "抖音描述(≤100字，带标签)", "tags": "标签1 #标签2 #标签3"},
  "shipinhao": {"title": "视频号标题(≤16字，不能带任何标点符号，带话题#)", "desc": "视频号描述(≤80字)", "tags": "#标签1 #标签2"},
  "kuaishou": {"title": "快手标题(≤30字，接地气，末尾最多4个#标签)", "desc": "快手描述(≤100字，末尾最多4个#标签)", "tags": "#标签1 #标签2 #标签3 #标签4"},
  "xiaohongshu": {"title": "小红书标题(≤20字，种草风，带emoji)", "desc": "小红书正文(≤150字，带#标签 带emoji)", "tags": "#标签1 #标签2 #标签3 #标签4 #标签5"}
}
tags字段放推荐的标签列表，格式如"#历史 #明朝 #朱元璋 #帝王故事"。标题要抓眼球但不标题党。只输出JSON，不要其他内容。"""},
            {"role": "user", "content": f"视频文案：\n{text[:1500]}"}],
        temperature=0.8, max_tokens=1200,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    import json
    return {"code": 0, "data": json.loads(raw)}


@router.post("/titles")
def gen_titles(data: RewriteRequest, db: Session = Depends(get_db)):
    """为文案生成爆款标题"""
    try:
        titles = generate_titles(data.original_text, user_id=data.user_id or _get_uid())
        return {"code": 0, "data": titles}
    except Exception as e:
        return {"code": 1, "message": f"生成失败：{str(e)[:100]}"}


@router.delete("/scripts/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    script = db.query(RewrittenScript).filter(RewrittenScript.id == script_id).first()
    if not script:
        raise HTTPException(404, "文案不存在")
    db.delete(script)
    db.commit()
    return {"code": 0, "message": "已删除"}
