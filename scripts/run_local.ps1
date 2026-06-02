# IoT Security Monitoring - FastAPI launch script
# Usage: .\scripts\run_local.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== IoT Security Monitoring ===" -ForegroundColor White
Write-Host ""

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[ERROR] Python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Python: $($python.Source)" -ForegroundColor Green

Write-Host "Installing backend dependencies..." -ForegroundColor Gray
python -m pip install -r backend/requirements.txt --quiet

$dbPath = "backend/iot_monitor.db"
if (Test-Path $dbPath) {
    try {
        Remove-Item $dbPath -Force -ErrorAction Stop
        Write-Host "[OK] Clean database prepared" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Existing database is in use; continuing" -ForegroundColor Yellow
    }
}

Write-Host "Starting FastAPI at http://127.0.0.1:8000/" -ForegroundColor White
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD/backend
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}

try {
    Start-Sleep -Seconds 3
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
    Write-Host "[OK] Backend health: $($health.status)" -ForegroundColor Green

    $scenario = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/demo/scenario" -Method Post
    Write-Host "[OK] Demo scenario: $($scenario.samples_sent) samples, $($scenario.alerts_created) alerts" -ForegroundColor Green

    Start-Process "http://127.0.0.1:8000/"
    Write-Host ""
    Write-Host "Dashboard: http://127.0.0.1:8000/" -ForegroundColor White
    Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

    Wait-Job $backendJob | Out-Null
    Receive-Job $backendJob
} finally {
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
}
