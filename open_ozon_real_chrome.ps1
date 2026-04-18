$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProfileDir = Join-Path $Root "ozon_ai\data\real_chrome_profile"
$Port = 9222
$Url = "https://seller.ozon.ru/app/registration/signin?redirect=L3Jldmlld3M%2FX19ycj0xJmFidF9hdHQ9MQ%3D%3D"

$Candidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$Chrome = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Chrome) {
    throw "Google Chrome was not found."
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$Args = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--lang=ru-RU",
    $Url
)

Write-Host "Starting real Chrome without Playwright automation flags..."
Write-Host "Debug endpoint: http://127.0.0.1:$Port"
Write-Host "Profile: $ProfileDir"
Start-Process -FilePath $Chrome -ArgumentList $Args

Write-Host ""
Write-Host "Next:"
Write-Host "1. Log in to Ozon in the opened Chrome window."
Write-Host "2. Open https://seller.ozon.ru/app/reviews in that same window."
Write-Host "3. Leave Chrome open and run:"
Write-Host "   .\venv\Scripts\python.exe .\import_ozon_session_from_chrome.py --account-id 3"
