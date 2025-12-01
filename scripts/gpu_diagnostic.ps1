# GPU Diagnostic Script
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "NVIDIA GPU Diagnostic" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host "`n1. Testing nvidia-smi from System32..." -ForegroundColor Yellow
$result1 = & "C:\Windows\System32\nvidia-smi.exe" 2>&1
Write-Host $result1

Write-Host "`n2. Testing nvidia-smi from DriverStore..." -ForegroundColor Yellow
$driverStorePath = "C:\Windows\System32\DriverStore\FileRepository\nv_dispui.inf_amd64_c3352d3df1cf4d8c\nvidia-smi.exe"
if (Test-Path $driverStorePath) {
    $result2 = & $driverStorePath 2>&1
    Write-Host $result2
} else {
    Write-Host "DriverStore nvidia-smi not found"
}

Write-Host "`n3. Testing PyTorch CUDA..." -ForegroundColor Yellow
$env:CUDA_VISIBLE_DEVICES = ""  # Clear any restrictions
$pythonCmd = @"
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'Device count: {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
else:
    print('CUDA NOT AVAILABLE - checking why...')
    import os
    print(f'CUDA_HOME: {os.environ.get("CUDA_HOME", "Not set")}')
    print(f'CUDA_PATH: {os.environ.get("CUDA_PATH", "Not set")}')
"@

d:\lmis_int\.venv\Scripts\python.exe -c $pythonCmd 2>&1

Write-Host "`n4. CUDA Library Check..." -ForegroundColor Yellow
$cudaLibs = @(
    "C:\Windows\System32\nvcuda.dll",
    "C:\Windows\System32\nvml.dll"
)
foreach ($lib in $cudaLibs) {
    if (Test-Path $lib) {
        $info = Get-Item $lib
        Write-Host "  Found: $lib ($($info.Length / 1MB) MB)"
    } else {
        Write-Host "  Missing: $lib" -ForegroundColor Red
    }
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan

