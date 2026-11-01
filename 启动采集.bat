@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动中东情报采集器（常驻，每 30 分钟一轮）
echo 日志: data\collector.log
start "ME-Intel-Collector" pythonw collector.py --daemon --interval 30
timeout /t 3 >nul
start "" dashboard.html
echo 已启动。直接关闭本窗口即可，采集器在后台继续运行。
timeout /t 4 >nul
