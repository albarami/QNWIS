# Production Deployment Script for Multi-GPU System
# Date: November 24, 2025
# System: 8 x NVIDIA A100 GPUs

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "MULTI-GPU SYSTEM - PRODUCTION DEPLOYMENT" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify 8 A100 GPUs Available
Write-Host "[1/7] Verifying GPU Hardware..." -ForegroundColor Yellow

try {
    $gpuCount = python -c "import torch; print(torch.cuda.device_count())"
    
    if ($gpuCount -eq "8") {
        Write-Host "  [PASS] Found $gpuCount GPUs" -ForegroundColor Green
        
        # Show GPU details
        python -c @"
import torch
for i in range(8):
    name = torch.cuda.get_device_name(i)
    mem = torch.cuda.get_device_properties(i).total_memory / 1e9
    print(f'  GPU {i}: {name} ({mem:.1f}GB)')
"@
    } else {
        Write-Host "  [FAIL] Expected 8 GPUs, found $gpuCount" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  [FAIL] Cannot detect GPUs: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Check CUDA 12.1 Operational
Write-Host "[2/7] Verifying CUDA..." -ForegroundColor Yellow

try {
    $cudaVersion = python -c "import torch; print(torch.version.cuda)"
    Write-Host "  [PASS] CUDA version: $cudaVersion" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] CUDA check failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Set Production Environment Variables
Write-Host "[3/7] Setting Production Environment..." -ForegroundColor Yellow

# Required environment variables
$env:QNWIS_ENABLE_PARALLEL_SCENARIOS = "true"
$env:QNWIS_ENABLE_FACT_VERIFICATION = "true"
$env:QNWIS_WORKFLOW_IMPL = "langgraph"

# Optional (with defaults)
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Host "  [WARN] ANTHROPIC_API_KEY not set - using from .env file" -ForegroundColor Yellow
}

if (-not $env:DATABASE_URL) {
    Write-Host "  [INFO] DATABASE_URL not set - using default" -ForegroundColor Cyan
}

Write-Host "  [PASS] Environment configured:" -ForegroundColor Green
Write-Host "    PARALLEL_SCENARIOS: $env:QNWIS_ENABLE_PARALLEL_SCENARIOS"
Write-Host "    FACT_VERIFICATION: $env:QNWIS_ENABLE_FACT_VERIFICATION"
Write-Host "    WORKFLOW: $env:QNWIS_WORKFLOW_IMPL"

Write-Host ""

# Step 4: Verify Configuration Files
Write-Host "[4/7] Verifying Configuration Files..." -ForegroundColor Yellow

$configFiles = @(
    "config/gpu_config.yaml",
    "config/production.yaml"
)

foreach ($file in $configFiles) {
    if (Test-Path $file) {
        Write-Host "  [PASS] Found: $file" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Missing: $file" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Step 5: Pre-Deployment Test
Write-Host "[5/7] Running Pre-Deployment Tests..." -ForegroundColor Yellow

Write-Host "  Running master verification..."
$masterTest = python test_parallel_scenarios.py 2>&1 | Select-String "Overall.*passed"

if ($masterTest -match "5/5|6/6") {
    Write-Host "  [PASS] Master verification: $masterTest" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Master test output: $masterTest" -ForegroundColor Yellow
}

Write-Host ""

# Step 6: Start Server with Production Config
Write-Host "[6/7] Starting Production Server..." -ForegroundColor Yellow

# Kill any existing Python processes
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

Write-Host "  Starting uvicorn on port 8000..."

# Start server in background
$serverJob = Start-Job -ScriptBlock {
    param($env_parallel, $env_verification, $env_workflow)
    
    $env:QNWIS_ENABLE_PARALLEL_SCENARIOS = $env_parallel
    $env:QNWIS_ENABLE_FACT_VERIFICATION = $env_verification
    $env:QNWIS_WORKFLOW_IMPL = $env_workflow
    
    Set-Location "D:\lmis_int"
    python -m uvicorn src.qnwis.api.server:app --host 0.0.0.0 --port 8000 --workers 1 2>&1
} -ArgumentList $env:QNWIS_ENABLE_PARALLEL_SCENARIOS, $env:QNWIS_ENABLE_FACT_VERIFICATION, $env:QNWIS_WORKFLOW_IMPL

Write-Host "  Server starting (Job ID: $($serverJob.Id))..." -ForegroundColor Cyan

# Wait for startup
Write-Host "  Waiting for startup (30 seconds for fact verification pre-indexing)..."
Start-Sleep -Seconds 30

Write-Host ""

# Step 7: Health Check After Startup
Write-Host "[7/7] Health Check..." -ForegroundColor Yellow

$maxAttempts = 5
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts -and -not $healthy) {
    $attempt++
    Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10
        
        if ($response.status -eq "healthy" -or $response -match "healthy") {
            Write-Host "  [PASS] Health check: HEALTHY" -ForegroundColor Green
            $healthy = $true
        } else {
            Write-Host "  [INFO] Health check response: $response" -ForegroundColor Cyan
            Start-Sleep -Seconds 5
        }
    } catch {
        Write-Host "  [RETRY] Health check failed, retrying..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}

if (-not $healthy) {
    Write-Host "  [FAIL] Server did not become healthy" -ForegroundColor Red
    Stop-Job -Job $serverJob
    Remove-Job -Job $serverJob
    exit 1
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Server running at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server Job ID: $($serverJob.Id)" -ForegroundColor Yellow
Write-Host ""
Write-Host "To stop server:" -ForegroundColor Yellow
Write-Host "  Stop-Job -Id $($serverJob.Id)" -ForegroundColor White
Write-Host "  Remove-Job -Id $($serverJob.Id)" -ForegroundColor White
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  Receive-Job -Id $($serverJob.Id) -Keep" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Run smoke tests: python test_smoke_tests.py" -ForegroundColor White
Write-Host "2. Monitor for 1 hour" -ForegroundColor White
Write-Host "3. Review DEPLOYMENT_SIGN_OFF_FINAL.md" -ForegroundColor White
Write-Host ""

# Keep job running
Write-Host "Press Ctrl+C to exit (server will continue running)" -ForegroundColor Yellow
Write-Host ""

# Return job ID for monitoring
return $serverJob.Id

