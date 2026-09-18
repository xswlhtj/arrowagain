$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "未找到 .venv，请先创建虚拟环境并安装 requirements-dev.txt。"
}

Push-Location $projectRoot
try {
    & $python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "自动化测试未通过，已取消打包。"
    }
    & $python -m PyInstaller --noconfirm --clean arrow_escape.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 打包失败。"
    }
    Write-Host "构建完成：$projectRoot\dist\箭途.exe"
}
finally {
    Pop-Location
}
