# ============================================================================
# NSIC Complete Startup - All CPU + GPU Services
# ============================================================================
# Starts: Embeddings, KG, Verification (CPU) + 8x ExLlama Llama 3.3 70B (GPU)
# ============================================================================

Write-Host "=" * 70
Write-Host "  NSIC COMPLETE STARTUP - CPU + GPU SERVICES"
Write-Host "=" * 70
Write-Host ""

# Load environment variables from .env
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object { 
        if ($_ -match '^([^=]+)=(.*)$') { 
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2]) 
        } 
    }
    Write-Host "[OK] Loaded environment from .env"
}

# Kill any existing processes on our ports
$ports = @(8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8100, 8101, 8102)
foreach ($port in $ports) {
    $proc = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped process on port $port"
    }
}

Write-Host ""
Write-Host "[1/4] Starting CPU Services..."
Write-Host ""

# Start Embeddings Server (port 8100) - NO OVERLAP with GPU ports!
Write-Host "  Starting Embeddings (port 8100)..."
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "src.nsic.servers.embeddings_server:app", "--host", "0.0.0.0", "--port", "8100" -WindowStyle Hidden

# Start KG Server (port 8101)
Write-Host "  Starting Knowledge Graph (port 8101)..."
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "src.nsic.servers.kg_server:app", "--host", "0.0.0.0", "--port", "8101" -WindowStyle Hidden

# Start Verification Server (port 8102)
Write-Host "  Starting Verification (port 8102)..."
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "src.nsic.servers.verification_server:app", "--host", "0.0.0.0", "--port", "8102" -WindowStyle Hidden

Write-Host ""
Write-Host "[2/4] Starting 8x Llama 3.3 70B GPU Instances (parallel)..."
Write-Host ""

# Start 8 ExLlama instances (one per GPU)
for ($i = 0; $i -lt 8; $i++) {
    $port = 8001 + $i
    Write-Host "  Starting Llama 3.3 GPU $i (port $port)..."
    Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "scripts/run_exllama_server.py", "--gpu_id", "$i", "--port", "$port" -WindowStyle Hidden
}

Write-Host ""
Write-Host "[3/4] Waiting for services to initialize (120 seconds)..."
Write-Host ""

# Wait for models to load (ExLlama takes 2-3 minutes per GPU)
Start-Sleep -Seconds 120

Write-Host "[4/4] Health Checks..."
Write-Host ""

# Check CPU services
$cpuServices = @(
    @{Name="Embeddings"; Port=8100},
    @{Name="KG"; Port=8101},
    @{Name="Verification"; Port=8102}
)

foreach ($svc in $cpuServices) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$($svc.Port)/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] $($svc.Name) (port $($svc.Port)): healthy"
    } catch {
        Write-Host "  [!!] $($svc.Name) (port $($svc.Port)): FAILED"
    }
}

# Check GPU instances
for ($i = 0; $i -lt 8; $i++) {
    $port = 8001 + $i
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$port/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] Llama 3.3 GPU $i (port $port): healthy"
    } catch {
        Write-Host "  [!!] Llama 3.3 GPU $i (port $port): FAILED"
    }
}

Write-Host ""
Write-Host "=" * 70
Write-Host "  STARTUP COMPLETE"
Write-Host "=" * 70
Write-Host ""
Write-Host "Service URLs:"
Write-Host "  CPU Services:"
Write-Host "    Embeddings:      http://localhost:8100"
Write-Host "    Knowledge Graph: http://localhost:8101"
Write-Host "    Verification:    http://localhost:8102"
Write-Host ""
Write-Host "  GPU Instances (ExLlama DeepSeek):"
Write-Host "    GPU 0: http://localhost:8001"
Write-Host "    GPU 1: http://localhost:8002"
Write-Host "    GPU 2: http://localhost:8003"
Write-Host "    GPU 3: http://localhost:8004"
Write-Host "    GPU 4: http://localhost:8005"
Write-Host "    GPU 5: http://localhost:8006"
Write-Host "    GPU 6: http://localhost:8007"
Write-Host "    GPU 7: http://localhost:8008"
Write-Host ""
Write-Host "Run test with: python scripts/test_full_e2e.py"
