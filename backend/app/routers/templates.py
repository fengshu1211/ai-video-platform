"""新手模板——人设预设 + 示例文案"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/templates", tags=["templates"])

PERSONA_TEMPLATES = [
    {
        "id": "history",
        "name": "历史博主",
        "icon": "🏛️",
        "persona": {
            "name": "历史科普号",
            "industry": "历史科普",
            "role": "历史博主",
            "personality": "幽默风趣，擅长用大白话讲历史",
            "content_style": "故事叙事风",
            "target_audience": "25-45岁历史爱好者",
        },
        "scripts": [
            {
                "title": "秦始皇陵地宫揭秘",
                "text": "你敢相信吗？秦始皇陵地宫，从来就不是史书里描写的"水银成川、机括如林"，而是一座仍在呼吸的地下星穹！一张刚刚浮出水面的高精度三维激光测绘影像，首次揭开地宫真容：它并非按常规墓制向下深掘，而是以九层宫阙的形态向上堆叠。封土之下76米，量子磁力梯度仪捕捉到异常环形结构与多重密闭空间。这不是传说，是考古学等了几十年的答案。",
                "duration": "约90秒",
            },
            {
                "title": "赤壁之战真相",
                "text": "赤壁之战，火烧连环船——这个故事你一定听过。但真相是：曹操的八十万大军根本不存在，那场大火可能也不是诸葛亮借来的东风。2024年最新地理考古发现，赤壁古战场的实际位置和史书记载相差了整整40公里。今天我们来还原一个真实的三国战场。",
                "duration": "约70秒",
            },
        ],
    },
    {
        "id": "home",
        "name": "家居设计师",
        "icon": "🏠",
        "persona": {
            "name": "家居装修号",
            "industry": "家居装修",
            "role": "全屋定制设计师",
            "personality": "专业严谨，用数据说话",
            "content_style": "快节奏干货",
            "target_audience": "25-40岁装修业主",
        },
        "scripts": [
            {
                "title": "全屋定制报价揭秘",
                "text": "你以为花大价钱买的是高端定制，结果拆开一看——一块普普通通的欧松板，出厂价才37.8元，到了你家报价单上，摇身一变成了198元一平米！这中间飞走的160块，是木头？是工艺？还是品牌滤镜？今天我蹲点工厂、翻烂合同、扒了37家全屋定制的真实报价单，把每笔钱流向摊在你面前。",
                "duration": "约75秒",
            },
            {
                "title": "18平老破小改造",
                "text": "18平米，一张单人床的面积，却住进了一对深圳打拼的年轻夫妻。不是将就，而是把老破小玩成了空间魔术！墙面翻下悬浮书桌，入夜收起变温软双人床。沙发掀开是37L储物舱，镜柜后藏着吹风机和发胶。他们没有买更大的房子，只是把每一寸空气都签了劳动合同。",
                "duration": "约65秒",
            },
        ],
    },
    {
        "id": "food",
        "name": "美食探店",
        "icon": "🍜",
        "persona": {
            "name": "美食探店号",
            "industry": "美食探店",
            "role": "美食博主",
            "personality": "亲和力强，画面感十足",
            "content_style": "幽默口语化",
            "target_audience": "18-35岁美食爱好者",
        },
        "scripts": [
            {
                "title": "街边30年苍蝇馆子",
                "text": "这条巷子我路过一百次，从来没注意到这家店——直到有一天，一个米其林大厨跟我说：你信不信，全城最好吃的回锅肉，藏在一个连招牌都没有的苍蝇馆子里。30年老店，老板是个67岁的婆婆，每天只炒30份。今天我带你去看看，什么叫真正的锅气。",
                "duration": "约60秒",
            },
        ],
    },
    {
        "id": "tech",
        "name": "数码评测",
        "icon": "💻",
        "persona": {
            "name": "数码评测号",
            "industry": "科技数码",
            "role": "数码博主",
            "personality": "客观理性，参数党最爱",
            "content_style": "快节奏干货",
            "target_audience": "20-35岁数码爱好者",
        },
        "scripts": [
            {
                "title": "两万八的显卡值不值",
                "text": "朋友们，停！先别急着下单RTX5090——那张被黄牛炒到两万八、散热器重得像砖头的信仰神卡，可能真不是你今年最聪明的选择。我们把AMD RX7900XTX塞进旗舰平台，实测赛博朋克2077光追全开加FSR3帧生成，结果让人沉默。这不是勉强能用，这是真性能平权。",
                "duration": "约80秒",
            },
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
    return {"code": 404, "message": "模板不存在"}
