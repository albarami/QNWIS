#!/usr/bin/env pwsh
# Start QNWIS Backend Server with proper configuration

Write-Host "🚀 Starting QNWIS Backend Server..." -ForegroundColor Green
Write-Host ""

# Check if port 8000 is in use and kill it
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "⚠️  Port 8000 already in use. Killing existing process..." -ForegroundColor Yellow
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Verify .env exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "   Copy .env.example to .env and configure it" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Environment file found" -ForegroundColor Green
Write-Host "✅ Starting server on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host ""
Write-Host "Expected startup sequence:" -ForegroundColor Cyan
Write-Host "  1. Logging configured" -ForegroundColor Gray
Write-Host "  2. Redis warnings (optional, safe to ignore)" -ForegroundColor Gray
Write-Host "  3. Pre-warming sentence embedder (10-15 seconds)" -ForegroundColor Gray
Write-Host "  4. Application startup complete" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "=" * 60
Write-Host ""

# Start the server  
python -m uvicorn src.qnwis.api.server:app --host 0.0.0.0 --port 8000 --reload
