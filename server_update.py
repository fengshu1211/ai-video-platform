"""更新服务器代码 + 清理卡死任务 + 重建前端"""
import paramiko
import time

HOST = "47.109.78.122"
USER = "root"
PWD = "Fengshu1211"

def run(c, cmd, desc=""):
    print(f"\n>>> {desc or cmd[:60]}")
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    if out.strip(): print(out.strip())
    if err.strip(): print("STDERR:", err.strip()[-200:])
    return out, err

print("=== connecting ===")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=30)
print("connected")

# 1. 重置卡死任务
run(c, 'cd /opt/ai-video-platform && sqlite3 data.db "UPDATE async_tasks SET status=\\\"failed\\\", progress_message=\\\"服务重启，任务已取消\\\" WHERE status IN (\\\"pending\\\",\\\"processing\\\");"', 'clean stuck tasks')
run(c, 'cd /opt/ai-video-platform && sqlite3 data.db "UPDATE video_projects SET status=\\\"draft\\\" WHERE status IN (\\\"processing\\\");"', 'reset processing projects')

# 2. 拉最新代码
run(c, 'cd /opt/ai-video-platform && git pull 2>&1', 'git pull')

# 3. 重启后端
run(c, 'systemctl restart ai-video && sleep 2 && systemctl status ai-video --no-pager | head -8', 'restart backend')

# 4. 重建前端 (node on server)
run(c, 'cd /opt/ai-video-platform/frontend && npm install --silent 2>&1 | tail -5', 'npm install')
run(c, 'cd /opt/ai-video-platform/frontend && npm run build 2>&1', 'npm build')
run(c, 'rm -rf /var/www/ai-video-platform/* && cp -r /opt/ai-video-platform/frontend/dist/* /var/www/ai-video-platform/', 'copy dist to nginx')

# 5. 验证
run(c, 'curl -s http://localhost:8000/api/video/projects | head -c 150', 'verify backend')
run(c, 'curl -s http://localhost/ | head -c 80', 'verify frontend')

print("\n=== DONE ===")
print("http://47.109.78.122")
c.close()
