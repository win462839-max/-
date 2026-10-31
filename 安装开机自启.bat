@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 注册 Windows 计划任务：登录后自动启动采集器（每 30 分钟一轮）
schtasks /create /tn "MiddleEastIntelCollector" /tr "\"%~dp0run_daemon.bat\"" /sc ONLOGON /rl HIGHEST /f
if errorlevel 1 (
  echo 注册失败，请右键以管理员身份运行本文件
) else (
  echo 注册成功。下次登录后自动运行；立即启动请执行 启动采集.bat
)
pause
