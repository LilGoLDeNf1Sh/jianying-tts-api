$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install --target "$PSScriptRoot\.packages" -r requirements.txt
Write-Host '安装完成。保持剪映已登录运行，然后执行 .\start.ps1'
