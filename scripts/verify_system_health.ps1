#!/usr/bin/env pwsh
<#
.SYNOPSIS
    QNWIS System Health Verification Script
.DESCRIPTION
    Validates that all components of the QNWIS system are operational:
    - Backend syntax check
    - Backend server health
    - Frontend connectivity
    - Critical file integrity
.NOTES
    Run this after any code changes to ensure system stability
#>

$ErrorActionPreference = "Continue"
$script:failures = 0

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = ""
    )
    
    if ($Passed) {
        Write-Host "✅ PASS: $TestName" -ForegroundColor Green
        if ($Details) { Write-Host "   $Details" -ForegroundColor Gray }
    } else {
        Write-Host "❌ FAIL: $TestName" -ForegroundColor Red
        if ($Details) { Write-Host "   $Details" -ForegroundColor Yellow }
        $script:failures++
    }
}

Write-Host "`n=== QNWIS System Health Verification ===" -ForegroundColor Cyan
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" -ForegroundColor Gray

# Test 1: Python Syntax Check
Write-Host "[1/6] Checking backend syntax..." -ForegroundColor Cyan
$compileResult = python -m py_compile src\qnwis\orchestration\graph_llm.py 2>&1
$syntaxPassed = $LASTEXITCODE -eq 0
Write-TestResult -TestName "Backend Python syntax" -Passed $syntaxPassed -Details $(if (-not $syntaxPassed) { $compileResult })

# Test 2: Flake8 Static Analysis
Write-Host "[2/6] Running static analysis..." -ForegroundColor Cyan
$flakeResult = python -m flake8 src\qnwis\orchestration\graph_llm.py --select=E9,F82,F83,F821 2>&1
$flakePassed = $LASTEXITCODE -eq 0
Write-TestResult -TestName "Flake8 critical errors" -Passed $flakePassed -Details $(if (-not $flakePassed) { $flakeResult })

# Test 3: Backend Health Check
Write-Host "[3/6] Checking backend health..." -ForegroundColor Cyan
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    $healthJson = $healthResponse.Content | ConvertFrom-Json
    $backendHealthy = $healthResponse.StatusCode -eq 200 -and $healthJson.status -match "healthy|alive"
    Write-TestResult -TestName "Backend server health" -Passed $backendHealthy -Details "Status: $($healthJson.status)"
} catch {
    Write-TestResult -TestName "Backend server health" -Passed $false -Details "Server not responding: $($_.Exception.Message)"
}

# Test 4: Backend Readiness
Write-Host "[4/6] Checking backend readiness..." -ForegroundColor Cyan
try {
    $readyResponse = Invoke-WebRequest -Uri "http://localhost:8000/health/ready" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
    $readyJson = $readyResponse.Content | ConvertFrom-Json
    $backendReady = $readyJson.status -eq "healthy"
    $queryCount = $readyJson.registry_query_count
    Write-TestResult -TestName "Backend readiness" -Passed $backendReady -Details "Query registry: $queryCount queries loaded"
} catch {
    Write-TestResult -TestName "Backend readiness" -Passed $false -Details "Readiness check failed (may be degraded but operational)"
}

# Test 5: Critical File Integrity
Write-Host "[5/6] Verifying critical files..." -ForegroundColor Cyan
$criticalFiles = @(
    "src\qnwis\orchestration\graph_llm.py",
    "src\qnwis\api\server.py",
    "src\qnwis\api\routers\council_llm.py",
    "qnwis-frontend\src\App.tsx",
    "qnwis-frontend\src\hooks\useWorkflowStream.ts"
)

$allFilesExist = $true
foreach ($file in $criticalFiles) {
    if (-not (Test-Path $file)) {
        $allFilesExist = $false
        Write-Host "   Missing: $file" -ForegroundColor Red
    }
}
Write-TestResult -TestName "Critical files present" -Passed $allFilesExist -Details "$($criticalFiles.Count) files checked"

# Test 6: Frontend Configuration
Write-Host "[6/6] Checking frontend configuration..." -ForegroundColor Cyan
$frontendEnvExists = Test-Path "qnwis-frontend\.env"
if ($frontendEnvExists) {
    $envContent = Get-Content "qnwis-frontend\.env" -Raw
    $apiUrlConfigured = $envContent -match "VITE_QNWIS_API_URL=http://localhost:8000"
    Write-TestResult -TestName "Frontend .env configuration" -Passed $apiUrlConfigured -Details "API URL configured correctly"
} else {
    Write-TestResult -TestName "Frontend .env configuration" -Passed $false -Details ".env file missing"
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
if ($script:failures -eq 0) {
    Write-Host "✅ All tests passed! System is healthy and operational." -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ $($script:failures) test(s) failed. Please review and fix issues." -ForegroundColor Red
    exit 1
}
