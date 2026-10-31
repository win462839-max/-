@echo off
chcp 65001 >nul
taskkill /FI "WINDOWTITLE eq ME-Intel-Collector*" /F >nul 2>&1
taskkill /IM pythonw.exe /FI "COMMANDLINE eq *collector.py*" /F >nul 2>&1
wmic process where "name='pythonw.exe' and commandline like '%%collector.py%%'" call terminate >nul 2>&1
echo 采集器已停止（如仍有残留，可在任务管理器结束 pythonw.exe）
timeout /t 3 >nul
