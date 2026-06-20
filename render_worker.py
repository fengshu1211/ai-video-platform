"""本地渲染Agent — 本地TTS + HyperFrames渲染，只从服务器拉任务、回传结果"""
# Windows GBK 编码修复：必须在任何import之前强制设置
import os, sys
os.environ['PYTHONIOENCODING'] = 'utf-8'
# 重新加载 subprocess 模块使编码生效
if 'subprocess' in sys.modules:
    del sys.modules['subprocess']

import requests, json, time, shutil
from pathlib import Path

# 素材索引（自动匹配的素材从这里取源文件）
MATERIAL_INDEX = Path(r"D:\全屋定制\圣栎美家文件夹\素材索引.json")
_material_index_cache = None

def _load_mat_index():
    global _material_index_cache
    if _material_index_cache is None and MATERIAL_INDEX.exists():
        with open(MATERIAL_INDEX, "r", encoding="utf-8") as f:
            _material_index_cache = json.load(f)
    return _material_index_cache

def _resolve_auto_material(name: str) -> str | None:
    """从素材索引中找到本地源文件路径"""
    idx = _load_mat_index()
    if not idx:
        return None
    for m in idx.get("materials", []):
        if m["name"] == name:
            src = m.get("src", "")
            if src and Path(src).exists():
                return src
    return None

# 第一个参数指定服务器地址，默认连云端
# python render_worker.py                    → 连 47.109.78.122
# python render_worker.py local              → 连 localhost:8000
import sys
SERVER = "http://localhost:8000" if len(sys.argv) > 1 and sys.argv[1] == "local" else "http://47.109.78.122"
WORK_DIR = Path(__file__).parent / "render_work"
POLL_INTERVAL = 5

sys.path.insert(0, str(Path(__file__).parent / "backend"))

def log(msg):
    print(f"[Worker] {msg}", flush=True)


def render_one(task):
    """本地渲染入口：根据task_type分派"""
    if task.get("task_type") == "quick_video":
        return _render_quick_video(task)
    return _render_hf_video(task)


def _render_quick_video(task):
    """快速出片：调用pipeline_v1.py"""
    import subprocess as _sp
    tid = task["task_id"]
    log(f"QuickVideo #{tid}: {task.get('title','?')}")
    script = task.get("script_text", "")
    if not script:
        log("  no script")
        return {"status": "failed", "error": "no script"}
    qp = task.get("quick_params", {})
    output = WORK_DIR / f"qv_{tid}.mp4"
    pp = Path(r"D:\全屋定制\圣栎美家文件夹\知识库\素材入库工具\pipeline_v1.py")
    cmd = ["python", str(pp), "--script", script, "--output", str(output)]
    if qp.get("brand"): cmd.append("--brand")
    if task.get("materials"):
        for m in task["materials"]: cmd.extend(["--素材", m])
    log("  running pipeline...")
    r = _sp.run(cmd, capture_output=True, timeout=600)
    if output.exists():
        log(f"  ok ({output.stat().st_size/1024/1024:.1f}MB)")
        return {"status": "completed", "output_path": str(output)}
    return {"status": "failed", "error": r.stderr.decode(errors="replace")[:200]}


def _render_hf_video(task):
    """HyperFrames渲染"""

    """本地渲染：TTS + HyperFrames（HTML/CSS/GSAP → 无头浏览器 → MP4）"""
    tid = task["task_id"]
    pid = task["project_id"]
    work = WORK_DIR / f"task_{tid}"
    work.mkdir(parents=True, exist_ok=True)

    try:
        log(f"Task #{tid}: {task.get('title','?')}")

        # 1. 下载素材文件
        materials = task.get("materials", [])
        local_mats = []
        for m in materials:
            # 自动匹配的素材（_auto/前缀）从本地索引取源文件
            if m.startswith("_auto/"):
                src = _resolve_auto_material(Path(m).name)
                if src:
                    local = work / Path(m).name
                    shutil.copy2(src, local)
                    local_mats.append(str(local))
                    log(f"  自动素材: {Path(m).name} ({Path(src).stat().st_size//1024}KB)")
                else:
                    log(f"  自动素材未找到: {m}")
                continue
            # 普通上传素材从服务器下载
            local = work / Path(m).name
            try:
                r = requests.get(f"{SERVER}/uploads/{m}", timeout=30)
                local.write_bytes(r.content)
                local_mats.append(str(local))
            except Exception as e:
                log(f"  下载素材失败 {m}: {e}")

        # 2. 本地 TTS 合成（按任务声音设置选 Edge-TTS 对应声线）
        from app.services.tts_service import _edge_tts_segmented, text_to_speech
        from app.services.video_service import _clean_spoken_text
        script_text = task["script_text"]
        spoken = _clean_spoken_text(script_text)
        voice_id = task.get("voice_id", "") or ""
        # 各声音平台 → Edge-TTS 声线映射
        VOICE_MAP = {
            "longxiaoxia": "zh-CN-XiaoxiaoNeural",
            "longxiaochun": "zh-CN-XiaoyiNeural",
            "longxiaobai": "zh-CN-YunxiNeural",
            "longxiaocheng": "zh-CN-YunjianNeural",
            "longwan": "zh-CN-XiaoyiNeural",
            "longanran": "zh-CN-XiaohanNeural",
            "sambert-zhimao": "zh-CN-XiaoxiaoNeural",
            "sambert-zhichu": "zh-CN-YunjianNeural",
        }
        edge_voice = "zh-CN-XiaoxiaoNeural"
        # 自定义声音（speech:）→ 默认女声
        if voice_id.startswith("speech:") or voice_id.startswith("cosyvoice:"):
            edge_voice = "zh-CN-XiaoxiaoNeural"
        else:
            for ds_key, ev in VOICE_MAP.items():
                if ds_key in voice_id:
                    edge_voice = ev
                    break
        # 先尝试 text_to_speech（用任务声音，需API Key）
        try:
            audio_path = text_to_speech(spoken, voice_id, return_subtitles=False)
            log(f"  TTS with voice {voice_id}")
        except Exception:
            log(f"  TTS voice {voice_id} failed, using Edge-TTS ({edge_voice})")
            audio_path = _edge_tts_segmented(spoken, edge_voice)

        # 3. HyperFrames 渲染
        from app.services.hf_render import generate_hf_video
        output = generate_hf_video(
            script_text=spoken,
            tts_audio_path=str(audio_path),
            material_paths=local_mats if local_mats else None,
            bgm_vol=0.1,
            brand=task.get("brand", "圣栎美家"),
            work_dir=str(work),
        )
        log(f"  HF done: {output.stat().st_size // 1024}KB")

        # 4. 上传
        with open(output, "rb") as f:
            r = requests.post(f"{SERVER}/api/upload/file?file_type=videos",
                files={"file": (output.name, f, "video/mp4")}, timeout=120)
        if r.status_code == 200 and r.json().get("code") == 0:
            outpath = r.json()["data"]["path"]
            requests.post(f"{SERVER}/api/tasks/{tid}/done", json={
                "status": "completed", "progress": 100,
                "progress_message": "HyperFrames渲染完成",
                "result_json": json.dumps({"output_path": outpath}),
            })
            log(f"  Uploaded: {outpath}")
        else:
            log(f"  Upload failed: {r.status_code} {r.text[:100]}")

    except Exception as e:
        log(f"  FAILED: {e}")
        try:
            requests.post(f"{SERVER}/api/tasks/{tid}/done", json={
                "status": "failed", "progress_message": str(e)[:200]
            })
        except Exception:
            pass
    finally:
        shutil.rmtree(work, ignore_errors=True)

def main():
    log("HyperFrames Worker启动，轮询任务...")
    while True:
        try:
            r = requests.get(f"{SERVER}/api/tasks/pending_worker", timeout=5)
            if r.status_code != 200:
                time.sleep(POLL_INTERVAL)
                continue
            tasks = r.json().get("tasks", [])
            for task in tasks:
                render_one(task)
                break
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            log(f"轮询异常: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
