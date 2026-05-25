"""新手模板 - persona presets and sample scripts"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/templates", tags=["templates"])

PERSONA_TEMPLATES = [
    {
        "id": "history",
        "name": "历史科普",
        "icon": "history",
        "persona": {
            "name": "历史科普号",
            "industry": "历史科普",
            "specialization": "",
            "brand_name": "",
            "role": "历史博主",
            "personality": "幽默风趣, 擅长用大白话讲历史",
            "features": "",
            "content_style": "story",
            "target_audience": "25-45岁历史爱好者",
        },
        "scripts": [
            {"title": "秦始皇陵地宫揭秘", "duration": "约90秒",
             "text": "秦始皇陵地宫从来不是史书里描写的水银成川, 机括如林, 而是一座仍在呼吸的地下星穹. 高精度三维激光测绘首次揭开地宫真容: 它并非向下深掘, 而是以九层宫阙向上堆叠. 封土之下76米, 量子磁力梯度仪捕捉到异常环形结构与多重密闭空间."},
        ],
    },
    {
        "id": "home",
        "name": "家居装修",
        "icon": "home",
        "persona": {
            "name": "家居装修号",
            "industry": "家居装修",
            "specialization": "",
            "brand_name": "",
            "role": "全屋定制设计师",
            "personality": "专业严谨, 用数据说话",
            "features": "",
            "content_style": "fast",
            "target_audience": "25-40岁装修业主",
        },
        "scripts": [
            {"title": "全屋定制报价大揭秘", "duration": "约75秒",
             "text": "一块普普通通的欧松板, 出厂价才37.8元, 到了报价单上摇身一变成了198元一平米. 这中间飞走的160块, 是木头, 是工艺, 还是品牌滤镜? 我们蹲点工厂, 翻烂合同, 扒了37家真实报价单, 把每笔钱流向摊在你面前."},
        ],
    },
    {
        "id": "food",
        "name": "美食探店",
        "icon": "food",
        "persona": {
            "name": "美食探店号",
            "industry": "美食探店",
            "specialization": "",
            "brand_name": "",
            "role": "美食博主",
            "personality": "亲和力强, 画面感十足",
            "features": "",
            "content_style": "humorous",
            "target_audience": "18-35岁美食爱好者",
        },
        "scripts": [
            {"title": "街边30年苍蝇馆子", "duration": "约60秒",
             "text": "一个米其林大厨跟我说: 全城最好吃的回锅肉, 藏在一个连招牌都没有的苍蝇馆子里. 30年老店, 老板是个67岁的婆婆, 每天只炒30份. 今天带你去看看什么叫真正的锅气."},
        ],
    },
    {
        "id": "tech",
        "name": "数码评测",
        "icon": "tech",
        "persona": {
            "name": "数码评测号",
            "industry": "科技数码",
            "specialization": "",
            "brand_name": "",
            "role": "数码博主",
            "personality": "客观理性, 参数党最爱",
            "features": "",
            "content_style": "fast",
            "target_audience": "20-35岁数码爱好者",
        },
        "scripts": [
            {"title": "两万八的显卡值不值", "duration": "约80秒",
             "text": "先别急着下单RTX5090 - 那张被黄牛炒到两万八的信仰神卡. 我们把RX7900XTX塞进旗舰平台, 实测赛博朋克2077光追全开加FSR3帧生成, 结果让人沉默. 这不是勉强能用, 这是真性能平权."},
        ],
    },
]


@router.get("/personas")
def list_persona_templates():
    return {"code": 0, "templates": [
        {"id": t["id"], "name": t["name"], "icon": t["icon"],
         "persona": t["persona"], "script_count": len(t["scripts"])}
        for t in PERSONA_TEMPLATES
    ]}


@router.get("/personas/{template_id}")
def get_template(template_id: str):
    for t in PERSONA_TEMPLATES:
        if t["id"] == template_id:
            return {"code": 0, "template": t}
    return {"code": 404, "message": "template not found"}
