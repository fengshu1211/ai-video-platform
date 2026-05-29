"""视频生成异步任务——全自动管线"""
import json, threading
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.config import DATABASE_URL, OUTPUTS_DIR


def _prepare_and_delegate(project_id: int, task_id: int):
    """服务器端轻活：TTS合成语音 → 标记pending_worker交给本地渲染"""
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    db = Session(engine)
    try:
        from app.models.database import VideoProject, AsyncTask, RewrittenScript, VoiceProfile

        project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
        if not project:
            return

        task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()

        # 获取文案
        script_text = ""
        if project.script_id:
            script = db.query(RewrittenScript).filter(RewrittenScript.id == project.script_id).first()
            if script:
                script_text = script.rewritten_text or script.original_text
        if not script_text:
            if task: task.status = "failed"; task.progress_message = "没有文案"; db.commit()
            return

        # 获取语音参数
        voice_id = "longxiaochun_v2"
        if project.voice_id:
            voice = db.query(VoiceProfile).filter(VoiceProfile.id == project.voice_id).first()
            if voice and voice.voice_id:
                voice_id = voice.voice_id

        # 标记为等待Worker渲染（TTS等重活在Worker本地做）
        if task:
            task.status = "pending_worker"
            task.progress = 10
            task.progress_message = "等待本地渲染..."
            db.commit()

        print(f"[prepare] project #{project_id} -> pending_worker")
    except Exception as e:
        try:
            task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
            if task:
                task.status = "failed"
                task.progress_message = f"准备失败: {str(e)[:100]}"
                db.commit()
        except Exception:
            pass
        print(f"[prepare] failed: {e}")
    finally:
        db.close()
from app.models.database import AsyncTask, VideoProject, RewrittenScript, VoiceProfile


def _get_db():
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    return Session(engine)


def _run_video_generation(project_id: int) -> dict:
    """全自动视频生成管线（无Celery依赖的直接调用版本）"""
    return _generate_video_impl(project_id, _celery_id=f"direct_{project_id}")


def generate_video_task(project_id: int):
    """视频生成任务入口"""
    return _generate_video_impl(project_id, _celery_id=f"task_{project_id}")


def _generate_video_impl(project_id: int, _celery_id: str = "", _db=None):
    """生成管线核心实现（可传入外部DB会话避免锁冲突）"""
    db = _db if _db is not None else _get_db()
    try:
        project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
        if not project:
            return {"status": "failed", "error": "项目不存在"}

        # 获取文案
        script_text = ""
        if project.script_id:
            script = db.query(RewrittenScript).filter(RewrittenScript.id == project.script_id).first()
            if script:
                script_text = script.rewritten_text or script.original_text

        if not script_text:
            return {"status": "failed", "error": "没有找到文案内容"}

        # 获取语音：硅基流动URI直接用 > 自定义样本 > 预设音色
        voice_id = "alex"
        custom_sample = None
        if project.voice_id:
            voice = db.query(VoiceProfile).filter(VoiceProfile.id == project.voice_id).first()
            if voice:
                if voice.voice_id.startswith("speech:") or voice.voice_id.startswith("cosyvoice:"):
                    voice_id = voice.voice_id  # 硅基流动已注册的URI，直接用
                elif voice.is_custom and voice.custom_sample_path:
                    custom_sample = voice.custom_sample_path
                elif voice.voice_id and not voice.voice_id.startswith("custom:"):
                    voice_id = voice.voice_id

        # 任务追踪（取最新记录，避免前端拿到旧任务ID）
        task_record = db.query(AsyncTask).filter(
            AsyncTask.ref_id == project_id, AsyncTask.task_type == "video_generation"
        ).order_by(AsyncTask.id.desc()).first()
        if not task_record:
            task_record = AsyncTask(task_type="video_generation", ref_id=project_id, celery_task_id=_celery_id)
            db.add(task_record)
            db.commit()

        def report(percent: int, msg: str):
            task_record.status = "processing"
            task_record.progress = percent
            task_record.progress_message = msg
            db.commit()

        project.status = "processing"
        db.commit()

        # ─── 1. AI导演分镜：深度理解文案→规划每段素材方案 ───
        report(5, "AI导演正在分析文案...")
        try:
            from app.services.ai_service import plan_visual_materials, extract_keywords_and_mood
            visual_plan = plan_visual_materials(script_text)
            mood_analysis = extract_keywords_and_mood(script_text)
        except Exception as e:
            print(f"[video_tasks] AI导演分镜失败: {e}")
            visual_plan = {"segments": [], "mood": "calm"}
            mood_analysis = {"mood": "calm", "mood_cn": "平静", "scene_type": "historical"}

        mood = visual_plan.get("mood", mood_analysis.get("mood", "calm"))
        mood_cn = mood_analysis.get("mood_cn", "平静")
        segments = visual_plan.get("segments", [])
        overall_theme = visual_plan.get("overall_theme", "")

        # 汇总所有搜索关键词（去重保序）
        all_keywords = []
        for seg in segments:
            for kw in seg.get("keywords_cn", []):
                if kw not in all_keywords:
                    all_keywords.append(kw)
            for kw in seg.get("keywords_en", []):
                if kw not in all_keywords:
                    all_keywords.append(kw)
        if not all_keywords:
            all_keywords = mood_analysis.get("keywords_cn", []) + mood_analysis.get("keywords_en", [])

        report(15, f"AI导演：{overall_theme or '已理解全文'}，{len(segments)}个视觉段落")

        # ─── 2. 获取素材：用户上传优先 → AI生图 → Pexels备用 → 纯色兜底 ───
        material_paths = []

        # 1) 用户上传的素材（优先使用）
        material_paths_json = project.material_paths_json or "[]"
        try:
            user_materials = json.loads(material_paths_json)
        except Exception:
            user_materials = []
        # 校验用户素材是否存在
        valid_user_mats = []
        for mat in user_materials:
            mat_path = Path(__file__).parent.parent.parent / "uploads" / mat
            if mat_path.exists() and mat_path.stat().st_size > 500:
                valid_user_mats.append(mat)
        if valid_user_mats:
            material_paths = [str(m.relative_to(m.parent.parent)) for m in valid_user_mats]
            report(25, f"使用用户上传的 {len(material_paths)} 个素材")

        # 2) 没有用户素材时：直接走纯色背景（不调AI生图，不搜海外图库）
        if not material_paths:
            report(20, "没有上传素材，将使用品牌背景")

        report(45, f"共准备 {len(material_paths)} 个素材")

        # ─── 3. 自动匹配BGM        report(45, f"共准备 {len(material_paths)} 个素材")

        # ─── 3. 自动匹配BGM ───
        bgm_path = project.bgm_path
        if not bgm_path:
            from app.services.bgm_service import get_bgm_for_mood
            bgm_path = get_bgm_for_mood(mood)
            if bgm_path:
                report(45, f"自动匹配BGM：{mood_cn}风格")
            else:
                report(45, f"未找到{mood_cn}风格BGM，跳过（可上传bgm_{mood_cn}.mp3自定义）")

        # ─── 4. 对口型预处理 ───
        lip_sync_video = None
        face_video_path = None
        if project.lip_sync_enabled:
            # 找上传的人脸素材（跳过AI生成的ai_*.png场景图）
            face_exts = ('.mp4', '.mov', '.avi', '.webm')
            if project.lip_sync_mode in ('digital_human', 'virtual_host'):
                face_exts = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.mp4', '.mov', '.avi', '.webm')
            for mat in list(material_paths):
                # 跳过AI生成的场景图
                if "ai_" in mat and not project.lip_sync_mode in ('digital_human',):
                    continue
                if mat.lower().endswith(face_exts):
                    from pathlib import Path
                    fp = Path(mat)
                    if not fp.is_absolute():
                        fp = Path(__file__).parent.parent.parent / "uploads" / mat
                    if fp.exists():
                        face_video_path = fp
                        material_paths.remove(mat)
                        break
            # 如果移除人脸素材后没有背景了，生成AI图（主视频模式除外）
            if not material_paths and (not face_video_path or project.lip_sync_mode != "full"):
                report(35, "AI正在生成历史场景背景...")
                try:
                    from app.services.image_service import generate_scene_images
                    ai_bg = generate_scene_images(script_text, count=3)
                    for img in ai_bg:
                        material_paths.append(str(img.relative_to(
                            Path(__file__).parent.parent.parent / "uploads")))
                    report(40, f"AI生成了 {len(ai_bg)} 张背景图")
                except Exception:
                    pass

        # ─── 5. 视频合成 ───
        report(60, "开始视频合成...")
        from app.services.video_service import generate_video

        output_path = generate_video(
            script_text=script_text,
            voice_id=voice_id,
            custom_voice_sample=custom_sample,
            bgm_path=bgm_path,
            bgm_volume=project.bgm_volume or 0.3,
            material_paths=material_paths,
            lip_sync_video=str(face_video_path.relative_to(Path(__file__).parent.parent.parent / "uploads")) if face_video_path else None,
            lip_sync_mode=project.lip_sync_mode or "pip",
            aspect_ratio=project.aspect_ratio or "9:16",
            subtitle_enabled=bool(project.subtitle_enabled),
            image_animation_type=project.image_animation_type,
            subtitle_animation=project.subtitle_animation or "fade",
            progress_callback=report,
        )

        project.status = "completed"
        project.output_path = str(output_path.relative_to(output_path.parent.parent))
        from app.utils.ffmpeg_utils import get_media_duration
        project.duration_seconds = get_media_duration(output_path)

        # 自动同步到平台存储
        try:
            from app.services.sync_service import auto_sync_video
            auto_sync_video(project.output_path)
        except Exception:
            pass

        task_record.status = "completed"
        task_record.progress = 100
        task_record.progress_message = "视频生成完成"
        task_record.result_json = json.dumps({"output_path": project.output_path}, ensure_ascii=False)
        db.commit()

        return {"status": "completed", "project_id": project_id}

    except Exception as e:
        try:
            db.rollback()
            project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
            if project:
                project.status = "failed"
            task_rec = db.query(AsyncTask).filter(
                AsyncTask.ref_id == project_id, AsyncTask.task_type == "video_generation"
            ).first()
            if task_rec:
                task_rec.status = "failed"
                task_rec.progress_message = str(e)[:200]
            db.commit()
        except Exception:
            pass
        print(f"generate_video_task failed: {e}")
        return {"status": "failed", "error": str(e)[:200]}
    finally:
        db.close()


def _search_and_download(keywords: list[str], material_paths: list[str]):
    """Pexels+Pixabay双源搜索视频素材并下载"""
    from app.services.material_service import search_videos, download_video
    searched_ids = set()
    for kw in keywords[:5]:
        try:
            results = search_videos(kw, per_page=3)
            if not results:
                print(f"[video_tasks] 视频搜索'{kw}'无结果")
                continue
            for v in results:
                if v["id"] not in searched_ids:
                    searched_ids.add(v["id"])
                    try:
                        path = download_video(v["download_url"], v["id"])
                        if path and path.stat().st_size > 1000:
                            material_paths.append(str(path.relative_to(path.parent.parent)))
                    except Exception as e:
                        print(f"[video_tasks] 下载视频失败 {v.get('id')}: {e}")
            if len(material_paths) >= 5:
                break
        except Exception as e:
            print(f"[video_tasks] 视频搜索'{kw}'异常: {e}")
