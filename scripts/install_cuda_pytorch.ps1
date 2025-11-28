# NSIC Phase 0: Install CUDA PyTorch
# This script properly installs PyTorch with CUDA 12.1 support for 8x A100 GPUs
# Run from project root: .\scripts\install_cuda_pytorch.ps1

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "NSIC PHASE 0: CUDA PYTORCH INSTALLATION" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Ensure we're in the right directory
if (-not (Test-Path "D:\lmis_int\.venv")) {
    Write-Host "ERROR: Virtual environment not found at D:\lmis_int\.venv" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "`n[1/6] Activating virtual environment..." -ForegroundColor Yellow
& D:\lmis_int\.venv\Scripts\Activate.ps1

# Check current torch version
Write-Host "`n[2/6] Current PyTorch status:" -ForegroundColor Yellow
try {
    python -c "import torch; print(f'Version: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')"
} catch {
    Write-Host "torch not currently installed" -ForegroundColor Gray
}

# Clear pip cache to avoid cached CPU version
Write-Host "`n[3/6] Clearing pip cache..." -ForegroundColor Yellow
pip cache purge

# Completely uninstall torch packages (ignore errors if not installed)
Write-Host "`n[4/6] Uninstalling existing torch packages..." -ForegroundColor Yellow
pip uninstall torch -y 2>&1 | Out-Null
pip uninstall torchvision -y 2>&1 | Out-Null
pip uninstall torchaudio -y 2>&1 | Out-Null
Write-Host "Uninstall complete (or packages were not installed)" -ForegroundColor Gray

# Install CUDA 12.1 PyTorch - THIS IS THE CRITICAL STEP
Write-Host "`n[5/6] Installing PyTorch with CUDA 12.1 support..." -ForegroundColor Yellow
Write-Host "This will download ~2.5GB and may take several minutes..." -ForegroundColor Gray
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Check if install succeeded
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

# Verify installation
Write-Host "`n[6/6] Verifying installation..." -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan

$verification = @"
import torch
import sys

print(f'PyTorch Version: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'CUDA Version: {torch.version.cuda}')
print(f'cuDNN Enabled: {torch.backends.cudnn.enabled}')

if torch.cuda.is_available():
    print(f'GPU Count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f'  GPU {i}: {props.name} ({props.total_memory // 1024**3} GB)')
    sys.exit(0)
else:
    print('CUDA NOT AVAILABLE - Installation failed')
    sys.exit(1)
"@

python -c $verification

if ($LASTEXITCODE -eq 0) {
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "SUCCESS: PyTorch CUDA installation complete!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host "FAILED: CUDA still not available after installation" -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Red
    Write-Host "  1. NVIDIA driver is installed (nvidia-smi should work)" -ForegroundColor Red
    Write-Host "  2. CUDA toolkit 12.1 is compatible with your driver" -ForegroundColor Red
    Write-Host "======================================================================" -ForegroundColor Red
    exit 1
}
