"""Generate clean templates.py with proper encoding"""
import os

BRAND = "圣栎美家"

def brand_system(role_name, extra=""):
    return f"你是全屋定制品牌{BRAND}的{role_name}。所有文案必须提到品牌名{BRAND}。{BRAND}是江山欧派旗下花木匠健康板材的四川和山东总代理。{extra}"

templates_code = f'''"""全屋定制行业文案模板 API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, RewrittenScript
import json

router = APIRouter(prefix="/api/templates", tags=["templates"])

class GenerateReq(BaseModel):
    template_id: str
    fields: dict

TEMPLATES = [
    {{
        "id": "product_showcase",
        "name": "产品展示",
        "desc": "推荐单款产品，突出卖点和材质",
        "icon": "gold",
        "structure": [
            {{"role": "system", "content": "{brand_system('产品导购', '口播风格专业亲切。')}"}},
            {{"role": "user", "content": (
                "为以下全屋定制产品写一段抖音口播文案（约150-200字）：\\n"
                "产品名称：{{product_name}}\\n"
                "3个卖点：{{selling_points}}\\n"
                "材质/工艺：{{material}}\\n"
                "参考价格：{{price}}\\n\\n"
                "结构要求：\\n"
                "1. 开头用钩子吸引注意力\\n"
                "2. 中间逐一说卖点和材质，用大白话解释\\n"
                "3. 结尾引导咨询或到店，必须提到品牌名{BRAND}\\n"
                "只输出文案，不要任何说明文字。"
            )}},
        ],
        "fields": [
            {{"key": "product_name", "label": "产品名称", "placeholder": "如：ENF级实木多层衣柜"}},
            {{"key": "selling_points", "label": "3个卖点", "placeholder": "如：ENF环保、静音阻尼、一门到顶"}},
            {{"key": "material", "label": "材质/工艺", "placeholder": "如：18mm实木多层板+PET肤感门板"}},
            {{"key": "price", "label": "参考价格", "placeholder": "如：投影面积1280元/㎡"}},
        ],
    }},
    {{
        "id": "craft_knowledge",
        "name": "工艺科普",
        "desc": "讲解制作工艺，建立专业信任",
        "icon": "bulb",
        "structure": [
            {{"role": "system", "content": "{brand_system('工艺专家', '口播风格专业严谨但不枯燥。')}"}},
            {{"role": "user", "content": (
                "为以下全屋定制工艺写一段抖音口播科普文案（约150-200字）：\\n"
                "工艺名称：{{craft_name}}\\n"
                "相比其他工艺的优势：{{advantages}}\\n"
                "品质背书：{{certificate}}\\n\\n"
                "结构要求：\\n"
                "1. 开头用你知道吗或很多人不知道引入\\n"
                "2. 解释工艺原理，用生活化比喻\\n"
                "3. 对比普通工艺，突出优势\\n"
                "4. 结尾用证书/检测报告背书，并提到在{BRAND}可以找到这种工艺\\n"
                "只输出文案，不要任何说明文字。"
            )}},
        ],
        "fields": [
            {{"key": "craft_name", "label": "工艺名称", "placeholder": "如：PUR封边 vs EVA封边"}},
            {{"key": "advantages", "label": "工艺优势", "placeholder": "如：防水防潮、不易开胶、边缘光滑无缝"}},
            {{"key": "certificate", "label": "品质背书", "placeholder": "如：ENF级环保检测报告、SGS认证"}},
        ],
    }},
    {{
        "id": "avoid_pitfalls",
        "name": "避坑指南",
        "desc": "帮客户避开常见套路，引流到店",
        "icon": "warning",
        "structure": [
            {{"role": "system", "content": "{brand_system('资深顾问', '口播风格犀利直白。')}"}},
            {{"role": "user", "content": (
                "为以下全屋定制领域的坑写一段抖音口播避坑文案（约150-200字）：\\n"
                "坑的类型：{{pitfall_type}}\\n"
                "正确的避坑方案：{{solution}}\\n\\n"
                "结构要求：\\n"
                "1. 开头用千万别XXX或你以为捡了便宜制造紧迫感\\n"
                "2. 列出最常见的2-3个坑，用真实价格对比\\n"
                "3. 给出靠谱的避坑方案\\n"
                "4. 结尾引导到{BRAND}咨询\\n"
                "只输出文案，不要任何说明文字。"
            )}},
        ],
        "fields": [
            {{"key": "pitfall_type", "label": "坑的类型", "placeholder": "如：报价套路、板材以次充好、五金件减配"}},
            {{"key": "solution", "label": "避坑方案", "placeholder": "如：认准ENF检测报告、合同注明板材品牌和厚度"}},
        ],
    }},
    {{
        "id": "package_promo",
        "name": "套餐推广",
        "desc": "推广套餐活动，引流到店成交",
        "icon": "star",
        "structure": [
            {{"role": "system", "content": "{brand_system('销售经理', '口播风格热情有感染力。')}"}},
            {{"role": "user", "content": (
                "为以下全屋定制套餐写一段抖音推广口播文案（约150-200字）：\\n"
                "套餐名称：{{package_name}}\\n"
                "套餐内容：{{contents}}\\n"
                "套餐价格：{{price}}\\n"
                "活动有效期：{{validity}}\\n\\n"
                "结构要求：\\n"
                "1. 开头宣布福利（如重磅消息、仅限X天）\\n"
                "2. 说清楚套餐包含什么，强调性价比\\n"
                "3. 营造紧迫感（限量/限时）\\n"
                "4. 引导立即私信或到{BRAND}预订\\n"
                "只输出文案，不要任何说明文字。"
            )}},
        ],
        "fields": [
            {{"key": "package_name", "label": "套餐名称", "placeholder": "如：全屋定制11件套"}},
            {{"key": "contents", "label": "套餐内容", "placeholder": "如：3米衣柜+2米橱柜+鞋柜+酒柜+书柜+阳台柜"}},
            {{"key": "price", "label": "套餐价格", "placeholder": "如：仅需9999元（原价15800）"}},
            {{"key": "validity", "label": "有效期", "placeholder": "如：即日起至6月30日，仅限前20名"}},
        ],
    }},
    {{
        "id": "customer_case",
        "name": "客户案例",
        "desc": "真实案例打动潜在客户",
        "icon": "camera",
        "structure": [
            {{"role": "system", "content": "{brand_system('客服', '口播风格真诚温暖。')}"}},
            {{"role": "user", "content": (
                "为以下全屋定制客户案例写一段抖音口播文案（约150-200字）：\\n"
                "案例描述：{{case_desc}}\\n"
                "使用的产品/板材：{{products_used}}\\n\\n"
                "结构要求：\\n"
                "1. 开头展示改造后的惊艳效果\\n"
                "2. 简要说改造前的痛点\\n"
                "3. 介绍用了什么产品和板材\\n"
                "4. 结尾引导咨询同款方案，提到{BRAND}\\n"
                "只输出文案，不要任何说明文字。"
            )}},
        ],
        "fields": [
            {{"key": "case_desc", "label": "案例描述", "placeholder": "如：成都高新区张女士家89㎡小三房，全屋定制花了3.2万"}},
            {{"key": "products_used", "label": "使用产品/板材", "placeholder": "如：花木匠ENF实木多层板+欧派同款拉手+PET门板"}},
        ],
    }},
    {{
        "id": "brand_trust",
        "name": "行业背书",
        "desc": "展示品牌实力，建立客户信任",
        "icon": "shield",
        "structure": [
            {{"role": "system", "content": "{brand_system('市场总监', '口播风格大气自信。')}"}},
            {{"role": "user", "content": (
                "为以下品牌写一段抖音口播背书文案（约150-200字）：\\n"
                "合作品牌：{{brand_name}}\\n"
                "核心优势：{{advantages}}\\n\\n"
                "结构要求：\\n"
                "1. 开头亮出品牌身份（我们是江山欧派旗下{BRAND}）\\n"
                "2. 用数据和事实说话（授权、检测报告、合作案例）\\n"
                "3. 强调服务承诺\\n"
                "4. 结尾引导全国定制工厂合作\\n"
                "只输出文案，不要任何说明文字。"
            )}},
        ],
        "fields": [
            {{"key": "brand_name", "label": "合作品牌", "placeholder": "如：江山欧派授权·花木匠健康板材"}},
            {{"key": "advantages", "label": "核心优势", "placeholder": "如：四川+山东总代理、ENF级环保认证、面向全国定制工厂"}},
        ],
    }},
]


@router.get("")
def list_templates():
    return {{
        "code": 0,
        "data": [
            {{"id": t["id"], "name": t["name"], "desc": t["desc"], "icon": t["icon"], "fields": t["fields"]}}
            for t in TEMPLATES
        ],
    }}


@router.post("/generate")
def generate_script(req: GenerateReq, db: Session = Depends(get_db)):
    template_id = req.template_id
    fields = req.fields
    import random as _rnd
    STYLES = [
        {{"name": "活泼", "prompt": "用活泼热情的语气，多带口语，像朋友聊天一样。"}},
        {{"name": "专业", "prompt": "用专业理性的语气，引用数据和标准，像行业顾问在讲解。"}},
        {{"name": "幽默", "prompt": "用轻松幽默的语气，加一点调侃和自嘲，让人会心一笑又记住要点。"}},
    ]
    style = _rnd.choice(STYLES)

    tmpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if not tmpl:
        return {{"code": 1, "message": "模板不存在"}}

    messages = []
    for item in tmpl["structure"]:
        content = item["content"]
        if item["role"] == "user":
            content += f"\\n口播风格：{{style['prompt']}}"
        for key, val in fields.items():
            content = content.replace("{{" + key + "}}", str(val))
        messages.append({{"role": item["role"], "content": content}})

    from openai import OpenAI
    from app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
    r = client.chat.completions.create(
        model="qwen-plus",
        messages=messages,
        temperature=0.8,
        max_tokens=600,
    )
    script = r.choices[0].message.content.strip()

    record = RewrittenScript(
        original_text=json.dumps(fields, ensure_ascii=False),
        rewritten_text=script,
        style=template_id,
        word_count=len(script),
        source_type="template",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {{"code": 0, "data": {{"script_id": record.id, "text": script, "style": style["name"]}}}}
'''

output_path = r'd:\应用开发项目集\AI短视频创作平台项目\backend\app\routers\templates.py'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(templates_code)
print(f"Written to {output_path}")

# Verify
import ast
ast.parse(templates_code)
print("Syntax OK")
