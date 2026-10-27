@echo off
cd /d "%~dp0"
if exist ".packages" set "PYTHONPATH=%~dp0.packages"
python -m pytest -q
