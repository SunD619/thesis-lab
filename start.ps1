$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw '请先按 README 创建 .venv 并安装依赖。'
}
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
    & npm.cmd --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败。' }
}
Write-Host '打开 http://127.0.0.1:8000 体验证见。按 Ctrl+C 停止服务。'
& .venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
