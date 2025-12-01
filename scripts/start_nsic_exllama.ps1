# NSIC Enterprise Startup Script - ExLlamaV2 8-GPU Configuration
# Starts: 3 CPU services (ports 8100-8102) + 8 DeepSeek instances (ports 8001-8008)

Write-Host "=" * 60
Write-Host "NSIC Enterprise Startup - ExLlamaV2 8-GPU Configuration"
Write-Host "=" * 60
Write-Host ""

# Stop any existing services on our ports
Write-Host "Stopping existing services..." -ForegroundColor Yellow
$ports = @(8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8100, 8101, 8102)
foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        $procId = $conn.OwningProcess
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped process on port $port (PID: $procId)"
    }
}
Start-Sleep -Seconds 3
Write-Host "Done." -ForegroundColor Green
Write-Host ""

# Start CPU Services (ports 8100-8102)
Write-Host "Starting CPU Services..." -ForegroundColor Cyan
Write-Host "  Embeddings Server -> Port 8100"
Start-Process powershell -ArgumentList "-NoExit -Command cd D:\lmis_int; .\.venv\Scripts\python.exe -m src.nsic.servers.embeddings_server"
Start-Sleep -Seconds 2

Write-Host "  KG Server -> Port 8101"
Start-Process powershell -ArgumentList "-NoExit -Command cd D:\lmis_int; .\.venv\Scripts\python.exe -m src.nsic.servers.kg_server"
Start-Sleep -Seconds 2

Write-Host "  Verification Server -> Port 8102"
Start-Process powershell -ArgumentList "-NoExit -Command cd D:\lmis_int; `$env:HF_TOKEN='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'; .\.venv\Scripts\python.exe -m src.nsic.servers.verification_server"
Start-Sleep -Seconds 5
Write-Host "CPU Services started!" -ForegroundColor Green
Write-Host ""

# Start 8 DeepSeek ExLlamaV2 instances (one per GPU)
Write-Host "Starting 8 DeepSeek ExLlamaV2 instances..." -ForegroundColor Cyan
for ($i = 0; $i -lt 8; $i++) {
    $port = 8001 + $i
    Write-Host "  Instance $($i+1): GPU $i -> Port $port"
    Start-Process powershell -ArgumentList "-NoExit -Command cd D:\lmis_int; `$env:CUDA_VISIBLE_DEVICES='$i'; .\.venv\Scripts\python.exe scripts\run_exllama_server.py --gpu_id $i --port $port"
    Start-Sleep -Seconds 2
}
Write-Host "DeepSeek instances starting... (model loading takes ~2-3 minutes)" -ForegroundColor Yellow
Write-Host ""

# Wait for models to load
Write-Host "Waiting for models to load (3 minutes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 180

# Health checks
Write-Host ""
Write-Host "=" * 60
Write-Host "Health Checks"
Write-Host "=" * 60

# Check CPU services
Write-Host ""
Write-Host "CPU Services:" -ForegroundColor Cyan
$cpuServices = @(
    @{Name="Embeddings"; Port=8100},
    @{Name="KG"; Port=8101},
    @{Name="Verification"; Port=8102}
)
foreach ($svc in $cpuServices) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($svc.Port)/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  ✅ $($svc.Name) (port $($svc.Port)): Healthy" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $($svc.Name) (port $($svc.Port)): Not responding" -ForegroundColor Red
    }
}

# Check DeepSeek instances
Write-Host ""
Write-Host "DeepSeek Instances:" -ForegroundColor Cyan
for ($i = 0; $i -lt 8; $i++) {
    $port = 8001 + $i
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -Method Get -TimeoutSec 10 -ErrorAction Stop
        $data = $response.Content | ConvertFrom-Json
        Write-Host "  ✅ Instance $($i+1) (GPU $i, port $port): Healthy - $($data.gpu_memory_gb)GB VRAM" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ Instance $($i+1) (GPU $i, port $port): Not responding" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=" * 60
Write-Host "GPU Memory Usage:"
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader,nounits
Write-Host "=" * 60
Write-Host ""
Write-Host "Startup complete! Run tests with:" -ForegroundColor Green
Write-Host "  pytest tests/test_phase10_e2e.py -v" -ForegroundColor White

