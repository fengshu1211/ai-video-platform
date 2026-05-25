"""FastAPI 应用入口"""
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.config import CORS_ORIGINS
from app.models.database import init_db
from app.routers import topics, content, voice, video, tasks, upload, materials, auth, userdata

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# 匹配无时区的 ISO datetime 字符串，自动补 +08:00
_ISO_DT = re.compile(r'"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"')
# 清理 JSON 中非法的 \udXXX 代理对转义序列
_SURROGATE_ESC = re.compile(r'\\u[dD][89aAbBcCdDeEfF][0-9a-fA-F]{2}')

class BeijingJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        raw = super().render(content).decode("utf-8", errors="replace")
        raw = _SURROGATE_ESC.sub("", raw)
        return _ISO_DT.sub(r'"\1+08:00"', raw).encode("utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print(f"init_db failed: {e}")
    # 每周一10:37自动刷新选题
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        scheduler = BackgroundScheduler()
        def weekly_refresh():
            try:
                import requests, json
                tracks_resp = requests.get("http://localhost:8000/api/topics/tracks", timeout=10)
                tracks = tracks_resp.json()
                for t in tracks:
                    requests.post(f"http://localhost:8000/api/topics/hot/refresh?track_id={t['id']}", timeout=30)
            except Exception:
                pass
        # 每小时自动同步用户数据到平台存储
        def hourly_sync():
            try:
                from app.services.sync_service import sync_all_users
                sync_all_users()
            except Exception:
                pass
        scheduler.add_job(weekly_refresh, CronTrigger(day_of_week="mon", hour=10, minute=37))
        scheduler.add_job(hourly_sync, CronTrigger(minute=7))  # 每小时07分
        scheduler.start()
    except Exception:
        pass
    yield


app = FastAPI(title="自媒体创作平台", version="0.2.0", lifespan=lifespan,
              default_response_class=BeijingJSONResponse)

# 用户自定义API Key中间件（线程本地存储，各service通过 get_user_key() 读取）
import threading
_user_keys = threading.local()

@app.middleware("http")
async def user_keys_middleware(request, call_next):
    _user_keys.dashscope = request.headers.get("X-DashScope-Key", "") or os.getenv("DASHSCOPE_API_KEY", "")
    _user_keys.siliconflow = request.headers.get("X-SiliconFlow-Key", "") or os.getenv("SILICONFLOW_API_KEY", "")
    return await call_next(request)

def get_user_key(service: str) -> str:
    """服务层调用此函数获取当前请求用户的API Key"""
    return getattr(_user_keys, service, "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(topics.router)
app.include_router(content.router)
app.include_router(voice.router)
app.include_router(video.router)
app.include_router(tasks.router)
app.include_router(upload.router)
app.include_router(materials.router)
app.include_router(auth.router)
app.include_router(userdata.router)

# 托管前端静态文件 + 上传文件
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
from app.config import UPLOADS_DIR
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.get("/api/health")
def health():
    return {"code": 0, "message": "ok"}

@app.get("/ping")
def ping():
    return {"status": "alive"}

@app.get("/manual.html")
def serve_manual():
    manual = FRONTEND_DIR / "manual.html"
    if manual.exists():
        return FileResponse(manual)
    return {"code": 404, "message": "manual not found"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """兜底——前端SPA路由"""
    if full_path.startswith("api/"):
        return {"code": 404, "message": "not found"}
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"code": 404, "message": "frontend not built, run: cd frontend && npx vite build"}
