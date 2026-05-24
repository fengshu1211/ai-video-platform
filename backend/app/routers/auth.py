"""用户注册登录 + 人设系统"""
import hashlib
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.database import get_db, User, UserPersona

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash(phone: str, pwd: str) -> str:
    return hashlib.sha256(f"{phone}:{pwd}:salt2024".encode()).hexdigest()


class RegisterReq(BaseModel):
    phone: str
    password: str
    display_name: str = ""


class LoginReq(BaseModel):
    phone: str
    password: str


class PersonaReq(BaseModel):
    industry: str = ""       # 行业
    role: str = ""           # 角色/职位
    personality: str = ""    # 性格特征
    hobbies: str = ""        # 兴趣爱好
    content_style: str = ""  # 内容风格偏好
    target_audience: str = ""  # 目标受众


# ── 注册 ──
@router.post("/register")
def register(data: RegisterReq, db: Session = Depends(get_db)):
    if not data.phone or len(data.phone) < 11:
        raise HTTPException(400, "请输入正确的手机号")
    if len(data.password) < 4:
        raise HTTPException(400, "密码至少4位")
    existing = db.query(User).filter(User.phone == data.phone).first()
    if existing:
        raise HTTPException(400, "该手机号已注册")
    user = User(phone=data.phone, password_hash=_hash(data.phone, data.password),
                display_name=data.display_name or f"用户{data.phone[-4:]}")
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"code": 0, "message": "注册成功", "user_id": user.id}


# ── 登录 ──
@router.post("/login")
def login(data: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == data.phone).first()
    if not user or user.password_hash != _hash(data.phone, data.password):
        raise HTTPException(401, "手机号或密码错误")
    user.last_login_at = datetime.now()
    db.commit()
    return {"code": 0, "message": "登录成功", "user_id": user.id,
            "display_name": user.display_name}


# ── 人设分析 ──
@router.post("/persona")
def save_persona(data: PersonaReq, user_id: int, db: Session = Depends(get_db)):
    """保存用户人设，AI分析生成风格模板"""
    persona = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
    if not persona:
        persona = UserPersona(user_id=user_id)
        db.add(persona)

    persona.industry = data.industry
    persona.role = data.role
    persona.personality = data.personality
    persona.hobbies = data.hobbies
    persona.content_style = data.content_style
    persona.target_audience = data.target_audience
    persona.updated_at = datetime.now()

    # AI分析
    try:
        from app.services.ai_service import analyze_persona_style
        result = analyze_persona_style(data.model_dump())
        persona.ai_style_template = json.dumps(result, ensure_ascii=False)
        persona.ai_keywords = json.dumps(result.get("keywords", []), ensure_ascii=False)
    except Exception as e:
        print(f"Persona AI analysis failed: {e}")
        persona.ai_style_template = json.dumps({"error": str(e)}, ensure_ascii=False)

    db.commit()
    db.refresh(persona)

    return {
        "code": 0,
        "message": "人设保存成功",
        "persona": {
            "industry": persona.industry,
            "role": persona.role,
            "style_template": json.loads(persona.ai_style_template or "{}"),
            "keywords": json.loads(persona.ai_keywords or "[]"),
        },
    }


@router.get("/persona")
def get_persona(user_id: int, db: Session = Depends(get_db)):
    persona = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
    if not persona:
        return {"code": 0, "persona": None}
    return {
        "code": 0,
        "persona": {
            "industry": persona.industry, "role": persona.role,
            "personality": persona.personality, "hobbies": persona.hobbies,
            "content_style": persona.content_style,
            "target_audience": persona.target_audience,
            "style_template": json.loads(persona.ai_style_template or "{}"),
            "keywords": json.loads(persona.ai_keywords or "[]"),
        },
    }
