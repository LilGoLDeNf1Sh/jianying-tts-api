$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PYTHONPATH = "$PSScriptRoot\.packages"
$env:PYTHONUTF8 = '1'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
