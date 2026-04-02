# IoT Security Monitoring — Local Launch Script
# Usage: .\scripts\run_local.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== IoT Security Monitoring Platform ===" -ForegroundColor Cyan
Write-Host ""

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python found: $($python.Source)" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
pip install -r backend/requirements.txt --quiet 2>$null
$ErrorActionPreference = "Stop"
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# Remove old database for clean demo
$dbPath = "backend/iot_monitor.db"
if (Test-Path $dbPath) {
    try {
        Remove-Item $dbPath -Force -ErrorAction Stop
        Write-Host "[OK] Old database removed for clean demo" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Could not remove old database (in use), continuing..." -ForegroundColor Yellow
    }
}

# Start backend in background
Write-Host ""
Write-Host "Starting backend..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD/backend
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
Start-Sleep -Seconds 3

# Check health
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
    Write-Host "[OK] Backend is running: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Backend failed to start" -ForegroundColor Red
    Stop-Job $backendJob
    exit 1
}

# Send normal telemetry from all device types
Write-Host ""
Write-Host "Sending normal telemetry..." -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
$deviceTypes = @("temperature_sensor", "smart_plug", "ip_camera", "smart_door_lock")
foreach ($dt in $deviceTypes) {
    python simulator/main.py --once --seed 42 --device-type $dt --mode normal --ingest-url http://127.0.0.1:8000/api/ingest/telemetry 2>$null | Out-Null
}
Write-Host "[OK] Normal telemetry sent for $($deviceTypes.Count) device types" -ForegroundColor Green

# Run threat scenarios
Write-Host ""
Write-Host "Running threat scenarios..." -ForegroundColor Yellow
python simulator/scenarios/run_scenario.py --scenario all --ingest-url http://127.0.0.1:8000/api/ingest/telemetry 2>$null | Out-Null
Write-Host "[OK] Threat scenarios completed" -ForegroundColor Green

# Send abnormal telemetry (triggers ML)
Write-Host ""
Write-Host "Sending abnormal telemetry (ML detection)..." -ForegroundColor Yellow
python simulator/main.py --once --seed 99 --device-type temperature_sensor --mode abnormal --ingest-url http://127.0.0.1:8000/api/ingest/telemetry 2>$null | Out-Null
Write-Host "[OK] Abnormal telemetry sent" -ForegroundColor Green
$ErrorActionPreference = "Stop"

# Open browser
Write-Host ""
Write-Host "Opening dashboard in browser..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:8000/"

Write-Host ""
Write-Host "=== Dashboard is ready at http://127.0.0.1:8000/ ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the backend" -ForegroundColor Gray
Write-Host ""

# Wait for backend job
try {
    Wait-Job $backendJob | Out-Null
    Receive-Job $backendJob
} finally {
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
}
