# IoT Security Monitoring - Desktop Launch Script
# Usage: .\scripts\run_desktop.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "=== IoT Security Monitoring Desktop ===" -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Python found: $($python.Source)" -ForegroundColor Green
Write-Host "Installing dependencies..." -ForegroundColor Yellow
python -m pip install -r backend/requirements.txt

Write-Host "Starting desktop app..." -ForegroundColor Yellow
python -m desktop_app.main
