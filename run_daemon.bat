@echo off
cd /d "%~dp0"
pythonw collector.py --daemon --interval 30
