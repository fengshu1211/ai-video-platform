#!/bin/bash
# SadTalker AutoDL 一键部署脚本
# 在AutoDL容器实例启动后运行此脚本

set -e

echo "=== 安装系统依赖 ==="
apt-get update && apt-get install -y ffmpeg wget git python3-pip libgl1 libglib2.0-0

echo "=== 克隆SadTalker ==="
cd /root
git clone https://github.com/OpenTalker/SadTalker.git || true
cd SadTalker

echo "=== 安装Python依赖 ==="
pip install -r requirements.txt
pip install flask

echo "=== 下载预训练模型 ==="
mkdir -p checkpoints
bash scripts/download_models.sh

echo "=== 创建API服务 ==="
cat > /root/SadTalker/api_server.py << 'PYEOF'
"""SadTalker HTTP API — 接收照片+音频，返回数字人说话视频"""
from flask import Flask, request, send_file
import subprocess, tempfile, os
from pathlib import Path

app = Flask(__name__)
WORK_DIR = Path("/root/SadTalker")
OUTPUT_DIR = WORK_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/process", methods=["POST"])
def process():
    photo = request.files.get("photo")
    audio = request.files.get("audio")
    if not photo or not audio:
        return {"error": "需要photo和audio文件"}, 400

    photo_path = OUTPUT_DIR / f"input_photo_{photo.filename}"
    audio_path = OUTPUT_DIR / f"input_audio_{audio.filename}"
    output_path = OUTPUT_DIR / "output_video.mp4"

    photo.save(str(photo_path))
    audio.save(str(audio_path))

    # 音频转WAV
    wav_path = OUTPUT_DIR / "input_audio.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-ar", "16000", "-ac", "1", str(wav_path)
    ], check=True)

    # 运行SadTalker
    subprocess.run([
        "python", "inference.py",
        "--driven_audio", str(wav_path),
        "--source_image", str(photo_path),
        "--result_dir", str(OUTPUT_DIR),
        "--still",
        "--preprocess", "full",
        "--enhancer", "gfpgan",
    ], check=True, cwd=str(WORK_DIR))

    # 找到最新生成的视频
    results = sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if results:
        return send_file(results[0], mimetype="video/mp4")
    return {"error": "生成失败"}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
PYEOF

echo "=== 部署完成 ==="
echo "启动API: python /root/SadTalker/api_server.py"
echo "测试: curl http://localhost:8090/health"
echo ""
echo "注意: 模型下载可能较慢，如果失败请手动下载放到 checkpoints/"
