"""快速部署：上传修改的后端文件+前端dist"""
import paramiko
import os

HOST = "47.109.78.122"
USER = "root"
PWD = "Fengshu1211"
BASE = r"d:\应用开发项目集\AI短视频创作平台项目"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=15)
print("connected")

sftp = c.open_sftp()

# Upload backend files
backend_files = [
    "backend/app/services/video_service.py",
    "backend/app/services/image_service.py",
    "backend/app/tasks/video_tasks.py",
]
for f in backend_files:
    local = os.path.join(BASE, f)
    remote = "/opt/ai-video-platform/" + f.replace("\\", "/")
    sftp.put(local, remote)
    print("uploaded:", f)

# Upload frontend dist
dist_dir = os.path.join(BASE, "frontend", "dist")
for item in os.listdir(dist_dir):
    local = os.path.join(dist_dir, item)
    remote = "/var/www/ai-video-platform/" + item
    if os.path.isfile(local):
        sftp.put(local, remote)
        print("uploaded dist:", item)
    elif os.path.isdir(local):
        # Handle subdirectories like assets/
        for sub in os.listdir(local):
            sub_local = os.path.join(local, sub)
            try:
                sftp.mkdir(remote)
            except IOError:
                pass
            sub_remote = remote + "/" + sub
            sftp.put(sub_local, sub_remote)
            print("uploaded dist:", item + "/" + sub)

sftp.close()

# Restart backend
_, out, _ = c.exec_command("systemctl restart ai-video && sleep 2 && curl -s http://localhost:8000/api/video/projects | head -c 80")
print("Verify backend:", out.read().decode()[:100])

# Test nginx
_, out, _ = c.exec_command("curl -s http://localhost/ | head -c 80")
print("Verify frontend:", out.read().decode()[:100])

c.close()
print("DONE")
