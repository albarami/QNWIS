# start_nsic_enterprise.ps1 - Enterprise Grade NSIC Startup Script
# 
# Starts all persistent GPU services:
# - Embeddings Server (GPU 0-1, Port 8003)
# - Knowledge Graph Server (GPU 4, Port 8004)
# - Verification Server (GPU 5, Port 8005)
# - DeepSeek Instance 1 (GPU 2-3, Port 8001) - if not already running
# - DeepSeek Instance 2 (GPU 6-7, Port 8002) - if not already running
#
# All models are loaded at startup and kept in GPU memory permanently.

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  NSIC ENTERPRISE STARTUP - Persistent GPU Services" -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

# Configuration
$VENV_PYTHON = "d:/lmis_int/.venv/Scripts/python.exe"
$PROJECT_ROOT = "d:/lmis_int"

# Change to project root
Set-Location $PROJECT_ROOT

# Function to check if a port is in use
function Test-Port {
    param($Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient("localhost", $Port)
        $connection.Close()
        return $true
    } catch {
        return $false
    }
}

# Function to wait for a service to be ready
function Wait-ForService {
    param($Port, $Name, $MaxWait = 120)
    
    Write-Host "  Waiting for $Name (port $Port)..." -ForegroundColor Yellow
    $elapsed = 0
    while (-not (Test-Port $Port)) {
        Start-Sleep -Seconds 5
        $elapsed += 5
        if ($elapsed -ge $MaxWait) {
            Write-Host "  TIMEOUT: $Name did not start within ${MaxWait}s" -ForegroundColor Red
            return $false
        }
        Write-Host "    ... waiting ($elapsed s)" -ForegroundColor Gray
    }
    Write-Host "  $Name is ready!" -ForegroundColor Green
    return $true
}

# ============================================================================
# 1. Start Embeddings Server (GPU 0-1, Port 8003)
# ============================================================================
Write-Host ""
Write-Host "[1/5] EMBEDDINGS SERVER (GPU 0-1, Port 8003)" -ForegroundColor Magenta

if (Test-Port 8003) {
    Write-Host "  Already running on port 8003" -ForegroundColor Green
} else {
    Write-Host "  Starting embeddings server..." -ForegroundColor Yellow
    
    $env:CUDA_VISIBLE_DEVICES = "0,1"
    Start-Process -FilePath $VENV_PYTHON `
        -ArgumentList "-m", "src.nsic.servers.embeddings_server", "--port", "8003" `
        -WorkingDirectory $PROJECT_ROOT `
        -WindowStyle Normal
    
    Start-Sleep -Seconds 5
}

# ============================================================================
# 2. Start Knowledge Graph Server (GPU 4, Port 8004)
# ============================================================================
Write-Host ""
Write-Host "[2/5] KNOWLEDGE GRAPH SERVER (GPU 4, Port 8004)" -ForegroundColor Magenta

if (Test-Port 8004) {
    Write-Host "  Already running on port 8004" -ForegroundColor Green
} else {
    Write-Host "  Starting KG server..." -ForegroundColor Yellow
    
    $env:CUDA_VISIBLE_DEVICES = "4"
    Start-Process -FilePath $VENV_PYTHON `
        -ArgumentList "-m", "src.nsic.servers.kg_server", "--port", "8004" `
        -WorkingDirectory $PROJECT_ROOT `
        -WindowStyle Normal
    
    Start-Sleep -Seconds 5
}

# ============================================================================
# 3. Start Verification Server (GPU 5, Port 8005)
# ============================================================================
Write-Host ""
Write-Host "[3/5] VERIFICATION SERVER (GPU 5, Port 8005)" -ForegroundColor Magenta

if (Test-Port 8005) {
    Write-Host "  Already running on port 8005" -ForegroundColor Green
} else {
    Write-Host "  Starting verification server..." -ForegroundColor Yellow
    
    $env:CUDA_VISIBLE_DEVICES = "5"
    Start-Process -FilePath $VENV_PYTHON `
        -ArgumentList "-m", "src.nsic.servers.verification_server", "--port", "8005" `
        -WorkingDirectory $PROJECT_ROOT `
        -WindowStyle Normal
    
    Start-Sleep -Seconds 5
}

# ============================================================================
# 4. Check DeepSeek Instance 1 (GPU 2-3, Port 8001)
# ============================================================================
Write-Host ""
Write-Host "[4/5] DEEPSEEK INSTANCE 1 (GPU 2-3, Port 8001)" -ForegroundColor Magenta

if (Test-Port 8001) {
    Write-Host "  Already running on port 8001" -ForegroundColor Green
} else {
    Write-Host "  WARNING: DeepSeek Instance 1 not running!" -ForegroundColor Red
    Write-Host "  Start it manually with:" -ForegroundColor Yellow
    Write-Host "    python scripts/deploy_deepseek_native.py --instance 1 --production" -ForegroundColor White
}

# ============================================================================
# 5. Check DeepSeek Instance 2 (GPU 6-7, Port 8002)
# ============================================================================
Write-Host ""
Write-Host "[5/5] DEEPSEEK INSTANCE 2 (GPU 6-7, Port 8002)" -ForegroundColor Magenta

if (Test-Port 8002) {
    Write-Host "  Already running on port 8002" -ForegroundColor Green
} else {
    Write-Host "  WARNING: DeepSeek Instance 2 not running!" -ForegroundColor Red
    Write-Host "  Start it manually with:" -ForegroundColor Yellow
    Write-Host "    python scripts/deploy_deepseek_native.py --instance 2 --production" -ForegroundColor White
}

# ============================================================================
# Wait for services to be ready
# ============================================================================
Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  Waiting for services to initialize..." -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan

$embeddings_ready = Wait-ForService -Port 8003 -Name "Embeddings" -MaxWait 180
$kg_ready = Wait-ForService -Port 8004 -Name "Knowledge Graph" -MaxWait 180
$verification_ready = Wait-ForService -Port 8005 -Name "Verification" -MaxWait 180

# ============================================================================
# Health Checks
# ============================================================================
Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  Running Health Checks..." -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan

$all_healthy = $true

# Check Embeddings
if ($embeddings_ready) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8003/health" -Method Get
        Write-Host "  Embeddings: " -NoNewline
        Write-Host $response.status -ForegroundColor Green
        Write-Host "    GPU Memory: $($response.gpu_memory_gb) GB"
    } catch {
        Write-Host "  Embeddings: FAILED" -ForegroundColor Red
        $all_healthy = $false
    }
}

# Check KG
if ($kg_ready) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8004/health" -Method Get
        Write-Host "  Knowledge Graph: " -NoNewline
        Write-Host $response.status -ForegroundColor Green
        Write-Host "    Nodes: $($response.node_count), Edges: $($response.edge_count)"
        Write-Host "    GPU Memory: $($response.gpu_memory_gb) GB"
    } catch {
        Write-Host "  Knowledge Graph: FAILED" -ForegroundColor Red
        $all_healthy = $false
    }
}

# Check Verification
if ($verification_ready) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8005/health" -Method Get
        Write-Host "  Verification: " -NoNewline
        Write-Host $response.status -ForegroundColor Green
        Write-Host "    CrossEncoder: $($response.cross_encoder_loaded), NLI: $($response.nli_model_loaded)"
        Write-Host "    GPU Memory: $($response.gpu_memory_gb) GB"
    } catch {
        Write-Host "  Verification: FAILED" -ForegroundColor Red
        $all_healthy = $false
    }
}

# Check DeepSeek
if (Test-Port 8001) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8001/v1/models" -Method Get
        Write-Host "  DeepSeek 1: " -NoNewline
        Write-Host "healthy" -ForegroundColor Green
    } catch {
        Write-Host "  DeepSeek 1: FAILED" -ForegroundColor Red
    }
}

if (Test-Port 8002) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8002/v1/models" -Method Get
        Write-Host "  DeepSeek 2: " -NoNewline
        Write-Host "healthy" -ForegroundColor Green
    } catch {
        Write-Host "  DeepSeek 2: FAILED" -ForegroundColor Red
    }
}

# ============================================================================
# GPU Memory Check
# ============================================================================
Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  GPU Memory Status (should show memory on all GPUs)" -ForegroundColor Cyan
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan

nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv

# ============================================================================
# Final Status
# ============================================================================
Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan

if ($all_healthy) {
    Write-Host "  ALL SERVICES HEALTHY - Enterprise Grade Ready!" -ForegroundColor Green
} else {
    Write-Host "  SOME SERVICES FAILED - Check logs" -ForegroundColor Red
}

Write-Host "=" -NoNewline; Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor White
Write-Host "  Embeddings:     http://localhost:8003" -ForegroundColor Cyan
Write-Host "  Knowledge Graph: http://localhost:8004" -ForegroundColor Cyan
Write-Host "  Verification:    http://localhost:8005" -ForegroundColor Cyan
Write-Host "  DeepSeek 1:      http://localhost:8001" -ForegroundColor Cyan
Write-Host "  DeepSeek 2:      http://localhost:8002" -ForegroundColor Cyan
Write-Host ""

