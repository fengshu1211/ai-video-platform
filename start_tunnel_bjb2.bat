@echo off
echo [bjb2 / 3080Ti] 正在建立双服务隧道...
ssh -f -N -L 8080:localhost:8080 -L 8090:localhost:8090 -o StrictHostKeyChecking=no -p 22593 root@connect.bjb2.seetacloud.com
echo 已连接 bjb2:
echo   Wav2Lip   -> localhost:8080
echo   SadTalker -> localhost:8090
echo.
pause
