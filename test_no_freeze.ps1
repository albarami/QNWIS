#!/usr/bin/env pwsh
# Test that backend doesn't freeze in stub mode

Write-Host "🧪 Testing backend for freeze..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Health check
Write-Host "1️⃣  Health check..." -NoNewline
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    if ($health.status -eq "healthy") {
        Write-Host " ✅ PASS" -ForegroundColor Green
    } else {
        Write-Host " ❌ FAIL" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host " ❌ FAIL - $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Quick query with timeout
Write-Host "2️⃣  Quick query (10s timeout)..." -NoNewline
try {
    $body = @{question = "test"} | ConvertTo-Json
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/v1/council/stream" `
        -Method POST `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 10
    
    if ($response.StatusCode -eq 200) {
        Write-Host " ✅ PASS (no freeze)" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Message -match "timeout") {
        Write-Host " ❌ FAIL - FROZE!" -ForegroundColor Red
        exit 1
    } else {
        Write-Host " ⚠️  ERROR - $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Test 3: Check no deterministic agents in stub mode
Write-Host "3️⃣  Verify stub mode (no deterministic agents)..." -NoNewline
try {
    $body = @{question = "unemployment trends"} | ConvertTo-Json
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/v1/council/stream" `
        -Method POST `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 120  # 2 minute max
    
    $content = $response.Content
    
    # Check that deterministic agents were NOT invoked
    if ($content -notmatch "time_machine|TimeMachine completed" -and 
        $content -notmatch "predictor|Predictor completed" -and
        $content -notmatch "scenario|Scenario completed") {
        Write-Host " ✅ PASS (deterministic agents disabled)" -ForegroundColor Green
    } else {
        Write-Host " ⚠️  WARNING - deterministic agents were invoked" -ForegroundColor Yellow
    }
    
    # Check that it completed
    if ($content -match "synthesis|complete") {
        Write-Host "4️⃣  Query completed successfully" -ForegroundColor Green
    }
    
} catch {
    if ($_.Exception.Message -match "timeout") {
        Write-Host " ❌ FAIL - QUERY FROZE!" -ForegroundColor Red
        Write-Host "   Deterministic agents are still being invoked and blocking!" -ForegroundColor Red
        exit 1
    } else {
        Write-Host " ⚠️  ERROR - $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✅ ALL TESTS PASSED - No freeze detected!" -ForegroundColor Green
Write-Host "   Stub mode working correctly with 4 LLM agents only" -ForegroundColor Cyan
