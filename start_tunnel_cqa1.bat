@echo off
echo [cqa1 / 4090D] 正在建立双服务隧道...
ssh -f -N -L 8080:localhost:8080 -L 8090:localhost:8090 -o StrictHostKeyChecking=no -p 15123 root@connect.cqa1.seetacloud.com
echo 已连接 cqa1:
echo   Wav2Lip   -> localhost:8080
echo   SadTalker -> localhost:8090
echo.
pause
