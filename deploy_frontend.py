"""部署前端 + 配置 nginx 到服务器"""
import paramiko
import os
import posixpath
from pathlib import Path

HOST = "47.109.78.122"
USER = "root"
PWD = "Fengshu1211"

DIST_DIR = Path(__file__).parent / "frontend" / "dist"
NGINX_CONF = """
server {
    listen 80;
    server_name _;

    root /var/www/ai-video-platform;
    index index.html;

    # 前端静态文件
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }

    # 上传文件
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
"""

def run_ssh(c, cmd, desc=""):
    print(f"\n>>> {desc or cmd[:60]}")
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    if out.strip():
        print(out.strip())
    if err.strip():
        print("STDERR:", err.strip()[-300:])
    return out, err

print("=== 连接服务器 ===")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PWD, timeout=15)
print("已连接")

# 1. 安装 nginx
out, _ = run_ssh(client, "which nginx && echo '已安装' || echo '需要安装'", "检查 nginx")
if "需要安装" in out:
    run_ssh(client, "apt update && apt install -y nginx", "安装 nginx")

# 2. 清理旧文件，上传新 dist
run_ssh(client, "rm -rf /var/www/ai-video-platform && mkdir -p /var/www/ai-video-platform", "准备目录")

print("\n>>> 上传前端文件...")
sftp = client.open_sftp()

def upload_dir(local_dir, remote_dir):
    for item in sorted(os.listdir(local_dir)):
        local_path = os.path.join(local_dir, item)
        remote_path = posixpath.join(remote_dir, item)
        if os.path.isfile(local_path):
            print(f"  {item}")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            try:
                sftp.mkdir(remote_path)
            except IOError:
                pass
            upload_dir(local_path, remote_path)

upload_dir(str(DIST_DIR), "/var/www/ai-video-platform")
sftp.close()
print("上传完成")

# 3. 写 nginx 配置
run_ssh(client, "cat > /etc/nginx/sites-available/ai-video << 'NGXEOF'\n" + NGINX_CONF + "\nNGXEOF", "写配置")
run_ssh(client, "rm -f /etc/nginx/sites-enabled/default && ln -sf /etc/nginx/sites-available/ai-video /etc/nginx/sites-enabled/ai-video", "启用站点")

# 4. 测试并重启 nginx
out, err = run_ssh(client, "nginx -t 2>&1", "测试 nginx 配置")
if "successful" in out + err:
    run_ssh(client, "systemctl enable nginx && systemctl restart nginx", "启动 nginx")
    print("\n✅ nginx 已启动")
else:
    print("\n❌ nginx 配置有误，请检查")

# 5. 验证
print("\n=== 验证 ===")
import time
time.sleep(2)
stdin, stdout, stderr = client.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost/")
http_code = stdout.read().decode().strip()
print(f"前端访问状态码: {http_code}")

stdin, stdout, stderr = client.exec_command("curl -s http://localhost/api/video/projects | head -c 100")
print(f"API代理: {stdout.read().decode()[:100]}")

client.close()
print("\n=== 完成 ===")
print("访问 http://47.109.78.122")
