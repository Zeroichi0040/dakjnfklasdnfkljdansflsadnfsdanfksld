@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_WINDOWS.bat --dev first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_tests.py %*
pause
