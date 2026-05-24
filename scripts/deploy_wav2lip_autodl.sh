#!/bin/bash
# Wav2Lip AutoDL 一键部署脚本
# 在AutoDL容器实例启动后运行此脚本

set -e

echo "=== 安装系统依赖 ==="
apt-get update && apt-get install -y ffmpeg wget git python3-pip

echo "=== 克隆Wav2Lip ==="
cd /root
git clone https://github.com/Rudrabha/Wav2Lip.git || true
cd Wav2Lip

echo "=== 安装Python依赖 ==="
pip install -r requirements.txt
pip install flask gdown

echo "=== 下载预训练模型 ==="
mkdir -p checkpoints
cd checkpoints
# Wav2Lip主模型
gdown "https://drive.google.com/uc?id=1t3bb6Mz0jRqjM7q7s6Xw7kFn1yJ8Xm5L" -O wav2lip.pth || echo "请手动下载模型到 checkpoints/wav2lip.pth"
# 人脸检测模型
gdown "https://drive.google.com/uc?id=1z7Hx5d5o9Qk8h6eLXPmY5L1K3jW8h5tD" -O wav2lip_gan.pth || echo "请手动下载GAN模型"
cd /root/Wav2Lip

echo "=== 创建API服务 ==="
cat > /root/Wav2Lip/api_server.py << 'PYEOF'
"""Wav2Lip HTTP API — 接收视频+音频，返回对口型视频"""
from flask import Flask, request, send_file
import subprocess, tempfile, os
from pathlib import Path

app = Flask(__name__)
WORK_DIR = Path("/root/Wav2Lip")
OUTPUT_DIR = WORK_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/process", methods=["POST"])
def process():
    # 接收上传文件
    video = request.files.get("video")
    audio = request.files.get("audio")
    if not video or not audio:
        return {"error": "需要video和audio文件"}, 400

    video_path = OUTPUT_DIR / "input_video.mp4"
    audio_path = OUTPUT_DIR / "input_audio.wav"
    output_path = OUTPUT_DIR / "output_video.mp4"

    video.save(str(video_path))
    audio.save(str(audio_path))

    # 音频转WAV（Wav2Lip要求）
    subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-ar", "16000", "-ac", "1", str(OUTPUT_DIR / "input_audio_16k.wav")
    ], check=True)

    # 运行Wav2Lip
    subprocess.run([
        "python", "inference.py",
        "--checkpoint_path", str(WORK_DIR / "checkpoints/wav2lip.pth"),
        "--face", str(video_path),
        "--audio", str(OUTPUT_DIR / "input_audio_16k.wav"),
        "--outfile", str(output_path),
        "--resize_factor", "1",
        "--face_det_batch_size", "2",
        "--wav2lip_batch_size", "16",
    ], check=True, cwd=str(WORK_DIR))

    return send_file(output_path, mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
PYEOF

echo "=== 部署完成 ==="
echo "启动API: python /root/Wav2Lip/api_server.py"
echo "测试: curl http://localhost:8080/health"
echo ""
echo "注意: 需要先下载模型文件放到 /root/Wav2Lip/checkpoints/"
