# CLAUDE.md — AI短视频创作平台

## 用户：丰哥

- 自媒体历史类博主，非专业程序员
- 说人话、分步来、少确认、直接做

## 技术栈

- 前端：React 19 + Vite 6 + TypeScript + Ant Design 5
- 后端：Python 3.12 + FastAPI + SQLAlchemy 2.0 + SQLite
- 任务队列：Celery + Redis（Windows用Memurai）
- 视频处理：FFmpeg（subprocess调用）
- AI：通义千问API（文本改写）、火山引擎TTS（语音合成）

## 启动命令

```bash
# Redis（先启动）
memurai-server

# 后端
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Celery Worker
cd backend
celery -A app.tasks.celery_app worker --loglevel=info -P solo

# 前端
cd frontend
npm run dev
```

## 项目架构

```
frontend (React + Ant Design)  <-->  backend (FastAPI + SQLite)
                                        |
                                   Celery Worker (视频生成/内容抓取)
                                        |
                                   FFmpeg (音视频合成)
```

## 重要约定

- Pydantic v2：必须用 List[Any] / Dict[str, Any]，不可裸写 list/dict
- 所有异步任务（视频生成、内容抓取）需要创建 async_tasks 记录并更新进度
- FFmpeg 命令统一封装在 utils/ffmpeg_utils.py，不允许在 service 中直接拼命令
- 视频生成管线顺序：TTS音频 → 计算时长 → 准备素材 → FFmpeg混流 → 烧录字幕
- 前端 axios baseURL = '/api'，Vite dev server 代理到 :8000
- 所有上传文件放在 backend/uploads/ 下按类型分子目录
- 数据库文件 backend/data.db（SQLite），自动创建
