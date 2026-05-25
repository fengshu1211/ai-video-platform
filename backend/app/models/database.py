"""所有数据库表定义"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship, Session
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI依赖注入：获取数据库会话"""
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表，并执行轻量级迁移"""
    Base.metadata.create_all(engine)
    # 迁移：为 video_projects 添加 image_animation_type 列（如果不存在）
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE video_projects ADD COLUMN image_animation_type VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE video_projects ADD COLUMN subtitle_animation VARCHAR(20) DEFAULT 'fade'"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE video_projects ADD COLUMN collected INTEGER DEFAULT 0"))
            conn.commit()
        except Exception:
            pass
    # 一次性迁移：旧 UTC 数据转北京时间（+8h）
    from sqlalchemy import text as _tx
    with engine.connect() as conn:
        for table in ["video_projects", "rewritten_scripts", "hot_topics",
                      "voice_profiles", "tracks", "users", "async_tasks"]:
            for col in ["created_at", "updated_at"]:
                try:
                    conn.execute(_tx(f"UPDATE {table} SET {col}=datetime({col},'+8 hours') WHERE {col} IS NOT NULL"))
                except Exception:
                    pass
        conn.commit()

# ──────────────── 用户表 ────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(200))
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    last_login_at = Column(DateTime)


# ──────────────── 用户人设表 ────────────────
class UserPersona(Base):
    __tablename__ = "user_personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100), default="未命名")
    industry = Column(String(100))
    role = Column(String(100))
    personality = Column(Text)
    hobbies = Column(Text)
    content_style = Column(Text)
    target_audience = Column(String(200))
    ai_style_template = Column(Text)  # AI分析的专属风格模板JSON
    ai_keywords = Column(Text)        # AI提取的关键词标签
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ──────────────── 赛道表 ────────────────
class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)


# ──────────────── 爆款选题表 ────────────────
class HotTopic(Base):
    __tablename__ = "hot_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    platform = Column(String(50))
    title = Column(String(500), nullable=False)
    source_url = Column(String(1000))
    metrics_json = Column(Text, default="{}")
    ai_analysis = Column(Text)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)

    track = relationship("Track")


# ──────────────── 改写文案表 ────────────────
class RewrittenScript(Base):
    __tablename__ = "rewritten_scripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("hot_topics.id"))
    original_text = Column(Text, nullable=False)
    rewritten_text = Column(Text, nullable=False)
    rewrite_prompt = Column(Text)
    style = Column(String(50), default="similar")  # similar / original / aggressive
    word_count = Column(Integer, default=0)
    is_approved = Column(Integer, default=0)
    source_type = Column(String(50), default="manual")  # manual / link
    source_url = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)

    topic = relationship("HotTopic")


# ──────────────── 语音配置表 ────────────────
class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)  # huoshan / azure / custom
    voice_id = Column(String(200), nullable=False)
    gender = Column(String(10))
    style = Column(String(50))
    sample_url = Column(String(500))
    is_custom = Column(Integer, default=0)
    custom_sample_path = Column(String(500))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)


# ──────────────── 视频项目表 ────────────────
class VideoProject(Base):
    __tablename__ = "video_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    script_id = Column(Integer, ForeignKey("rewritten_scripts.id"))
    voice_id = Column(Integer, ForeignKey("voice_profiles.id"))
    bgm_path = Column(String(500))
    bgm_volume = Column(Float, default=0.3)
    material_paths_json = Column(Text, default="[]")
    aspect_ratio = Column(String(20), default="9:16")  # 9:16竖版 / 16:9横版 / 1:1方形
    subtitle_enabled = Column(Integer, default=1)
    lip_sync_enabled = Column(Integer, default=0)  # 0=关闭 1=Wav2Lip对口型
    lip_sync_mode = Column(String(10), default="pip")  # pip=画中画 / full=主视频全屏
    image_animation_type = Column(String(20))  # zoom_in/zoom_out/pan_left/pan_right/pan_up/pan_down
    subtitle_animation = Column(String(20), default="fade")  # fade/slide_up/pop/none
    collected = Column(Integer, default=0)  # 0=未收藏 1=已收藏到成品库
    status = Column(String(30), default="draft")  # draft/processing/completed/failed
    output_path = Column(String(500))
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    script = relationship("RewrittenScript")
    voice = relationship("VoiceProfile")


# ──────────────── 异步任务追踪表 ────────────────
class AsyncTask(Base):
    __tablename__ = "async_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False)  # video_generation / scraping / tts
    ref_id = Column(Integer)
    celery_task_id = Column(String(200))
    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    progress = Column(Integer, default=0)
    progress_message = Column(String(500))
    error_message = Column(Text)
    result_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
