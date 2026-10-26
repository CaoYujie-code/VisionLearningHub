@echo off
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "launch.py" --stop
