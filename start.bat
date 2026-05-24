@echo off
chcp 65001 >nul
title 自媒体创作平台

:: 自动添加Windows Defender白名单
powershell -Command "Add-MpPreference -ExclusionPath '%~dp0'" >nul 2>&1

cd /d "%~dp0backend"

:: 检查Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.12
    echo 下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 获取本机局域网IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4" ^| findstr "192.168"') do set LAN_IP=%%a
set LAN_IP=%LAN_IP: =%

echo.
echo ============================================
echo   自媒体创作平台
echo ============================================
echo.
echo   电脑浏览器: http://localhost:8000
if not "%LAN_IP%"=="" echo   手机浏览器: http://%LAN_IP%:8000
echo.
echo   手机打开后，浏览器菜单 - 添加到桌面
echo   即可像APP一样使用
echo ============================================
echo.

:: 启动后端（监听所有网络接口，手机可访问）
start "后端服务" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul
start http://localhost:8000
