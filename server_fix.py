import paramiko, time

HOST = "47.109.78.122"
USER = "root"
PWD = "Fengshu1211"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=15)
print("connected", flush=True)

cmds = """
cd /opt/ai-video-platform
git checkout -- .
git pull --force
sleep 1
systemctl restart ai-video
sleep 3
systemctl status ai-video --no-pager | head -8
echo "===HEALTH==="
curl -s http://localhost:8000/api/health
"""

stdin, stdout, stderr = c.exec_command(cmds)
out = stdout.read().decode()
err = stderr.read().decode()
print(out, flush=True)
if err:
    print("STDERR:", err[-500:], flush=True)
c.close()
