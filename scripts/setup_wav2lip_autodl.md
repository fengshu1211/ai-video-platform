# Wav2Lip AutoDL 部署指南

## 1. 创建GPU实例
- 打开 https://www.autodl.com
- 租一台 RTX 3060（约0.6元/时）
- 镜像选：PyTorch 2.0 + Python 3.10 + CUDA 11.8
- 数据盘：20GB

## 2. 连接实例
打开JupyterLab终端，运行：
```bash
cd /root
bash <(curl -s https://your-server/setup_wav2lip.sh)
```
或手动执行 deploy_wav2lip_autodl.sh 的内容

## 3. 获取实例IP
- 在AutoDL控制台查看实例的SSH地址
- 记录：IP + 端口（如 123.45.67.89:42151）

## 4. 配置平台
将IP和端口填入 backend/app/config.py 的 WAV2LIP_HOST / WAV2LIP_PORT

## 5. 启动服务
```bash
cd /root/Wav2Lip
python api_server.py
```
服务运行在 8080 端口

## 6. 使用
平台新建视频项目 → 勾选"启用对口型" → 上传人脸视频 → 生成
