"""爆款选题 API"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db, Track, HotTopic
from app.schemas.topic import TrackCreate, TrackOut, HotTopicOut

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("/tracks", response_model=list[TrackOut])
def list_tracks(db: Session = Depends(get_db)):
    return db.query(Track).filter(Track.is_active == 1).all()


@router.post("/tracks", response_model=TrackOut)
def create_track(data: TrackCreate, db: Session = Depends(get_db)):
    track = Track(**data.model_dump())
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


@router.get("/hot", response_model=list[HotTopicOut])
def list_hot_topics(track_id: int | None = None, platform: str | None = None, db: Session = Depends(get_db)):
    q = db.query(HotTopic).filter(HotTopic.status == "active")
    if track_id:
        q = q.filter(HotTopic.track_id == track_id)
    if platform:
        q = q.filter(HotTopic.platform == platform)
    return q.order_by(HotTopic.created_at.desc()).limit(10).all()


@router.post("/hot/refresh", response_model=list[HotTopicOut])
def refresh_hot_topics(track_id: int, db: Session = Depends(get_db)):
    """AI实时分析生成爆款选题"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(404, "赛道不存在")

    # 归档旧选题
    db.query(HotTopic).filter(HotTopic.track_id == track_id).update({"status": "archived"})

    # AI生成新选题
    from app.services.topic_service import generate_hot_topics
    try:
        items = generate_hot_topics(track.name, count=8)
    except Exception as e:
        raise HTTPException(500, f"AI生成选题失败：{e}")

    new_topics = []
    for item in items:
        topic = HotTopic(
            track_id=track_id,
            title=item["title"],
            platform=item.get("platform", "douyin"),
            metrics_json=json.dumps(item.get("metrics", {}), ensure_ascii=False),
            ai_analysis=item.get("analysis", ""),
        )
        db.add(topic)
        new_topics.append(topic)

    db.commit()
    for t in new_topics:
        db.refresh(t)
    return new_topics


@router.get("/hot/{topic_id}", response_model=HotTopicOut)
def get_hot_topic(topic_id: int, db: Session = Depends(get_db)):
    return db.query(HotTopic).filter(HotTopic.id == topic_id).first()
