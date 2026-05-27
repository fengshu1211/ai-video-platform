"""语音系统 API"""
import subprocess
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.models.database import get_db, VoiceProfile
from app.schemas.voice import VoiceProfileOut, TTSRequest
from app.services.tts_service import text_to_speech, MINIMAX_VOICES, clone_voice, _upload_voice_to_siliconflow
from app.config import VOICES_DIR

router = APIRouter(prefix="/api/voice", tags=["voice"])


def get_audio_duration(file_path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(file_path)],
            capture_output=True, text=True, timeout=5,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0


@router.get("/profiles", response_model=list[VoiceProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(VoiceProfile).filter(VoiceProfile.status == "active").all()
    # 首次自动同步MiniMax音色
    preset_count = sum(1 for p in profiles if p.provider == "edge_tts")
    if preset_count == 0:
        for v in MINIMAX_VOICES:
            existing = db.query(VoiceProfile).filter(VoiceProfile.voice_id == v["id"]).first()
            if not existing:
                db.add(VoiceProfile(name=v["name"], provider="minimax", voice_id=v["id"],
                                    gender=v["gender"], style=v["style"]))
        db.commit()
        profiles = db.query(VoiceProfile).filter(VoiceProfile.status == "active").all()
    return profiles


@router.post("/profiles/custom", response_model=VoiceProfileOut)
async def upload_custom_voice(
    name: str = Form(...),
    gender: str = Form("male"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传自定义语音，自动进行声音复刻"""
    ext = Path(file.filename).suffix.lower()
    if ext not in (".mp3", ".wav", ".m4a", ".ogg"):
        raise HTTPException(400, f"不支持的音频格式：{ext}")

    new_name = f"custom_{uuid.uuid4().hex}{ext}"
    file_path = VOICES_DIR / new_name
    content = await file.read()
    file_path.write_bytes(content)

    # 检查时长（CosyVoice推荐≥3秒清晰语音）
    duration = get_audio_duration(file_path)
    if duration > 0 and duration < 2.5:
        file_path.unlink(missing_ok=True)
        raise HTTPException(400, f"音频时长仅 {duration:.1f} 秒，至少需要 3 秒清晰语音")

    # ASR转写参考文本
    ref_text = ""
    try:
        from app.services.asr_service import transcribe_audio
        ref_text = transcribe_audio(file_path)
        file_path.with_suffix(".txt").write_text(ref_text, encoding="utf-8")
    except Exception:
        pass

    # 硅基流动CosyVoice声音复刻（免费，首选）
    sf_voice_uri = None
    provider = "custom"
    is_custom = 1
    voice_id = f"custom:{new_name}"

    if duration >= 3.0 or duration == 0:
        try:
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name.replace(" ", "_"))[:30]
            if not safe_name or safe_name[0].isdigit():
                safe_name = "voice_" + (safe_name or uuid.uuid4().hex[:8])
            if len(safe_name) < 8:
                safe_name = safe_name + "_" + uuid.uuid4().hex[:4]

            # 优先硅基流动（免费）
            sf_voice_uri = _upload_voice_to_siliconflow(file_path, safe_name, ref_text)
            if sf_voice_uri:
                voice_id = sf_voice_uri
                provider = "siliconflow"
                print(f"Voice registered via SiliconFlow: {safe_name}")
            else:
                # 降级MiniMax（付费）
                mm_voice_id = clone_voice(file_path, safe_name)
                if mm_voice_id:
                    voice_id = mm_voice_id
                    provider = "minimax"
        except Exception as e:
            print(f"Clone error: {e}")

    profile = VoiceProfile(
        name=name, provider=provider, voice_id=voice_id,
        gender=gender, is_custom=is_custom,
        custom_sample_path=str(file_path.relative_to(file_path.parent.parent)),
        style="声音复刻" if provider == "minimax" else "自定义",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/profiles/{profile_id}", response_model=VoiceProfileOut)
def update_profile(profile_id: int, name: str = Form(None), gender: str = Form(None), db: Session = Depends(get_db)):
    profile = db.query(VoiceProfile).filter(VoiceProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, "语音不存在")
    if name is not None:
        profile.name = name
    if gender is not None and gender in ("male", "female", "special"):
        profile.gender = gender
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(VoiceProfile).filter(VoiceProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, "语音不存在")
    if profile.is_custom:
        if profile.custom_sample_path:
            (VOICES_DIR.parent / profile.custom_sample_path).unlink(missing_ok=True)
        db.delete(profile)
    else:
        profile.status = "inactive"
    db.commit()
    return {"code": 0, "message": "已删除"}


@router.post("/tts")
def tts_synthesize(data: TTSRequest, db: Session = Depends(get_db)):
    voice = db.query(VoiceProfile).filter(VoiceProfile.id == data.voice_id).first()
    if not voice:
        raise HTTPException(404, "语音不存在")
    audio_path = text_to_speech(data.text, voice.voice_id,
                                reference_sample=voice.custom_sample_path)
    return FileResponse(audio_path, media_type="audio/mpeg", filename=audio_path.name)


@router.get("/profiles/{voice_id}/preview")
def preview_voice(voice_id: int, db: Session = Depends(get_db)):
    """生成试听"""
    voice = db.query(VoiceProfile).filter(VoiceProfile.id == voice_id).first()
    if not voice:
        raise HTTPException(404, "语音不存在")
    audio_path = text_to_speech("你好，我是自媒体创作平台的AI语音助手，这是我的声音效果。",
                                voice.voice_id, reference_sample=voice.custom_sample_path)
    return FileResponse(audio_path, media_type="audio/mpeg")
