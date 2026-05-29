"""全屋定制行业文案模板 API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.database import get_db, RewrittenScript
import json

router = APIRouter(prefix="/api/templates", tags=["templates"])

class GenerateReq(BaseModel):
    template_id: str
    fields: dict
    style: str = "随机"

TEMPLATES = [
    {
        "id": "product_showcase",
        "brand": "圣栎美家",
        "name": "产品招商",
        "desc": "面向经销商展示产品，突出合作优势",
        "icon": "gold",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的招商经理，面向全国经销商和定制门店招商。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家，是江山欧派旗下花木匠健康板材的四川和山东总代理，主营全屋定制柜类、木门、墙板，诚招各地经销商合作。口播风格专业有说服力。"},
            {"role": "user", "content": (
                "为以下全屋定制产品写一段面向经销商的抖音招商口播文案（约150-200字）：\n"
                "产品名称：{product_name}\n"
                "3个卖点：{selling_points}\n"
                "材质/工艺：{material}\n"
                "出厂参考价：{price}\n\n"
                "结构要求：\n"
                "1. 开头用'定制老板看过来'或'经销商注意'引入，直接说产品\n"
                "2. 中间逐一说卖点和材质，强调出厂价优势\n"
                "3. 结尾引导客户在评论区留言索取资料，必须清晰提到品牌名：圣栎美家\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "product_name", "label": "产品名称", "placeholder": "如：ENF级实木多层衣柜"},
            {"key": "selling_points", "label": "3个卖点", "placeholder": "如：ENF环保、静音阻尼、一门到顶"},
            {"key": "material", "label": "材质/工艺", "placeholder": "如：18mm实木多层板+PET肤感门板"},
            {"key": "price", "label": "参考价格", "placeholder": "如：投影面积1280元/㎡"},
        ],
    },
    {
        "id": "craft_knowledge",
        "brand": "圣栎美家",
        "name": "工艺科普",
        "desc": "讲解制作工艺，建立专业信任",
        "icon": "bulb",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的工艺专家。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家，是江山欧派旗下花木匠健康板材的四川和山东总代理。口播风格专业严谨但不枯燥。"},
            {"role": "user", "content": (
                "为以下全屋定制工艺写一段面向经销商的抖音科普文案（约150-200字）：\n"
                "工艺名称：{craft_name}\n"
                "相比其他工艺的优势：{advantages}\n"
                "品质背书：{certificate}\n\n"
                "结构要求：\n"
                "1. 开头用你知道吗或很多人不知道引入\n"
                "2. 解释工艺原理，用生活化比喻\n"
                "3. 对比普通工艺，突出优势\n"
                "4. 结尾用证书/检测报告背书，结尾引导客户在评论区留言索取工艺资料，并提到与圣栎美家合作\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "craft_name", "label": "工艺名称", "placeholder": "如：PUR封边 vs EVA封边"},
            {"key": "advantages", "label": "工艺优势", "placeholder": "如：防水防潮、不易开胶、边缘光滑无缝"},
            {"key": "certificate", "label": "品质背书", "placeholder": "如：ENF级环保检测报告、SGS认证"},
        ],
    },
    {
        "id": "avoid_pitfalls",
        "brand": "圣栎美家",
        "name": "避坑指南",
        "desc": "帮客户避开常见套路，引流到店",
        "icon": "warning",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的资深顾问。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家，是江山欧派旗下花木匠健康板材的四川和山东总代理。口播风格犀利直白。"},
            {"role": "user", "content": (
                "为以下全屋定制领域的坑写一段抖音口播避坑文案（约150-200字）：\n"
                "坑的类型：{pitfall_type}\n"
                "正确的避坑方案：{solution}\n\n"
                "结构要求：\n"
                "1. 开头用千万别XXX或你以为捡了便宜制造紧迫感\n"
                "2. 列出最常见的2-3个坑，用真实价格对比\n"
                "3. 给出靠谱的避坑方案\n"
                "4. 结尾引导在评论区留言索取避坑清单，必须提到圣栎美家\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "pitfall_type", "label": "坑的类型", "placeholder": "如：报价套路、板材以次充好、五金件减配"},
            {"key": "solution", "label": "避坑方案", "placeholder": "如：认准ENF检测报告、合同注明板材品牌和厚度"},
        ],
    },
    {
        "id": "package_promo",
        "brand": "圣栎美家",
        "name": "套餐推广",
        "desc": "推广套餐活动，引流到店成交",
        "icon": "star",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的销售经理。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家，是江山欧派旗下花木匠健康板材的四川和山东总代理。口播风格热情有感染力。"},
            {"role": "user", "content": (
                "为以下全屋定制套餐写一段抖音推广口播文案（约150-200字）：\n"
                "套餐名称：{package_name}\n"
                "套餐内容：{contents}\n"
                "套餐价格：{price}\n"
                "活动有效期：{validity}\n\n"
                "结构要求：\n"
                "1. 开头宣布福利（如重磅消息、仅限X天）\n"
                "2. 说清楚套餐包含什么，强调性价比\n"
                "3. 营造紧迫感（限量/限时）\n"
                "4. 结尾引导在评论区留言索取套餐报价，必须提到圣栎美家\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "package_name", "label": "套餐名称", "placeholder": "如：全屋定制11件套"},
            {"key": "contents", "label": "套餐内容", "placeholder": "如：3米衣柜+2米橱柜+鞋柜+酒柜+书柜+阳台柜"},
            {"key": "price", "label": "套餐价格", "placeholder": "如：仅需9999元（原价15800）"},
            {"key": "validity", "label": "有效期", "placeholder": "如：即日起至6月30日，仅限前20名"},
        ],
    },
    {
        "id": "customer_case",
        "brand": "圣栎美家",
        "name": "客户案例",
        "desc": "真实案例打动潜在客户",
        "icon": "camera",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的客服。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家，是江山欧派旗下花木匠健康板材的四川和山东总代理。口播风格真诚温暖。"},
            {"role": "user", "content": (
                "为以下全屋定制客户案例写一段抖音口播文案（约150-200字）：\n"
                "案例描述：{case_desc}\n"
                "使用的产品/板材：{products_used}\n\n"
                "结构要求：\n"
                "1. 开头展示改造后的惊艳效果\n"
                "2. 简要说改造前的痛点\n"
                "3. 介绍用了什么产品和板材\n"
                "4. 结尾引导在评论区留言索取同款方案，提到圣栎美家\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "case_desc", "label": "案例描述", "placeholder": "如：成都高新区张女士家89㎡小三房，全屋定制花了3.2万"},
            {"key": "products_used", "label": "使用产品/板材", "placeholder": "如：花木匠ENF实木多层板+欧派同款拉手+PET门板"},
        ],
    },
    {
        "id": "brand_trust",
        "brand": "圣栎美家",
        "name": "行业背书",
        "desc": "展示品牌实力，建立客户信任",
        "icon": "shield",
        "structure": [
            {"role": "user", "content": "你是全屋定制品牌圣栎美家的市场总监。所有文案必须清晰提到品牌名：圣栎美家。圣栎美家，是江山欧派旗下花木匠健康板材的四川和山东总代理。口播风格大气自信。"},
            {"role": "user", "content": (
                "为以下品牌写一段抖音口播背书文案（约150-200字）：\n"
                "合作品牌：{brand_name}\n"
                "核心优势：{advantages}\n\n"
                "结构要求：\n"
                "1. 开头亮出品牌身份（我们是江山欧派旗下圣栎美家）\n"
                "2. 用数据和事实说话（授权、检测报告、合作案例）\n"
                "3. 强调服务承诺\n"
                "4. 结尾引导在评论区留言索取合作资料\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "brand_name", "label": "合作品牌", "placeholder": "如：江山欧派授权·花木匠健康板材"},
            {"key": "advantages", "label": "核心优势", "placeholder": "如：四川+山东总代理、ENF级环保认证、面向全国定制工厂"},
        ],
    },
    {
        "id": "panel_sales",
        "brand": "纬臻木业",
        "name": "板材推广",
        "desc": "推广花木匠健康板材，面向全国定制工厂",
        "icon": "gold",
        "structure": [
            {"role": "user", "content": "你是纬臻木业的板材销售经理。纬臻木业，是江山欧派旗下花木匠健康板材的四川和山东总代理。所有文案必须清晰提到公司名：纬臻木业和板材品牌花木匠健康板材。口播风格专业自信。"},
            {"role": "user", "content": (
                "为花木匠健康板材写一段抖音推广口播文案（约150-200字）：\n"
                "板材类型：{panel_type}\n"
                "环保等级/认证：{eco_level}\n"
                "核心优势：{advantages}\n"
                "面向客户：{target_customers}\n\n"
                "结构要求：\n"
                "1. 开头用'定制工厂老板注意了'或'别再被板材商坑了'引入\n"
                "2. 强调ENF环保等级和检测报告背书\n"
                "3. 说明纬臻木业，是江山欧派旗下花木匠板材的授权总代\n"
                "4. 结尾引导在评论区留言索取板材样品和报价\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "panel_type", "label": "板材类型", "placeholder": "如：ENF实木多层板、PET准分子肤感板、原木碳晶系列"},
            {"key": "eco_level", "label": "环保等级/认证", "placeholder": "如：ENF级（甲醛释放≤0.025mg/m³）、F4星认证"},
            {"key": "advantages", "label": "核心优势", "placeholder": "如：江山欧派授权总代、现货充足、一件代发、16年行业经验"},
            {"key": "target_customers", "label": "面向客户", "placeholder": "如：全国定制工厂、全屋定制门店、装修公司"},
        ],
    },
    {
        "id": "factory_visit",
        "brand": "纬臻木业",
        "name": "工厂拜访",
        "desc": "拜访使用花木匠板材的客户工厂，帮客户宣传+吸引同行合作",
        "icon": "camera",
        "structure": [
            {"role": "user", "content": "你是纬臻木业的板材销售经理。纬臻木业，是江山欧派旗下花木匠健康板材的四川和山东总代理。你的视频文案是去拜访已经采购了花木匠板材的全屋定制工厂客户，一方面帮客户工厂做宣传出镜，一方面向同行展示花木匠板材的实际使用效果。所有文案必须提到花木匠健康板材和纬臻木业。"},
            {"role": "user", "content": (
                "为纬臻木业写一段拜访合作客户工厂的抖音口播文案（约150-200字）：\n"
                "拜访的客户工厂：{factory_name}\n"
                "客户工厂所在地/规模：{factory_info}\n"
                "客户用了哪些花木匠板材：{panels_used}\n"
                "客户工厂的评价/使用效果：{feedback}\n\n"
                "结构要求：\n"
                "1. 开头用'今天我们来到XX工厂'或'带你看一家用花木匠板材的工厂'开场\n"
                "2. 展示客户工厂的生产线和成品效果，帮客户做宣传\n"
                "3. 自然带出客户对花木匠板材的评价\n"
                "4. 结尾引导在评论区留言索取板材样品，必须提到纬臻木业、花木匠\n"
                "只输出文案，不要任何说明文字。"
            )},
        ],
        "fields": [
            {"key": "factory_name", "label": "拜访的客户工厂名称", "placeholder": "如：成都XX定制家居工厂、山东XX全屋定制"},
            {"key": "factory_info", "label": "工厂所在地/规模", "placeholder": "如：成都双流3000㎡生产基地、月产定制柜500套"},
            {"key": "panels_used", "label": "客户用了哪些板材", "placeholder": "如：花木匠ENF实木多层板做柜体+PET准分子肤感板做门板"},
            {"key": "feedback", "label": "客户工厂的评价/使用效果", "placeholder": "如：板材稳定性好不变形、ENF检测客户认可度高、出货效率提升30%"},
        ],
    },
]


@router.get("")
def list_templates(brand: str = ""):
    result = [
        {"id": t["id"], "name": t["name"], "desc": t["desc"], "icon": t["icon"],
         "brand": t.get("brand", "圣栎美家"), "fields": t["fields"]}
        for t in TEMPLATES
        if not brand or t.get("brand", "圣栎美家") == brand
    ]
    return {"code": 0, "data": result}


@router.post("/generate")
def generate_script(req: GenerateReq, db: Session = Depends(get_db)):
    template_id = req.template_id
    fields = req.fields
    import random as _rnd
    STYLES = [
        {"name": "活泼", "prompt": "用活泼热情的语气，多带口语，像朋友聊天一样。"},
        {"name": "专业", "prompt": "用专业理性的语气，引用数据和标准，像行业顾问在讲解。"},
        {"name": "幽默", "prompt": "用轻松幽默的语气，加一点调侃和自嘲，让人会心一笑又记住要点。"},
    ]
    # 用户选了具体风格就用选中的，否则随机
    if req.style and req.style != "随机":
        style = next((s for s in STYLES if s["name"] == req.style), _rnd.choice(STYLES))
    else:
        style = _rnd.choice(STYLES)

    tmpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if not tmpl:
        return {"code": 1, "message": "模板不存在"}

    messages = []
    for item in tmpl["structure"]:
        content = item["content"]
        if item["role"] == "user":
            content += f"\n口播风格：{style['prompt']}"
        for key, val in fields.items():
            content = content.replace("{" + key + "}", str(val))
        messages.append({"role": item["role"], "content": content})

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

    return {"code": 0, "data": {"script_id": record.id, "text": script, "style": style["name"]}}
