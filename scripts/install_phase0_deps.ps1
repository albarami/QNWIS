# NSIC Phase 0: Install Remaining Dependencies
# Run from project root: .\scripts\install_phase0_deps.ps1

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "NSIC PHASE 0: REMAINING DEPENDENCIES" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`n[1/4] Activating virtual environment..." -ForegroundColor Yellow
& D:\lmis_int\.venv\Scripts\Activate.ps1

# Install diskcache (pure Python, should work on all platforms)
Write-Host "`n[2/4] Installing diskcache..." -ForegroundColor Yellow
pip install diskcache
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: diskcache installation failed" -ForegroundColor Red
} else {
    Write-Host "diskcache installed successfully" -ForegroundColor Green
}

# Install faiss-cpu (faiss-gpu requires Linux)
Write-Host "`n[3/4] Installing faiss-cpu..." -ForegroundColor Yellow
Write-Host "Note: faiss-gpu is Linux-only, using faiss-cpu on Windows" -ForegroundColor Gray
pip install faiss-cpu
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: faiss-cpu installation failed" -ForegroundColor Red
} else {
    Write-Host "faiss-cpu installed successfully" -ForegroundColor Green
}

# Check vLLM availability on Windows
Write-Host "`n[4/4] Checking vLLM..." -ForegroundColor Yellow
Write-Host "Note: vLLM is Linux-only. On Windows, we'll use HuggingFace Transformers" -ForegroundColor Gray
Write-Host "      for DeepSeek inference with AutoModelForCausalLM + CUDA" -ForegroundColor Gray

# Verify installations
Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$verification = @"
import sys

# Check diskcache
try:
    import diskcache
    print(f'diskcache: {diskcache.__version__} - OK')
except ImportError as e:
    print(f'diskcache: FAILED - {e}')
    sys.exit(1)

# Check faiss
try:
    import faiss
    # faiss doesn't have __version__, just check it imports
    print(f'faiss: installed (faiss-cpu) - OK')
except ImportError as e:
    print(f'faiss: FAILED - {e}')
    sys.exit(1)

# Check torch CUDA (should already be installed)
try:
    import torch
    if torch.cuda.is_available():
        print(f'torch CUDA: {torch.version.cuda} with {torch.cuda.device_count()} GPUs - OK')
    else:
        print('torch CUDA: NOT AVAILABLE')
        sys.exit(1)
except ImportError as e:
    print(f'torch: FAILED - {e}')
    sys.exit(1)

print('')
print('All Phase 0 core dependencies installed!')
sys.exit(0)
"@

python -c $verification

if ($LASTEXITCODE -eq 0) {
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "SUCCESS: Phase 0 dependencies installed!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Note on vLLM:" -ForegroundColor Yellow
    Write-Host "  vLLM is Linux-only and cannot be installed on Windows." -ForegroundColor Yellow
    Write-Host "  For DeepSeek-R1-70B inference, we will use:" -ForegroundColor Yellow
    Write-Host "    - HuggingFace Transformers with AutoModelForCausalLM" -ForegroundColor Yellow
    Write-Host "    - device_map='auto' for multi-GPU distribution" -ForegroundColor Yellow
    Write-Host "    - This provides equivalent functionality on Windows" -ForegroundColor Yellow
} else {
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host "FAILED: Some dependencies could not be installed" -ForegroundColor Red
    Write-Host "======================================================================" -ForegroundColor Red
    exit 1
}

