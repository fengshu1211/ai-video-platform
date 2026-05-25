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
    persona_id: int = 0
    name: str = ""
    industry: str = ""
    specialization: str = ""  # 细分领域
    brand_name: str = ""      # 品牌名称
    role: str = ""
    personality: str = ""
    hobbies: str = ""
    features: str = ""        # 产品特点/卖点
    content_style: str = ""
    target_audience: str = ""


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


# ── 人设管理（最多3个）──
@router.post("/persona")
def save_persona(data: PersonaReq, user_id: int, db: Session = Depends(get_db)):
    """保存/更新用户人设，AI分析生成风格模板"""
    if data.persona_id:
        persona = db.query(UserPersona).filter(UserPersona.id == data.persona_id, UserPersona.user_id == user_id).first()
        if not persona:
            raise HTTPException(404, "人设不存在")
    else:
        count = db.query(UserPersona).filter(UserPersona.user_id == user_id).count()
        if count >= 3:
            raise HTTPException(400, "最多创建3个人设")
        persona = UserPersona(user_id=user_id)
        db.add(persona)

    persona.industry = data.industry or persona.industry if hasattr(persona, 'industry') else data.industry
    persona.specialization = data.specialization
    persona.brand_name = data.brand_name
    persona.role = data.role
    persona.personality = data.personality
    persona.hobbies = data.hobbies
    persona.features = data.features
    persona.content_style = data.content_style
    persona.target_audience = data.target_audience
    if data.name:
        persona.name = data.name
    persona.updated_at = datetime.now()

    try:
        from app.services.ai_service import analyze_persona_style
        result = analyze_persona_style(data.model_dump())
        persona.ai_style_template = json.dumps(result, ensure_ascii=False)
        persona.ai_keywords = json.dumps(result.get("keywords", []), ensure_ascii=False)
    except Exception as e:
        print(f"Persona AI analysis failed: {e}")

    db.commit()
    db.refresh(persona)
    return {"code": 0, "message": "人设保存成功", "persona_id": persona.id,
            "style_template": json.loads(persona.ai_style_template or "{}")}


@router.get("/persona")
def list_personas(user_id: int, db: Session = Depends(get_db)):
    personas = db.query(UserPersona).filter(UserPersona.user_id == user_id).all()
    return {"code": 0, "personas": [{
        "id": p.id, "name": getattr(p, 'name', '未命名'),
        "industry": p.industry, "specialization": getattr(p, 'specialization', ''),
        "brand_name": getattr(p, 'brand_name', ''),
        "role": p.role, "personality": p.personality,
        "features": getattr(p, 'features', ''),
        "content_style": p.content_style, "target_audience": p.target_audience,
        "style_template": json.loads(p.ai_style_template or "{}"),
        "keywords": json.loads(p.ai_keywords or "[]"),
    } for p in personas]}


@router.delete("/persona/{persona_id}")
def delete_persona(persona_id: int, user_id: int, db: Session = Depends(get_db)):
    persona = db.query(UserPersona).filter(UserPersona.id == persona_id, UserPersona.user_id == user_id).first()
    if not persona:
        raise HTTPException(404, "人设不存在")
    db.delete(persona)
    db.commit()
    return {"code": 0, "message": "已删除"}
