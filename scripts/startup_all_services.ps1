# ============================================================================
# QNWIS COMPLETE STARTUP SCRIPT
# ============================================================================
# This script ensures ALL required services are running before the system starts:
#   1. PostgreSQL (database)
#   2. Engine B (GPU compute services - Monte Carlo, Sensitivity, etc.)
#   3. Embeddings Server (CPU - for Knowledge Graph)
#   4. Knowledge Graph Server (CPU)
#   5. Verification Server (CPU)
#   6. Redis (optional caching)
# ============================================================================

param(
    [switch]$SkipHealthCheck,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $color = switch ($Status) {
        "OK"      { "Green" }
        "FAIL"    { "Red" }
        "WARN"    { "Yellow" }
        "INFO"    { "Cyan" }
        default   { "White" }
    }
    $prefix = switch ($Status) {
        "OK"      { "[OK]" }
        "FAIL"    { "[FAIL]" }
        "WARN"    { "[WARN]" }
        "INFO"    { "[INFO]" }
        default   { "[....]" }
    }
    Write-Host "$prefix $Message" -ForegroundColor $color
}

function Test-ServiceHealth {
    param([string]$Name, [int]$Port, [string]$Endpoint = "/health")
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port$Endpoint" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Wait-ForService {
    param([string]$Name, [int]$Port, [int]$MaxWait = 60, [string]$Endpoint = "/health")
    $waited = 0
    while ($waited -lt $MaxWait) {
        if (Test-ServiceHealth -Name $Name -Port $Port -Endpoint $Endpoint) {
            return $true
        }
        Start-Sleep -Seconds 2
        $waited += 2
        Write-Host "." -NoNewline
    }
    Write-Host ""
    return $false
}

function Stop-ProcessOnPort {
    param([int]$Port)
    $proc = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | 
            Select-Object -ExpandProperty OwningProcess -First 1
    if ($proc) {
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        return $true
    }
    return $false
}

# ============================================================================
# BANNER
# ============================================================================
Clear-Host
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              QNWIS COMPLETE STARTUP - ALL SERVICES                       ║" -ForegroundColor Cyan
Write-Host "║══════════════════════════════════════════════════════════════════════════║" -ForegroundColor Cyan
Write-Host "║  PostgreSQL | Engine B (8 GPUs) | Embeddings | KG | Verification         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# STEP 0: Load Environment
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host " STEP 0: Loading Environment" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

Set-Location $PSScriptRoot\..

if (Test-Path ".env") {
    Get-Content .env | ForEach-Object { 
        if ($_ -match '^([^#][^=]+)=(.*)$') { 
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim()) 
        } 
    }
    Write-Status "Loaded environment from .env" "OK"
} else {
    Write-Status "No .env file found - using defaults" "WARN"
}

# ============================================================================
# STEP 1: Check PostgreSQL
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host " STEP 1: PostgreSQL Database" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pgService) {
    if ($pgService.Status -eq "Running") {
        Write-Status "PostgreSQL is running ($($pgService.Name))" "OK"
    } else {
        Write-Status "Starting PostgreSQL..." "INFO"
        Start-Service -Name $pgService.Name -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        $pgService = Get-Service -Name $pgService.Name
        if ($pgService.Status -eq "Running") {
            Write-Status "PostgreSQL started successfully" "OK"
        } else {
            Write-Status "Failed to start PostgreSQL!" "FAIL"
            exit 1
        }
    }
} else {
    Write-Status "PostgreSQL service not found - please install PostgreSQL" "FAIL"
    exit 1
}

# ============================================================================
# STEP 2: Check GPU Availability
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host " STEP 2: GPU and CUDA Check" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$nvidiaSmi = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
if ($LASTEXITCODE -eq 0) {
    $gpuCount = ($nvidiaSmi | Measure-Object -Line).Lines
    Write-Status "Found $gpuCount NVIDIA GPU(s):" "OK"
    $nvidiaSmi | ForEach-Object { Write-Host "       $_" -ForegroundColor Gray }
    
    # Check CuPy
    $cupyCheck = python -c "import cupy; print(f'CuPy {cupy.__version__} - {cupy.cuda.runtime.getDeviceCount()} GPUs')" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Status "CuPy available: $cupyCheck" "OK"
    } else {
        Write-Status "CuPy not installed - installing cupy-cuda12x..." "WARN"
        pip install cupy-cuda12x --quiet 2>$null
        Write-Status "CuPy installed" "OK"
    }
} else {
    Write-Status "No NVIDIA GPUs found - Engine B will use CPU fallback" "WARN"
}

# ============================================================================
# STEP 3: Start Engine B (GPU Compute Services)
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host " STEP 3: Engine B (GPU Compute Services)" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

if (Test-ServiceHealth -Name "Engine B" -Port 8001) {
    Write-Status "Engine B already running on port 8001" "OK"
} else {
    # Stop any existing process on port 8001
    if (Stop-ProcessOnPort -Port 8001) {
        Write-Status "Stopped existing process on port 8001" "INFO"
    }
    
    Write-Status "Starting Engine B (GPU: Monte Carlo, Sensitivity, Optimization, Forecasting, Thresholds, Benchmarking, Correlation)..." "INFO"
    Start-Process -FilePath "python" -ArgumentList "-m", "src.nsic.engine_b.api" -WindowStyle Hidden
    
    Write-Host "       Waiting for Engine B to initialize " -NoNewline
    if (Wait-ForService -Name "Engine B" -Port 8001 -MaxWait 30) {
        Write-Status "Engine B started successfully" "OK"
        
        # Check GPU status
        $health = (Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing).Content | ConvertFrom-Json
        $gpuServices = @("monte_carlo", "sensitivity", "thresholds", "correlation")
        $gpuEnabled = 0
        foreach ($svc in $gpuServices) {
            if ($health.services.$svc.gpu_available -eq $true) {
                $gpuEnabled++
            }
        }
        if ($gpuEnabled -gt 0) {
            Write-Status "Engine B GPU acceleration: $gpuEnabled/4 services using GPU" "OK"
        } else {
            Write-Status "Engine B running on CPU (GPU not available)" "WARN"
        }
    } else {
        Write-Status "Engine B failed to start!" "FAIL"
    }
}

# ============================================================================
# STEP 4: Start CPU Services (Embeddings, KG, Verification)
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host " STEP 4: CPU Services - Embeddings - KG - Verification" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$cpuServices = @(
    @{Name="Embeddings"; Port=8100; Module="src.nsic.servers.embeddings_server:app"},
    @{Name="Knowledge Graph"; Port=8101; Module="src.nsic.servers.kg_server:app"},
    @{Name="Verification"; Port=8102; Module="src.nsic.servers.verification_server:app"}
)

foreach ($svc in $cpuServices) {
    if (Test-ServiceHealth -Name $svc.Name -Port $svc.Port) {
        Write-Status "$($svc.Name) already running on port $($svc.Port)" "OK"
    } else {
        if (Stop-ProcessOnPort -Port $svc.Port) {
            Write-Status "Stopped existing process on port $($svc.Port)" "INFO"
        }
        
        Write-Status "Starting $($svc.Name) (port $($svc.Port))..." "INFO"
        Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", $svc.Module, "--host", "0.0.0.0", "--port", $svc.Port -WindowStyle Hidden
        
        Write-Host "       Waiting " -NoNewline
        if (Wait-ForService -Name $svc.Name -Port $svc.Port -MaxWait 30) {
            Write-Status "$($svc.Name) started" "OK"
        } else {
            Write-Status "$($svc.Name) failed to start" "WARN"
        }
    }
}

# ============================================================================
# STEP 5: Final Health Check
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host " STEP 5: Final Health Check" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$allServices = @(
    @{Name="PostgreSQL"; Port=5432; Check="service"},
    @{Name="Engine B (GPU)"; Port=8001; Check="http"},
    @{Name="Embeddings (CPU)"; Port=8100; Check="http"},
    @{Name="Knowledge Graph (CPU)"; Port=8101; Check="http"},
    @{Name="Verification (CPU)"; Port=8102; Check="http"}
)

$healthy = 0
$total = $allServices.Count

foreach ($svc in $allServices) {
    if ($svc.Check -eq "service") {
        $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($pgService -and $pgService.Status -eq "Running") {
            Write-Status "$($svc.Name): HEALTHY" "OK"
            $healthy++
        } else {
            Write-Status "$($svc.Name): DOWN" "FAIL"
        }
    } else {
        if (Test-ServiceHealth -Name $svc.Name -Port $svc.Port) {
            Write-Status "$($svc.Name): HEALTHY (port $($svc.Port))" "OK"
            $healthy++
        } else {
            Write-Status "$($svc.Name): DOWN (port $($svc.Port))" "FAIL"
        }
    }
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                           STARTUP COMPLETE                               ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($healthy -eq $total) {
    Write-Host "  ✅ ALL $total SERVICES HEALTHY" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  $healthy/$total SERVICES HEALTHY" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Service URLs:" -ForegroundColor White
Write-Host "    Engine B (GPU):       http://localhost:8001" -ForegroundColor Gray
Write-Host "    Embeddings (CPU):     http://localhost:8100" -ForegroundColor Gray
Write-Host "    Knowledge Graph:      http://localhost:8101" -ForegroundColor Gray
Write-Host "    Verification:         http://localhost:8102" -ForegroundColor Gray
Write-Host ""
Write-Host "  GPU Assignment (Engine B):" -ForegroundColor White
Write-Host "    GPU 0-1: Monte Carlo Simulation" -ForegroundColor Gray
Write-Host "    GPU 2:   Sensitivity Analysis" -ForegroundColor Gray
Write-Host "    GPU 3:   Optimization Solver" -ForegroundColor Gray
Write-Host "    GPU 4:   Time Series Forecasting" -ForegroundColor Gray
Write-Host "    GPU 5:   Threshold Detection" -ForegroundColor Gray
Write-Host "    GPU 6:   Benchmarking" -ForegroundColor Gray
Write-Host "    GPU 7:   Correlation Analysis" -ForegroundColor Gray
Write-Host ""
Write-Host "  Run diagnostic: python scripts/qnwis_enhanced_diagnostic.py --query economic_diversification --quick" -ForegroundColor Cyan
Write-Host ""

