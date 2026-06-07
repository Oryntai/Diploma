# IoT Security Monitoring - desktop device simulator
# Usage: .\scripts\run_desktop_simulator.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== IoT Device Desktop Simulator ===" -ForegroundColor White

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Python: $($python.Source)" -ForegroundColor Green
Write-Host "Start backend first with: .\scripts\run_local.ps1" -ForegroundColor Gray
python -m desktop_simulator.main
