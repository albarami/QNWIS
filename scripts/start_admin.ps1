# NSIC Startup Script - MUST RUN AS ADMINISTRATOR
# The A100 GPUs are in TCC mode which requires admin privileges

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "NSIC Enterprise Startup - Administrator Required" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Check admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host ""
    Write-Host "ERROR: This script must run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "The A100 GPUs are in TCC mode which requires admin access." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run as admin:" -ForegroundColor Cyan
    Write-Host "  1. Right-click PowerShell" -ForegroundColor White
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "  3. Navigate to D:\lmis_int" -ForegroundColor White
    Write-Host "  4. Run: .\scripts\start_admin.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Administrator privileges confirmed!" -ForegroundColor Green
Write-Host ""

# Test GPU access
Write-Host "Testing GPU access..." -ForegroundColor Yellow
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: GPU access failed even with admin!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "GPUs accessible!" -ForegroundColor Green
Write-Host ""

# Test PyTorch CUDA
Write-Host "Testing PyTorch CUDA..." -ForegroundColor Yellow
d:\lmis_int\.venv\Scripts\python.exe -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPUs: {torch.cuda.device_count()}')"

Write-Host ""
Write-Host "Ready to start services!" -ForegroundColor Green

