@echo off
cd /d "%~dp0"
if exist ".packages" set "PYTHONPATH=%~dp0.packages"
if not exist ".packages" (
  echo First run: python -m pip install -r requirements.txt
  exit /b 1
)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
