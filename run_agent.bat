@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [BKR] Using Python: %PY%
"%PY%" doctor.py
if errorlevel 1 (
  echo [BKR] Doctor reported critical issues. Fix them before continuing.
  pause
  exit /b 1
)

"%PY%" main.py
endlocal

