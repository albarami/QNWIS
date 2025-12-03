<#
.SYNOPSIS
    NSIC System Stop Script - Gracefully stops all NSIC services

.DESCRIPTION
    Stops all running NSIC services:
    - Engine B (GPU compute)
    - Frontend (if running)
    - Any background Python processes

.EXAMPLE
    .\scripts\stop_nsic_system.ps1
#>

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "NSIC System Shutdown" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan
Write-Host ""

# Stop processes by port
$ports = @(8001, 3000, 8000)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "[STOP] Port $port - $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Yellow
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

# Stop any uvicorn processes
$uvicornProcs = Get-Process -Name python -ErrorAction SilentlyContinue | 
                Where-Object { $_.CommandLine -like "*uvicorn*" }
foreach ($proc in $uvicornProcs) {
    Write-Host "[STOP] Uvicorn process (PID: $($proc.Id))" -ForegroundColor Yellow
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

# Stop any node processes (frontend)
$nodeProcs = Get-Process -Name node -ErrorAction SilentlyContinue
foreach ($proc in $nodeProcs) {
    Write-Host "[STOP] Node process (PID: $($proc.Id))" -ForegroundColor Yellow
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# Verify ports are free
Write-Host ""
Write-Host "Verifying shutdown..." -ForegroundColor Cyan
$allClear = $true
foreach ($port in $ports) {
    if (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue) {
        Write-Host "[WARN] Port $port still in use" -ForegroundColor Yellow
        $allClear = $false
    } else {
        Write-Host "[OK] Port $port is free" -ForegroundColor Green
    }
}

Write-Host ""
if ($allClear) {
    Write-Host "All NSIC services stopped successfully" -ForegroundColor Green
} else {
    Write-Host "Some services may still be running" -ForegroundColor Yellow
}
Write-Host ""

