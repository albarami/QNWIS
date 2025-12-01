@echo off
echo Setting up environment for ExLlamaV2 compilation...

REM Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

REM CUDA environment
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1
set PATH=%CUDA_HOME%\bin;%PATH%

REM Verify nvcc
echo.
echo Checking nvcc...
nvcc --version
if %ERRORLEVEL% NEQ 0 (
    echo NVCC not found!
    exit /b 1
)

REM Set PyTorch environment
set TORCH_CUDA_ARCH_LIST=8.0
echo TORCH_CUDA_ARCH_LIST=%TORCH_CUDA_ARCH_LIST%

echo.
echo Attempting to import ExLlamaV2...
d:\lmis_int\.venv\Scripts\python.exe -c "print('Importing...'); import exllamav2; print('SUCCESS!')"

echo.
echo Done. Exit code: %ERRORLEVEL%

