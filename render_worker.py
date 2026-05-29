"""本地渲染Agent — 本地TTS + HyperFrames渲染，只从服务器拉任务、回传结果"""
import requests, json, time, os, shutil, sys
from pathlib import Path

SERVER = "http://47.109.78.122"
WORK_DIR = Path(__file__).parent / "render_work"
POLL_INTERVAL = 5

sys.path.insert(0, str(Path(__file__).parent / "backend"))

def log(msg):
    print(f"[Worker] {msg}", flush=True)

def render_one(task):
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
            url = f"{SERVER}/uploads/{m}"
            local = work / Path(m).name
            try:
                r = requests.get(url, timeout=30)
                local.write_bytes(r.content)
                local_mats.append(str(local))
            except Exception as e:
                log(f"  下载素材失败 {m}: {e}")

        # 2. 本地 TTS 合成
        from app.services.tts_service import text_to_speech
        from app.services.video_service import _clean_spoken_text
        script_text = task["script_text"]
        voice_id = task.get("voice_id") or "longxiaochun_v2"
        spoken = _clean_spoken_text(script_text)
        audio_path = text_to_speech(spoken, voice_id, return_subtitles=False)

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
