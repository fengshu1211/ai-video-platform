@echo off
echo 正在连接 bjb2 (3080Ti) 双服务隧道...
ssh -f -N -L 8080:localhost:8080 -L 8090:localhost:8090 -o StrictHostKeyChecking=no -p 22593 root@connect.bjb2.seetacloud.com
echo 隧道已建立:
echo   Wav2Lip   -> localhost:8080
echo   SadTalker -> localhost:8090
echo.
echo 按任意键关闭窗口（服务仍在后台运行）
pause
