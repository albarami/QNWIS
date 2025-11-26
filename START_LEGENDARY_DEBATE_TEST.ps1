#!/usr/bin/env pwsh
# Start Legendary Debate Test
# This script starts both backend and frontend for testing

Write-Host "🚀 LEGENDARY DEBATE SYSTEM - TEST STARTUP" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan

# Check if backend is running
$backendRunning = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*uvicorn*"}

if ($backendRunning) {
    Write-Host "⚠️  Backend already running. Stopping..." -ForegroundColor Yellow
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Start backend in new terminal
Write-Host "🔄 Starting Backend..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python -m uvicorn qnwis.api.server:app --reload --port 8000"

Start-Sleep -Seconds 5

# Start frontend in new terminal
Write-Host "🔄 Starting Frontend..." -ForegroundColor Green
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\qnwis-frontend'; npm run dev"

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "✅ SERVICES STARTED!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Wait for services to fully start (30 seconds)"
Write-Host "  2. Open browser: http://localhost:3001"
Write-Host "  3. Paste this question:" -ForegroundColor Yellow
Write-Host ""
Write-Host "     What are the risks of increasing Qatar Qatarization target to 80 percent by 2028 while maintaining 5 percent GDP growth?" -ForegroundColor White
Write-Host ""
Write-Host "  4. Select provider: anthropic"
Write-Host "  5. Click Submit"
Write-Host "  6. Watch the legendary debate unfold!"
Write-Host ""
Write-Host "⏱️  Expected Duration: 25-32 minutes" -ForegroundColor Cyan
Write-Host "🎯 Expected Turns: 64-84 conversation turns" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to open browser..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Start-Process "http://localhost:3001"

Write-Host ""
Write-Host "🔥 LEGENDARY DEBATE SYSTEM IS LIVE!" -ForegroundColor Green
Write-Host ""
