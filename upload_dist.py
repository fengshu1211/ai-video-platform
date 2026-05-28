"""上传本地 dist 到服务器 nginx，带完整验证"""
import paramiko, os, posixpath, re, sys

HOST = "47.109.78.122"
USER = "root"
PWD = "Fengshu1211"
DIST = r"d:\应用开发项目集\AI短视频创作平台项目\frontend\dist"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PWD, timeout=15)
print("connected")

# Step 1: read local index.html to know expected JS file
local_index = os.path.join(DIST, "index.html")
with open(local_index, encoding="utf-8") as f:
    html = f.read()
m = re.search(r'src="([^"]+)"', html)
expected_js = m.group(1).split("/")[-1] if m else None
print(f"expected JS: {expected_js}")

# Step 2: purge remote directory completely
_, out, _ = c.exec_command("rm -rf /var/www/ai-video-platform")
print("purged:", out.read().decode().strip() or "ok")

# Step 3: recreate and upload
sftp = c.open_sftp()
def upload_dir(local_dir, remote_dir):
    sftp.mkdir(remote_dir)
    for item in sorted(os.listdir(local_dir)):
        local_path = os.path.join(local_dir, item)
        remote_path = posixpath.join(remote_dir, item)
        if os.path.isfile(local_path):
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            upload_dir(local_path, remote_path)

upload_dir(DIST, "/var/www/ai-video-platform")
sftp.close()
print("upload done")

# Step 4: verify
_, out, _ = c.exec_command("cat /var/www/ai-video-platform/index.html")
remote_html = out.read().decode()
remote_m = re.search(r'src="([^"]+)"', remote_html)
remote_js = remote_m.group(1).split("/")[-1] if remote_m else None

_, out, _ = c.exec_command(f"test -f /var/www/ai-video-platform/assets/{remote_js} && echo EXISTS || echo MISSING")
js_exists = out.read().decode().strip()
print(f"remote refs: {remote_js} [{js_exists}]")

if remote_js == expected_js and "EXISTS" in js_exists:
    _, out, _ = c.exec_command("curl -s http://localhost/ | head -1")
    print("verify:", out.read().decode().strip()[:80])
    print("DEPLOY OK")
else:
    print("DEPLOY FAILED - index.html references wrong JS file!")
    sys.exit(1)

c.close()
