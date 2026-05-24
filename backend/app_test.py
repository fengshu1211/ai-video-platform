from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"status": "ok", "message": "Hello from Render!"}

@app.get("/api/health")
def health():
    return {"code": 0, "message": "ok"}

@app.get("/ping")
def ping():
    return {"pong": True}
