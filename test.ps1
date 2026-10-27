$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PYTHONPATH = "$PSScriptRoot\.packages"
$env:PYTHONUTF8 = '1'
python -m pytest tests -q -p no:cacheprovider
