"""预置语音数据"""
from app.models.database import init_db, Session, engine
from app.models.database import VoiceProfile

init_db()
db = Session(engine)

voices = [
    {"name": "沉稳男声-李明", "provider": "huoshan", "voice_id": "BV001_streaming", "gender": "male", "style": "沉稳"},
    {"name": "激昂男声-张伟", "provider": "huoshan", "voice_id": "BV002_streaming", "gender": "male", "style": "激昂"},
    {"name": "温柔女声-小美", "provider": "huoshan", "voice_id": "BV003_streaming", "gender": "female", "style": "温柔"},
    {"name": "活泼女声-小优", "provider": "huoshan", "voice_id": "BV004_streaming", "gender": "female", "style": "活泼"},
    {"name": "知性女声-云希", "provider": "azure", "voice_id": "zh-CN-XiaoxiaoNeural", "gender": "female", "style": "知性"},
    {"name": "磁性男声-云野", "provider": "azure", "voice_id": "zh-CN-YunyeNeural", "gender": "male", "style": "磁性"},
    {"name": "新闻男声-云扬", "provider": "azure", "voice_id": "zh-CN-YunyangNeural", "gender": "male", "style": "新闻"},
    {"name": "情感女声-晓晓", "provider": "azure", "voice_id": "zh-CN-XiaohanNeural", "gender": "female", "style": "情感"},
]

for v in voices:
    existing = db.query(VoiceProfile).filter(VoiceProfile.voice_id == v["voice_id"]).first()
    if not existing:
        db.add(VoiceProfile(**v))

db.commit()
db.close()
print(f"预置语音完成：{len(voices)} 种")
