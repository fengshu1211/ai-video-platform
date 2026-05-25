"""新手模板 - persona presets and sample scripts"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/templates", tags=["templates"])

PERSONA_TEMPLATES = [
    {
        "id": "history",
        "name": "History Blogger",
        "icon": "temple",
        "persona": {
            "name": "History Channel",
            "industry": "History & Archaeology",
            "specialization": "",
            "brand_name": "",
            "role": "History Content Creator",
            "personality": "Humorous, storytelling style",
            "features": "",
            "content_style": "story",
            "target_audience": "History enthusiasts 25-45",
        },
        "scripts": [
            {"title": "Emperor Qin's Underground Palace", "duration": "90s",
             "text": "The Mausoleum of Qin Shi Huang was never the mercury-filled death trap of legend. New 3D laser scanning reveals a 9-tier palace stacked upward beneath the 76-meter mound, with quantum magnetometry detecting anomalous ring structures and sealed chambers. This is the answer archaeology has been waiting decades for."},
        ],
    },
    {
        "id": "home",
        "name": "Home Design",
        "icon": "home",
        "persona": {
            "name": "Home Renovation",
            "industry": "Home Improvement & Interior Design",
            "specialization": "",
            "brand_name": "",
            "role": "Interior Designer",
            "personality": "Professional, data-driven",
            "features": "",
            "content_style": "fast_facts",
            "target_audience": "Homeowners & renovators 25-40",
        },
        "scripts": [
            {"title": "Custom Cabinetry Price Breakdown", "duration": "75s",
             "text": "A plain OSB board costs 37.8 yuan from the factory. By the time it reaches your quotation sheet, it's 198 yuan per square meter. Where did that 160 yuan go? We visited factories, analyzed 37 real quotations, and traced every single cost."},
        ],
    },
    {
        "id": "food",
        "name": "Food Reviews",
        "icon": "utensils",
        "persona": {
            "name": "Food Channel",
            "industry": "Food & Dining",
            "specialization": "",
            "brand_name": "",
            "role": "Food Blogger",
            "personality": "Warm, vivid descriptions",
            "features": "",
            "content_style": "humorous",
            "target_audience": "Food lovers 18-35",
        },
        "scripts": [
            {"title": "30-Year Hidden Gem Restaurant", "duration": "60s",
             "text": "A Michelin chef once told me the best twice-cooked pork in town is hidden in an alley restaurant with no sign. 30 years old, run by a 67-year-old grandma who only cooks 30 portions a day. This is what real wok hei tastes like."},
        ],
    },
    {
        "id": "tech",
        "name": "Tech Reviews",
        "icon": "laptop",
        "persona": {
            "name": "Tech Channel",
            "industry": "Technology & Gadgets",
            "specialization": "",
            "brand_name": "",
            "role": "Tech Reviewer",
            "personality": "Objective, data-focused",
            "features": "",
            "content_style": "fast_facts",
            "target_audience": "Tech enthusiasts 20-35",
        },
        "scripts": [
            {"title": "Is the RTX5090 Worth 28000 Yuan?", "duration": "80s",
             "text": "Stop before you click buy on that RTX5090 - the faith card inflated to 28000 yuan by scalpers. We benchmarked the RX7900XTX against it in Cyberpunk 2077 with full ray tracing and FSR3 frame gen. The results will surprise you."},
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
