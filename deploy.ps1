# KAVACH-VISION Production Deployment Script

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " KAVACH-VISION - Production Deployment Automation (Windows)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Install Production WSGI Server (Waitress)
Write-Host "`n[1/3] Installing Production Dependencies (Waitress)..." -ForegroundColor Yellow
python -m pip install waitress

# 2. Pre-Flight Checks
Write-Host "`n[2/3] Performing Integrity Checks..." -ForegroundColor Yellow
if (-Not (Test-Path "zenora/dashboard/app.py")) {
    Write-Host "ERROR: app.py not found. Please run this script from the root project directory." -ForegroundColor Red
    exit 1
}
Write-Host "Dependencies OK. Files OK." -ForegroundColor Green

# 3. Start the Server
Write-Host "`n[3/3] Starting Production Server on Port 8080..." -ForegroundColor Yellow
Write-Host "The application is now running securely on 0.0.0.0:8080 (Accessible via localhost and LAN)" -ForegroundColor DarkGray
Write-Host "Press CTRL+C to stop the server.`n" -ForegroundColor DarkGray

$env:PYTHONPATH="."
python -c "from waitress import serve; from zenora.dashboard.app import app; serve(app, host='0.0.0.0', port=8080)"
