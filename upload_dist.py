"""上传本地 dist 到服务器 nginx 目录"""
import paramiko
import os

HOST = "47.109.78.122"
USER = "root"
PWD = "Fengshu1211"

DIST = r"d:\应用开发项目集\AI短视频创作平台项目\frontend\dist"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=15)
print("connected")

# Clear and recreate nginx directory
_, out, _ = c.exec_command("rm -rf /var/www/ai-video-platform/* && mkdir -p /var/www/ai-video-platform")
print(out.read().decode())

# Upload dist files
import posixpath
sftp = c.open_sftp()

def upload_dir(local_dir, remote_dir):
    for item in sorted(os.listdir(local_dir)):
        local_path = os.path.join(local_dir, item)
        remote_path = posixpath.join(remote_dir, item)
        if os.path.isfile(local_path):
            print(f"  uploading {item}...")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            try:
                sftp.mkdir(remote_path)
            except IOError:
                pass
            upload_dir(local_path, remote_path)

upload_dir(DIST, "/var/www/ai-video-platform")
sftp.close()
print("upload done")

# Verify
_, out, _ = c.exec_command("curl -s http://localhost/ | head -3")
print("verify:", out.read().decode()[:100])

c.close()
print("DONE")
