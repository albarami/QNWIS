#!/usr/bin/env pwsh
# Start QNWIS Frontend (React/Vite)

Write-Host "🎨 Starting QNWIS Frontend..." -ForegroundColor Green
Write-Host ""

# Navigate to frontend directory
Set-Location -Path "qnwis-frontend"

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "⚠️  node_modules not found. Running npm install..." -ForegroundColor Yellow
    npm install
}

Write-Host "✅ Starting development server" -ForegroundColor Green
Write-Host "✅ Frontend will be available at http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "=" * 60
Write-Host ""

# Start the frontend
npm run dev --host
