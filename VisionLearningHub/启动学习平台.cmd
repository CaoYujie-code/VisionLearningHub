@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Python environment missing. Please read README.md.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "launch.py"
