$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

Write-Host "Disabling OzonAutoReply proxy flag..." -ForegroundColor Cyan
.\venv\Scripts\python.exe .\disable_app_proxy.py

Write-Host ""
Write-Host "Current external IP:" -ForegroundColor Cyan
try {
    (Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 15).ip
} catch {
    Write-Host "Could not read external IP: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting OzonAutoReply..." -ForegroundColor Cyan
.\venv\Scripts\python.exe .\app.py
