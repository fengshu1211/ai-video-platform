@echo off
cd /d "D:\应用开发项目集\AI短视频创作平台项目\backend"
python -c "import sys; sys.path.insert(0, '.'); from app.tasks.video_tasks import _run_video_generation; print(_run_video_generation(%1))"
