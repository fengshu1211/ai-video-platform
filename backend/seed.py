"""预置初始数据：赛道 + 示例爆款选题"""
import json
from app.models.database import init_db, Session, engine
from app.models.database import Track, HotTopic

init_db()
db = Session(engine)

# ── 赛道 ──
tracks_data = [
    {"name": "历史解说", "description": "历史事件、人物传记、朝代更迭类内容"},
    {"name": "情感故事", "description": "情感经历、人际关系、两性话题"},
    {"name": "科普知识", "description": "自然科学、生活常识、冷知识"},
    {"name": "美食探店", "description": "美食制作、餐厅测评、饮食文化"},
    {"name": "军事评论", "description": "军事历史、武器装备、战略分析"},
]

tracks = []
for t in tracks_data:
    existing = db.query(Track).filter(Track.name == t["name"]).first()
    if existing:
        tracks.append(existing)
    else:
        track = Track(**t)
        db.add(track)
        db.flush()
        tracks.append(track)

# ── 爆款选题 ──
topic_samples = [
    {
        "track": "历史解说",
        "title": "如果秦始皇统一了全世界，现在的世界会是什么样？",
        "platform": "douyin",
        "metrics": {"views": 5200000, "likes": 320000, "comments": 18000, "shares": 65000},
        "analysis": "假设性历史选题，极强的话题性和讨论度，适合做系列内容",
    },
    {
        "track": "历史解说",
        "title": "明朝灭亡的真正原因：不是李自成，而是小冰河期",
        "platform": "douyin",
        "metrics": {"views": 3800000, "likes": 258000, "comments": 22000, "shares": 48000},
        "analysis": "颠覆传统认知，有数据支撑的历史分析类内容最容易出爆款",
    },
    {
        "track": "历史解说",
        "title": "清朝12位皇帝的一句话总结，乾隆最狂，溥仪最惨",
        "platform": "kuaishou",
        "metrics": {"views": 4100000, "likes": 290000, "comments": 35000, "shares": 72000},
        "analysis": "盘点类+对比类，信息密度高，适合短视频口播形式",
    },
    {
        "track": "情感故事",
        "title": "结婚十年才明白：门当户对比爱情更重要",
        "platform": "xiaohongshu",
        "metrics": {"views": 2800000, "likes": 185000, "comments": 42000, "shares": 56000},
        "analysis": "婚恋话题天然高互动，观点鲜明+亲身经历最有说服力",
    },
    {
        "track": "科普知识",
        "title": "为什么古代的银子是灰色的，电视剧里都是白的？",
        "platform": "douyin",
        "metrics": {"views": 6500000, "likes": 420000, "comments": 15000, "shares": 89000},
        "analysis": "日常现象切入，反差感强，打破认知盲点",
    },
    {
        "track": "军事评论",
        "title": "抗美援朝：志愿军用三三制战术打败了17国联军",
        "platform": "douyin",
        "metrics": {"views": 7200000, "likes": 480000, "comments": 28000, "shares": 95000},
        "analysis": "爱国主义+战术细节，历史类流量密码，正能量高赞",
    },
]

for ts in topic_samples:
    track = next((t for t in tracks if t.name == ts["track"]), None)
    if not track:
        continue
    existing = db.query(HotTopic).filter(HotTopic.title == ts["title"]).first()
    if not existing:
        topic = HotTopic(
            track_id=track.id,
            title=ts["title"],
            platform=ts["platform"],
            metrics_json=json.dumps(ts["metrics"], ensure_ascii=False),
            ai_analysis=ts["analysis"],
        )
        db.add(topic)

db.commit()
db.close()
print(f"预置数据完成：{len(tracks)} 条赛道，{len(topic_samples)} 条爆款选题")
